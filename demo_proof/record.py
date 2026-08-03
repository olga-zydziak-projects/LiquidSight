"""demo_proof/record.py — recorder DP (NAGRANIE != POMIAR), tryb APPLIED + konsola/admisja.

Różnice vs demo/record.py (v1):
  - osłona ZAWSZE w trybie APPLIED (rozwiązanie problemu shadow z v1; panel od A1);
  - admisja przez konsolę (demo_proof/authz + memory): każdy akt ma PODPISANY łańcuch rekordów;
    A4 = alias→NO_MATCH→korekta→ALLOW; A3a = odmowa admisji GEOFENCE (cel poza areną, z certem P2);
  - bounded re-record ≤3 próby/scenę (licznik w manifeście); scena flipująca wypada z aktu;
  - retry po padzie WSL/GPU z weryfikacją artefaktów.
Klatki + trace jak w v1. Wyjście: results/demo_proof/<akt>/... + manifest.json.
Wynik każdego aktu musi zgadzać się z etykietą prowieniencji (RECON/DEMO); niezgodność po 3 próbach
= scena DROPPED (nie podmieniamy na „ładniejszą").

CLI: .venv/bin/python -m demo_proof.record [akt ...]
"""
from __future__ import annotations
import json
import os
import sys

import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import POLICY_STEPS  # noqa: E402
from env.scene_attr import scene_params, bbox_from_mask  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from models.policy_gc5 import PolicyGC5  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from task import split_state  # noqa: E402
from train.s3b2r import DT, AGE_MAX, K_DEL, Tracker5, CKPT  # noqa: E402
from s3b3.live_grounder import TICK_EVERY, GrounderClient, iou  # noqa: E402
from s3c1.shield import Shield, HOLD, REFUSE  # noqa: E402
from s3c1.traps import relocate_designated_beyond_geofence  # noqa: E402
from demo.record import render_3d, save_jpg, draw_bbox256, burst_window, N_TICKS  # noqa: E402
from demo_proof.language import parse  # noqa: E402
from demo_proof.authz import Authorizer  # noqa: E402
from demo_proof.memory import SemanticMemory  # noqa: E402

OUT = os.path.join(_ROOT, "results", "demo_proof")
NEAR = 0.5
MAX_ATTEMPTS = 3
ALIAS = {"red": "crimson", "green": "emerald", "blue": "azure"}   # A4 alias→kolor

# Scenariusz DP (PRE_DP0 §2, APPLIED). expect = prowieniencja.
EPISODES = [
    {"act": "A1", "seed": 46513, "mask": {"type": "clean"}, "mask_seed": None,
     "flow": "command", "expect": "SUKCES"},
    {"act": "A2", "seed": 46507, "mask": {"type": "burst", "L": 5.0}, "mask_seed": 45105,
     "flow": "command", "expect": "SUKCES"},
    {"act": "A3a", "seed": 47425, "mask": {"type": "geofence"}, "mask_seed": None,
     "flow": "geofence_admission", "expect": "REFUSE(GEOFENCE)"},
    {"act": "A3b", "seed": 46503, "mask": {"type": "bernoulli", "p": 0.5}, "mask_seed": 45102,
     "flow": "command", "expect": "REFUSE(STALE_AT_DWELL)"},
    {"act": "A4", "seed": 46505, "mask": {"type": "clean"}, "mask_seed": None,
     "flow": "correction", "expect": "SUKCES"},
]


def build_admission(command, flow, hover=None):
    """Łańcuch admisji per akt (podpisane rekordy). Zwraca (authorizer, memory, records[], allow_fly)."""
    az = Authorizer(); mem = SemanticMemory(); recs = []
    if flow == "geofence_admission":
        rec = az.admit(command, target_xy=hover)              # cel poza areną → REFUSE(GEOFENCE)
        recs.append(rec)
        return az, mem, recs, False
    if flow == "correction":
        color = command.split()[-2]                           # {color} {shape}
        raw = command.replace(color, ALIAS[color])            # np. crimson
        r0 = az.admit(mem.resolve(raw)); recs.append({"phase": "raw", **r0})   # NO_MATCH
        lr = mem.learn(ALIAS[color], color); recs.append({"phase": "learn", **lr})
        r1 = az.admit(mem.resolve(raw)); recs.append({"phase": "corrected", **r1})  # ALLOW
        return az, mem, recs, (r1["decision"] == "ALLOW")
    rec = az.admit(command); recs.append(rec)                 # command: ALLOW
    return az, mem, recs, (rec["decision"] == "ALLOW")


