"""s3b4 — G2: zrywany strumien semantyczny (charakteryzacja mostkowania przerw).

ZERO treningu. Model FROZEN = ckpt/s3b2r/policy_gc5.pt (S3b2-R, 67%). Czysta ewaluacja.
Dropout DOSTARCZEN groundera (kontrakt D3 niezmieniony): grounder pytany co tick (dla
determinizmu i naturalnego no-det), ale DOSTARCZENIE do trackera moze byc stlumione wg
maski deterministycznej maska = f(seed_maski, epizod). Tracker mostkuje przerwe: ZOH +
rosnacy age (jak przy naturalnym braku locku).

Osie (D6): Bernoulli p (drop per tick) + burst L s (ciagle okno, start po pierwszym locku).
Maski: pula 45100+. Ramowanie G2 = charakteryzacja (bez progu). MIERZE = RAPORTUJE.

CLI: python -m train.s3b4 {probe|measure}
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
from env.scene_attr import bbox_from_mask, scene_params  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from models.policy_gc5 import PolicyGC5  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from task import split_state  # noqa: E402
from train.s3b2r import DT, Tracker5, CKPT  # noqa: E402  (model frozen)
from s3b3.live_grounder import TICK_EVERY, GrounderClient, iou  # noqa: E402

OUT = os.path.join(_ROOT, "results", "s3b4")
N_TICKS = POLICY_STEPS // TICK_EVERY          # 10 (1 Hz, epizod 10 s)
TICK_PERIOD = TICK_EVERY * DT                 # 1.0 s
R_GOAL, NEAR = 0.25, 0.5
BASE = 67.0                                   # granica G1 zmierzona (S3b2-R, precond-R 100 ep)
AGE_BINS = [0, .1, .25, .5, .75, 1.01]

# --- mapowanie poziom -> seed maski (pula 45100+), zapisane -----------------
MASK_SEED = {"p0.00": 45100, "p0.25": 45101, "p0.50": 45102, "p0.75": 45103,
             "L2": 45104, "L5": 45105, "p0.90": 45106, "p0.10": 45107,
             "probe_p0.50": 45150, "probe_L5": 45151}


def level_spec(name):
    """name -> dict(mode,param). Bernoulli 'pX.XX', burst 'LN', probe_*."""
    base = name.replace("probe_", "")
    if base.startswith("p"):
        return {"mode": "bernoulli", "p": float(base[1:]), "name": name}
    if base.startswith("L"):
        return {"mode": "burst", "L": float(base[1:]), "name": name}
    raise ValueError(name)


def eval_level(env, client, model, device, seeds, name):
    """Ewaluacja jednego poziomu dropoutu na wspolnych scenach (parowanie)."""
    spec = level_spec(name)
    mode = spec["mode"]; mseed = MASK_SEED[name]
    succ = 0; fails = collections.Counter(); cat = 0
    per_cell = collections.defaultdict(lambda: [0, 0, 0])
    n_tick_tot = n_dropout = n_natural_none = n_effective_none = 0
    wl_eps = []; near_fail = 0; age_dwell = []; n_entered = 0
    eps_dump = []
    for seed in seeds:
        K, A = scene_params(seed)
        obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
        command, did, objects = info["command"], info["designated_id"], info["objects"]
        h = model.init_hidden(1, device); tr = Tracker5()
        rng = np.random.default_rng([mseed, seed])
        drops = (rng.random(N_TICKS) < spec["p"]) if mode == "bernoulli" else None
        u = float(rng.random()) if mode == "burst" else None
        first_lock = None; window = None
        src_matched = []; positions = []; entered = False; age_at_entry = None
        for k in range(POLICY_STEPS):
            tgt = tr.vector(k)
            action, h = model.act(obs, tgt, h, device)
            st = env.env._getDroneStateVector(0); sp = split_state(st)
            pos = np.asarray(sp["pos"], float); positions.append(pos)
            if not entered and float(np.linalg.norm(pos - env.hover)) <= R_GOAL:
                entered = True; age_at_entry = float(tgt[4])
            obs, info, done = env.step(action)
            if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
                t = k // TICK_EVERY
                box, conf, _ = client.query(info["rgb256"], command)   # zawsze pytamy (determinizm)
                if mode == "bernoulli":
                    dropped = bool(drops[t])
                elif mode == "burst":
                    dropped = bool(window is not None and window[0] <= t < window[1])
                else:
                    dropped = False
                delivered = None if (dropped or box is None) else box
                n_tick_tot += 1
                n_dropout += int(dropped)
                n_natural_none += int(box is None)
                n_effective_none += int(delivered is None)
                if delivered is not None:
                    tr.observe(k, delivered)
                    # dopasowanie GT tylko dla DOSTARCZONYCH (co polityka realnie dostaje)
                    _, seg = drone_camera(env.env.CLIENT, sp["pos"], sp["quat"], 256, want_seg=True)
                    gtb = {o["id"]: bbox_from_mask(seg, o["id"]) for o in objects}
                    if gtb.get(did) and iou(delivered, gtb[did]) >= 0.5:
                        m = "designated"
                    else:
                        m = "other" if any(i != did and b and iou(delivered, b) >= 0.5
                                           for i, b in gtb.items()) else "background"
                    src_matched.append(m)
                    if mode == "burst" and first_lock is None:
                        first_lock = t
                        Lt = int(round(spec["L"] / TICK_PERIOD))
                        earliest, latest = t + 1, N_TICKS - Lt
                        start = earliest if latest < earliest else earliest + int(u * (latest - earliest + 1))
                        window = (start, start + Lt)
            if done:
                break
        positions = np.array(positions)
        min_dist = float(np.min(np.linalg.norm(positions - env.hover, axis=1)))
        ok = bool(info["success"]); ft = info["fail_type"]
        c = per_cell[(K, A)]; c[0] += 1; c[1] += int(ok); c[2] += int(ft == "wrong_lock")
        if ok:
            succ += 1
        else:
            fails[ft] += 1; cat += int(env.is_catastrophe(ft))
            near_fail += int(min_dist <= NEAR)
        if ft == "wrong_lock":
            wl_eps.append(src_matched)
        if entered:
            n_entered += 1; age_dwell.append(age_at_entry)
        eps_dump.append({"seed": seed, "K": K, "A": A, "success": ok, "fail_type": ft,
                         "min_dist": round(min_dist, 3), "first_lock": first_lock,
                         "burst_window": window, "age_at_dwell_entry": age_at_entry})
    # dekompozycja wrong-lock (pierwszy-zly / kradziez / inne)
    fb = th = ot = 0
    for sm in wl_eps:
        if not sm:
            ot += 1
        elif sm[0] == "other":
            fb += 1
        elif "designated" in sm and "other" in sm[sm.index("designated"):]:
            th += 1
        else:
            ot += 1
    n = len(seeds); nf = n - succ
    hist = np.histogram(age_dwell, bins=AGE_BINS)[0].tolist() if age_dwell else [0] * (len(AGE_BINS) - 1)
    return {
        "level": name, "mask_seed": mseed, "n": n,
        "sukces_pct": round(100 * succ / n, 1),
        "sd_binom_pp": round(100 * (succ / n * (1 - succ / n) / n) ** 0.5, 1),
        "wrong_lock_pct": round(100 * fails.get("wrong_lock", 0) / n, 1),
        "wrong_lock_decomp": {"pierwszy_zly": fb, "kradziez": th, "inne": ot,
                              "pierwszy_zly_pp": round(100 * fb / n, 1), "kradziez_pp": round(100 * th / n, 1)},
        "no_arrival": fails.get("no_arrival", 0), "dwell": fails.get("dwell", 0), "katastrofy": cat,
        "near_miss_pct_of_fails": round(100 * near_fail / nf, 1) if nf else 0.0,
        "eff_no_det_pct": round(100 * n_effective_none / n_tick_tot, 1),
        "natural_no_det_pct": round(100 * n_natural_none / n_tick_tot, 1),
        "dropout_pct": round(100 * n_dropout / n_tick_tot, 1),
        "n_entered_dwell": n_entered,
        "age_at_dwell_entry_hist": {"bins": AGE_BINS, "counts": hist},
        "per_cell": {f"K{K}_{A}": {"n": v[0], "sukces_pct": round(100 * v[1] / v[0], 1), "wrong_lock": v[2]}
                     for (K, A), v in sorted(per_cell.items())},
        "episodes": eps_dump,
    }


def _run(seeds, names, out_name):
    os.makedirs(OUT, exist_ok=True)
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    results = {}
    try:
        for nm in names:
            r = eval_level(env, client, model, device, seeds, nm)
            results[nm] = r
            print(f"[{nm}] sukces={r['sukces_pct']}%±{r['sd_binom_pp']} wl={r['wrong_lock_pct']}% "
                  f"(pierwszy-zly {r['wrong_lock_decomp']['pierwszy_zly']}/kradziez {r['wrong_lock_decomp']['kradziez']}) "
                  f"near-miss={r['near_miss_pct_of_fails']}% eff-no-det={r['eff_no_det_pct']}% "
                  f"age-dwell={r['age_at_dwell_entry_hist']['counts']}", flush=True)
    finally:
        client.close()
    env.close()
    json.dump({"model": CKPT, "seeds": [seeds[0], seeds[-1]], "n_per_level": len(seeds),
               "mask_pool": "45100+", "mask_map": {nm: MASK_SEED[nm] for nm in names},
               "base_pct": BASE, "results": results},
              open(os.path.join(OUT, out_name), "w"), indent=2)
    return results


def cmd_probe():
    """T1 — sonda rozdzielczosci: p=0.5 i L=5 na 46550-46569 (20 ep, poza pomiarem)."""
    seeds = list(range(46550, 46570))
    res = _run(seeds, ["probe_p0.50", "probe_L5"], "probe.json")
    a, b = res["probe_p0.50"]["sukces_pct"], res["probe_L5"]["sukces_pct"]
    lo, hi = BASE - 5, BASE
    if lo <= a <= hi and lo <= b <= hi:
        extra, decyzja = "p0.90", "os plaska -> dodaj p=0.9"
    elif a <= 15 and b <= 15:
        extra, decyzja = "p0.10", "klif -> dodaj p=0.1"
    else:
        extra, decyzja = None, "siatka bazowa bez zmian"
    out = {"probe_p0.50_pct": a, "probe_L5_pct": b, "base_pct": BASE, "band": [lo, hi],
           "extra_level": extra, "decyzja": decyzja}
    json.dump(out, open(os.path.join(OUT, "probe_decision.json"), "w"), indent=2)
    print(f"SONDA: p0.5={a}% L5={b}% | pasmo[{lo},{hi}] -> {decyzja} (extra={extra})", flush=True)


def cmd_measure():
    """T3 — pomiar pelny: wszystkie poziomy x 50 ep na 46500-46549 (parowane)."""
    seeds = list(range(46500, 46550))
    grid = json.load(open(os.path.join(OUT, "grid.json")))
    names = grid["levels"]
    # p0.00 pierwszy (kontrola spojnosci z precond-R)
    res = _run(seeds, names, "measure.json")
    p0 = res["p0.00"]["sukces_pct"]
    print(f"KONTROLA p0 vs {BASE}: {p0}% (rozbieznosc {round(p0 - BASE, 1)}pp; >10pp -> diagnoza)", flush=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    {"probe": cmd_probe, "measure": cmd_measure}[sys.argv[1]]()
