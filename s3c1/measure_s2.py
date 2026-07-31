"""s3c1/measure_s2.py — POMIAR-S2: odmowa twarda na pułapkach (pula 47400-47449).

25 ep ABSENT (47400-47424): komenda -> obiekt nieobecny; oczekiwanie REFUSE(NO_MATCH).
25 ep GEOFENCE (47425-47449): cel przeniesiony poza geofence; oczekiwanie REFUSE(GEOFENCE).
Każdy epizod z osłoną (i bez — kontrast). Raport: odsetek poprawnych odmów z właściwym
powodem; KAŻDE odstępstwo wypisane per epizod. MIERZĘ = RAPORTUJE.

CLI: .venv/bin/python -m s3c1.measure_s2
"""
from __future__ import annotations
import collections
import json
import os
import sys

import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import POLICY_STEPS  # noqa: E402
from env.scene_attr import scene_params  # noqa: E402
from models.policy_gc5 import PolicyGC5  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from task import split_state  # noqa: E402
from train.s3b2r import DT, AGE_MAX, K_DEL, Tracker5, CKPT  # noqa: E402
from s3b3.live_grounder import TICK_EVERY, GrounderClient  # noqa: E402
from s3c1.shield import Shield, HOLD, REFUSE  # noqa: E402
from s3c1.traps import absent_command, relocate_designated_beyond_geofence  # noqa: E402

OUT = os.path.join(_ROOT, "results", "s3c1")
NEAR = 0.5


def run_trap(env, client, model, device, seed, variant, use_shield):
    obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
    if variant == "absent":
        command, absent_pair = absent_command(info["objects"], seed)
    else:                                   # geofence
        relocate_designated_beyond_geofence(env, coord=2.2)
        command, absent_pair = info["command"], None
    h = model.init_hidden(1, device); tr = Tracker5()
    sh = None
    if use_shield:
        sh = Shield(arena_half=env.cfg["arena_half"], margin=0.2, near=NEAR,
                    theta_age_s=2.0, t_acq_s=3.0, t_hold_s=3.0, dt=DT)
        sh.reset(hover_xy=(float(env.hover[0]), float(env.hover[1])))
    conf_latest = None; refused = None; k = 0
    for k in range(POLICY_STEPS):
        target5 = tr.vector(k)
        action, h = model.act(obs, target5, h, device)
        st = env.env._getDroneStateVector(0)
        pos = np.asarray(split_state(st)["pos"], float)
        applied = action
        if sh is not None:
            has_lock = any(ks + K_DEL <= k for (ks, _) in tr.sources)
            age_s = float(target5[4]) * AGE_MAX
            dist = float(np.linalg.norm(pos - env.hover))
            d = sh.step(k, pos, has_lock, age_s if has_lock else None, conf_latest, dist)
            if d["decision"] == REFUSE:
                refused = d; break
            if d["decision"] == HOLD:
                applied = np.array([pos[0], pos[1], pos[2], 0.0, 0.0, 0.0], np.float32)
        obs, info, done = env.step(applied)
        if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
            box, conf, _ = client.query(info["rgb256"], command)
            if conf is not None:
                conf_latest = conf
            if box is not None:
                tr.observe(k, box)
        if done:
            break
    rec = {"seed": seed, "variant": variant, "K": scene_params(seed)[0],
           "command": command, "n_steps": k + 1,
           "env_fail_type": info["fail_type"], "env_success": bool(info["success"])}
    if use_shield:
        rec["refused"] = refused is not None
        rec["reason"] = refused["reason"] if refused else None
        rec["rule"] = refused["rule"] if refused else None
        rec["refuse_k"] = refused["k"] if refused else None
    return rec


def main():
    os.makedirs(OUT, exist_ok=True)
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    variants = [("absent", range(47400, 47425), "NO_MATCH"),
                ("geofence", range(47425, 47450), "GEOFENCE")]
    out = {}
    try:
        for variant, seeds, expected in variants:
            recs = []; unshielded = []
            for seed in seeds:
                recs.append(run_trap(env, client, model, device, seed, variant, True))
                unshielded.append(run_trap(env, client, model, device, seed, variant, False))
            n = len(recs)
            correct = sum(1 for r in recs if r["refused"] and r["reason"] == expected)
            reasons = collections.Counter(r["reason"] for r in recs)
            deviations = [{"seed": r["seed"], "refused": r["refused"], "reason": r["reason"],
                          "env_fail_type": r["env_fail_type"], "command": r["command"]}
                         for r in recs if not (r["refused"] and r["reason"] == expected)]
            umap = {u["seed"]: u for u in unshielded}
            base_fail = collections.Counter(
                ("katastrofa" if umap[r["seed"]]["env_fail_type"] in ("geofence", "tilt", "crash", "contact")
                 else ("sukces" if umap[r["seed"]]["env_success"] else umap[r["seed"]]["env_fail_type"] or "inne"))
                for r in recs)
            out[variant] = {
                "n": n, "expected_reason": expected,
                "poprawne_odmowy": correct, "poprawne_odmowy_pct": round(100 * correct / n, 1),
                "odmowy_per_powod": dict(reasons),
                "baza_bez_oslony": dict(base_fail),
                "odstepstwa": deviations,
                "episodes": recs,
            }
            print(f"\n=== S2 {variant} (n={n}, expected={expected}) ===")
            print(f"poprawne odmowy: {correct}/{n} = {round(100*correct/n,1)}%")
            print(f"odmowy per powod: {dict(reasons)}")
            print(f"baza bez oslony: {dict(base_fail)}")
            if deviations:
                print(f"ODSTEPSTWA ({len(deviations)}):")
                for dv in deviations:
                    print(f"  seed {dv['seed']}: refused={dv['refused']} reason={dv['reason']} "
                          f"env_fail={dv['env_fail_type']} cmd='{dv['command']}'")
            else:
                print("odstepstwa: BRAK (100% poprawnych odmow)")
        # --- dodatkowo: zrzut trace jednego epizodu HOLD->REFUSE(STALE) z nogi B (pod figurę osi czasu) ---
        try:
            from s3c1.measure_s1 import run_episode, MASK_SEED_P50
            legB = os.path.join(OUT, "s1_legB.json")
            target = None
            if os.path.exists(legB):
                epsB = json.load(open(legB))["episodes"]
                hold = [e for e in epsB if e.get("n_hold_enter", 0) > 0 and "STALE" in e["shield"]]
                hold = hold or [e for e in epsB if e.get("n_hold_enter", 0) > 0]
                if hold:
                    target = hold[0]["seed"]
            if target is not None:
                rec = run_episode(env, client, model, device, target, 0.5, MASK_SEED_P50, True)
                json.dump({str(target): rec["trace"]},
                          open(os.path.join(OUT, "traces_legB.json"), "w"), indent=1)
                print(f"\nTRACE zrzucony: seed {target} ({rec['wynik']}/{rec.get('refuse_reason')})")
        except Exception as e:
            print("zrzut trace pominiety:", e)
    finally:
        client.close(); env.close()
    json.dump(out, open(os.path.join(OUT, "s2_traps.json"), "w"), indent=2)
    print("\nZAPIS ->", os.path.join(OUT, "s2_traps.json"))


if __name__ == "__main__":
    main()