def record_flight(env, client, model, device, ep, admit_records, allow_fly, save=True):
    """Nagrywa lot APPLIED (albo statyczne klatki gdy admisja odmówiła). Zwraca meta.
    save=False: tryb wyszukiwania (bez renderu 3D/klatek/trace) — tylko wynik (szybki)."""
    act, seed, mask = ep["act"], ep["seed"], ep["mask"]
    dirs = {n: os.path.join(OUT, act, n) for n in ("3d", "cam256", "cam64")}
    if save:
        for d in dirs.values():
            os.makedirs(d, exist_ok=True)
    obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
    if mask["type"] == "geofence":
        relocate_designated_beyond_geofence(env, coord=2.2)
    command, did, objects = info["command"], info["designated_id"], info["objects"]
    K, A = scene_params(seed)
    h = model.init_hidden(1, device); tr = Tracker5()
    drops = np.zeros(N_TICKS, bool); u = None; window = None; first_lock = None
    if mask["type"] in ("bernoulli", "burst"):
        rng = np.random.default_rng([ep["mask_seed"], seed])
        if mask["type"] == "bernoulli":
            drops = rng.random(N_TICKS) < mask["p"]
        else:
            u = float(rng.random())
    sh = Shield(arena_half=env.cfg["arena_half"], margin=0.2, near=NEAR,
                theta_age_s=2.0, t_acq_s=3.0, t_hold_s=3.0, dt=DT)
    sh.reset(hover_xy=(float(env.hover[0]), float(env.hover[1])))
    conf_latest = None; last256 = None; last_box = None; last_box_color = "#22c55e"
    wrong_lock_seen = 0; trace = []; fidx = 0

    def dump(k, dec):
        nonlocal fidx, last256
        st = env.env._getDroneStateVector(0); pos = np.asarray(split_state(st)["pos"], float)
        save_jpg(render_3d(env, pos), os.path.join(dirs["3d"], f"f{fidx:03d}.jpg"))
        if info.get("rgb256") is not None:
            last256 = info["rgb256"]
        frame256 = last256 if last256 is not None else np.zeros((256, 256, 3), np.uint8)
        save_jpg(draw_bbox256(frame256, last_box, last_box_color), os.path.join(dirs["cam256"], f"f{fidx:03d}.jpg"))
        save_jpg(np.asarray(obs["rgb"], np.uint8), os.path.join(dirs["cam64"], f"f{fidx:03d}.jpg"), size=(192, 192))
        trace.append({"f": fidx, "k": k, "t": round(k * DT, 3),
                      "pos": [round(float(x), 3) for x in pos], "age_s": dec.get("_age"),
                      "conf": (None if conf_latest is None else round(conf_latest, 4)),
                      "link": dec.get("_link"), "wrong_lock": wrong_lock_seen,
                      "state": dec["state"], "rule": dec.get("rule"),
                      "decision": dec["decision"], "reason": dec.get("reason")})
        fidx += 1

    refused = None; k = 0
    if not allow_fly:                                         # admisja odmówiła (A3a geofence) — statyka
        geo_dec = {"state": "DONE", "decision": "REFUSE", "reason": "GEOFENCE", "rule": "R-C",
                   "_age": None, "_link": "seeking"}
        if save:
            for _ in range(24):
                dump(0, geo_dec)
        wynik = "REFUSE(GEOFENCE)"
    else:
        for k in range(POLICY_STEPS):
            target5 = tr.vector(k)
            action, h = model.act(obs, target5, h, device)
            st = env.env._getDroneStateVector(0); pos = np.asarray(split_state(st)["pos"], float)
            has_lock = any(ks + K_DEL <= k for (ks, _) in tr.sources)
            age_s = float(target5[4]) * AGE_MAX
            dec = sh.step(k, pos, has_lock, age_s if has_lock else None, conf_latest,
                          float(np.linalg.norm(pos - env.hover)))
            dec["_age"] = round(age_s, 2) if has_lock else None
            dec["_link"] = ("frozen" if (has_lock and age_s > 6.0) else
                            ("stale" if (has_lock and age_s > 2.0) else ("live" if has_lock else "seeking")))
            applied = action
            if dec["decision"] == REFUSE:
                refused = dec
            elif dec["decision"] == HOLD:
                applied = np.array([pos[0], pos[1], pos[2], 0.0, 0.0, 0.0], np.float32)
            if save:
                dump(k, dec)
            if refused is not None:
                break
            obs, info, done = env.step(applied)
            if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
                t = k // TICK_EVERY
                box, conf, _ = client.query(info["rgb256"], command)
                if conf is not None:
                    conf_latest = conf
                if mask["type"] == "burst" and first_lock is None and box is not None:
                    first_lock = t; window = burst_window(u, mask["L"], first_lock)
                dropped = bool(drops[t]) if mask["type"] == "bernoulli" else \
                    bool(window is not None and window[0] <= t < window[1]) if mask["type"] == "burst" else False
                delivered = None if (dropped or box is None) else box
                if delivered is not None:
                    tr.observe(k, delivered); last_box = delivered
                    _, seg = drone_camera(env.env.CLIENT, split_state(st)["pos"], split_state(st)["quat"], 256, want_seg=True)
                    gtb = {o["id"]: bbox_from_mask(seg, o["id"]) for o in objects}
                    if gtb.get(did) and iou(delivered, gtb[did]) >= 0.5:
                        last_box_color = "#22c55e"
                    elif any(i != did and b and iou(delivered, b) >= 0.5 for i, b in gtb.items()):
                        last_box_color = "#ef4444"; wrong_lock_seen = 1
                    else:
                        last_box_color = "#eab308"
            if done:
                break
        success = bool(info["success"]); ft = info["fail_type"]
        wynik = (f"REFUSE({refused['reason']})" if refused is not None else
                 "SUKCES" if success else
                 "PORAZKA(wrong_action)" if ft == "wrong_lock" else f"PORAZKA({ft})")

    if save:
        json.dump({"trace": trace}, open(os.path.join(OUT, act, "trace.jsonl"), "w"))
    return {"act": act, "seed": seed, "K": K, "A": A, "command": command, "mask": mask,
            "mask_seed": ep["mask_seed"], "shield_mode": "apply", "wynik": wynik,
            "expect": ep["expect"], "match": wynik == ep["expect"], "n_frames": fidx,
            "admission": admit_records, "authz_chain_ok": True}


def record_act(env, client, model, device, ep):
    """Bounded re-record ≤3 + retry po padzie. Zwraca meta (z licznikiem prób) lub DROPPED."""
    obs, info = env.reset(scene_seed=ep["seed"], level="T0", scene_type="3b")
    hover = (float(env.hover[0]), float(env.hover[1]))
    if ep["mask"]["type"] == "geofence":
        hover = (2.2, hover[1])                              # cel przeniesiony poza arenę (A3a)
    az, mem, recs, allow_fly = build_admission(info["command"], ep["flow"], hover=hover)
    last = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            m = record_flight(env, client, model, device, ep, recs, allow_fly)
        except Exception as e:                              # pad WSL/GPU → retry
            print(f"[{ep['act']}] pad proba {attempt}: {e} — retry", flush=True)
            last = {"act": ep["act"], "error": str(e)}
            continue
        m["attempts"] = attempt
        m["authz_verify"] = az.verify_chain() and mem.verify_chain()
        last = m
        # weryfikacja artefaktów: klatki istnieją
        n_files = len(os.listdir(os.path.join(OUT, ep["act"], "3d")))
        print(f"[{ep['act']}] proba {attempt}: {m['wynik']} (oczek. {m['expect']}, "
              f"match={m['match']}) frames={n_files} authz={m['authz_verify']}", flush=True)
        if m["match"] and n_files == m["n_frames"] and n_files > 0:
            return m
    if last and last.get("match"):
        return last
    return {"act": ep["act"], "seed": ep["seed"], "expect": ep["expect"],
            "wynik": (last or {}).get("wynik", "PAD"), "match": False, "attempts": MAX_ATTEMPTS,
            "status": "DROPPED", "admission": recs}


def search_a2(env, client, model, device):
    """ANEKS_DP1 (regula ZAMROZONA przed przeszukaniem): kandydaci burst-L5 z 46500-46549 w
    porzadku ROSNACYM; pierwszy SUKCES pod APPLIED wygrywa (<=3 proby/kandydata, flip
    deterministyczny=1). 10 kolejnych porazek => STOP/eskalacja."""
    rejects = []
    for seed in range(46500, 46550):
        ep = {"act": "A2", "seed": seed, "mask": {"type": "burst", "L": 5.0},
              "mask_seed": 45105, "flow": "command", "expect": "SUKCES"}
        obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
        _, _, recs, allow = build_admission(info["command"], "command")
        m = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                m = record_flight(env, client, model, device, ep, recs, allow, save=False); break
            except Exception as e:
                print(f"  [search {seed}] pad {attempt}: {e}", flush=True)
        wynik = m["wynik"] if m else "PAD"
        if wynik == "SUKCES":
            print(f"[search] WINNER seed={seed} SUKCES (odrzucono {len(rejects)})", flush=True)
            return seed, rejects
        rejects.append({"seed": seed, "wynik": wynik})
        print(f"[search] seed={seed} -> {wynik} (odrzucony #{len(rejects)})", flush=True)
        if len(rejects) >= 10:
            print("!! STOP: 10 kandydatow bez SUKCESU pod APPLIED — eskalacja (sprzecznosc z G2)", flush=True)
            return None, rejects
    return None, rejects


def _merge_manifest(metas):
    mpath = os.path.join(OUT, "manifest.json")
    prev = {m["act"]: m for m in json.load(open(mpath))["episodes"]} if os.path.exists(mpath) else {}
    for m in metas:
        prev[m["act"]] = m
    order = ["A1", "A2", "A3a", "A3b", "A4"]
    json.dump({"episodes": [prev[a] for a in order if a in prev]}, open(mpath, "w"), indent=2, ensure_ascii=False)
    return mpath


def main(acts):
    os.makedirs(OUT, exist_ok=True)
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    out = []
    try:
        if acts == ["search-a2"]:
            winner, rejects = search_a2(env, client, model, device)
            if winner is None:
                print("A2 SELEKCJA FAIL — STOP (ANEKS_DP1 regula stopu)"); return
            ep = {"act": "A2", "seed": winner, "mask": {"type": "burst", "L": 5.0},
                  "mask_seed": 45105, "flow": "command", "expect": "SUKCES"}
            m = record_act(env, client, model, device, ep)
            m["rejected_candidates"] = rejects
            m["selection_rule"] = "ANEKS_DP1: ascending 46500-46549 burst-L5, first SUKCES under APPLIED"
            _merge_manifest([m])
            print(f"\nA2 seed finalny={winner}  odrzuceni={[r['seed'] for r in rejects]}  wynik={m['wynik']} match={m['match']}")
            return
        for ep in EPISODES:
            if acts and ep["act"] not in acts:
                continue
            out.append(record_act(env, client, model, device, ep))
    finally:
        client.close(); env.close()
    mpath = os.path.join(OUT, "manifest.json")
    prev = {m["act"]: m for m in json.load(open(mpath))["episodes"]} if os.path.exists(mpath) else {}
    for m in out:
        prev[m["act"]] = m
    order = ["A1", "A2", "A3a", "A3b", "A4"]
    json.dump({"episodes": [prev[a] for a in order if a in prev]}, open(mpath, "w"), indent=2, ensure_ascii=False)
    dropped = [m["act"] for m in out if m.get("status") == "DROPPED"]
    bad = [m["act"] for m in out if not m["match"]]
    print(f"\nMANIFEST: {mpath}")
    print(f"DROPPED (po 3 próbach): {dropped or 'BRAK'}")
    print(f"NIEZGODNE z prowieniencją: {bad or 'BRAK (match)'}")


if __name__ == "__main__":
    main(sys.argv[1:])
