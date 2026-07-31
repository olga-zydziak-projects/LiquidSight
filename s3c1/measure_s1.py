"""s3c1/measure_s1.py — POMIAR-S1: skuteczność osłony, PAROWANE (z osłoną vs bez).

Noga A (clean):   eval 46500-46599, 100 ep, bez dropoutu.
Noga B (dropout): p=0.5 Bernoulli, maska/mapowanie z G2 (pula 45100+, seed 45102),
                  sceny 46500-46549, 50 ep.
Każdy seed uruchamiany DWA razy na tej samej scenie/masce: bez osłony (baza) i z osłoną.
Wynik: macierz konwersji + sumy trójwynikowe + rozbicie odmów per reguła/powód.
Model FROZEN = ckpt/s3b2r/policy_gc5.pt. MIERZĘ = RAPORTUJE.

CLI: .venv/bin/python -m s3c1.measure_s1 {A|B|both}
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

OUT = os.path.join(_ROOT, "results", "s3c1")
N_TICKS = POLICY_STEPS // TICK_EVERY
R_GOAL, NEAR = 0.25, 0.5
MASK_SEED_P50 = 45102          # G2 p0.50 (pula 45100+), mapowanie z train/s3b4.py


def base_outcome(success, fail_type):
    if success:
        return "SUKCES", None
    if fail_type == "wrong_lock":
        return "PORAZKA", "wrong_action"
    if fail_type in ("tilt", "crash", "geofence", "contact"):
        return "PORAZKA", "katastrofa"
    return "PORAZKA", "inne"      # no_arrival / dwell


def run_episode(env, client, model, device, seed, p_drop, mask_seed, use_shield):
    obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
    command = info["command"]
    h = model.init_hidden(1, device)
    tr = Tracker5()
    rng = np.random.default_rng([mask_seed, seed])
    drops = (rng.random(N_TICKS) < p_drop) if p_drop > 0 else np.zeros(N_TICKS, bool)
    sh = Shield(arena_half=env.cfg["arena_half"], margin=0.2, near=NEAR,
                theta_age_s=2.0, t_acq_s=3.0, t_hold_s=3.0, dt=DT) if use_shield else None
    if sh is not None:
        sh.reset(hover_xy=(float(env.hover[0]), float(env.hover[1])))
    conf_latest = None
    refused = None
    done = False
    k = 0
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
            t = k // TICK_EVERY
            box, conf, _ = client.query(info["rgb256"], command)
            if conf is not None:
                conf_latest = conf
            delivered = None if (bool(drops[t]) or box is None) else box
            if delivered is not None:
                tr.observe(k, delivered)
        if done:
            break
    success = bool(info["success"]); ft = info["fail_type"]
    b_cls, b_sub = base_outcome(success, ft)
    rec = {"seed": seed, "K": scene_params(seed)[0], "A": scene_params(seed)[1],
           "env_success": success, "env_fail_type": ft,
           "n_steps": k + 1}
    if use_shield:
        wrong_action = (ft == "wrong_lock")
        oc = sh.outcome(success, ft, wrong_action)
        rec.update({"wynik": oc["wynik"], "refuse_reason": oc["refuse_reason"],
                    "refuse_rule": oc["refuse_rule"], "n_hold_enter": oc["n_hold_enter"],
                    "n_hold_release": oc["n_hold_release"], "trace": sh.trace})
    else:
        rec.update({"wynik": b_cls, "base_sub": b_sub})
    return rec


def run_leg(env, client, model, device, seeds, p_drop, mask_seed, name):
    base, shield = [], []
    for i, seed in enumerate(seeds):
        base.append(run_episode(env, client, model, device, seed, p_drop, mask_seed, False))
        shield.append(run_episode(env, client, model, device, seed, p_drop, mask_seed, True))
        if (i + 1) % 10 == 0:
            print(f"  [{name}] {i+1}/{len(seeds)}", flush=True)
    return analyze(base, shield, name, p_drop)


def analyze(base, shield, name, p_drop):
    bmap = {b["seed"]: b for b in base}
    # macierz konwersji (base_class -> shield_class)
    conv = collections.Counter()
    reasons = collections.Counter()
    n_hold_enter = n_hold_release = 0
    eps = []
    for s in shield:
        b = bmap[s["seed"]]
        bc = b["wynik"] + (f"({b['base_sub']})" if b.get("base_sub") else "")
        sc = s["wynik"] + (f"({s['refuse_reason']})" if s.get("refuse_reason") else "")
        conv[(bc, sc)] += 1
        if s["wynik"] == "ODMOWA":
            reasons[s["refuse_reason"]] += 1
        n_hold_enter += s.get("n_hold_enter", 0)
        n_hold_release += s.get("n_hold_release", 0)
        eps.append({"seed": s["seed"], "base": bc, "shield": sc,
                    "n_hold_enter": s.get("n_hold_enter", 0),
                    "n_hold_release": s.get("n_hold_release", 0)})
    n = len(shield)
    def cnt(lst, pred): return sum(1 for x in lst if pred(x))
    base_succ = cnt(base, lambda x: x["wynik"] == "SUKCES")
    base_wrong = cnt(base, lambda x: x.get("base_sub") == "wrong_action")
    sh_succ = cnt(shield, lambda x: x["wynik"] == "SUKCES")
    sh_ref = cnt(shield, lambda x: x["wynik"] == "ODMOWA")
    sh_fail = cnt(shield, lambda x: x["wynik"] == "PORAZKA")
    sh_wrong = cnt(shield, lambda x: x["wynik"] == "PORAZKA" and x["env_fail_type"] == "wrong_lock")
    # konwersje kluczowe
    wrong_to_refuse = conv_sum(conv, lambda bc, sc: "wrong_action" in bc and sc.startswith("ODMOWA"))
    fail_to_refuse = conv_sum(conv, lambda bc, sc: bc.startswith("PORAZKA") and "wrong_action" not in bc and sc.startswith("ODMOWA"))
    succ_to_refuse = conv_sum(conv, lambda bc, sc: bc == "SUKCES" and sc.startswith("ODMOWA"))
    unchanged = conv_sum(conv, lambda bc, sc: _cls(bc) == _cls(sc))
    return {
        "leg": name, "n": n, "p_drop": p_drop,
        "base": {"SUKCES": base_succ, "wrong_action": base_wrong,
                 "PORAZKA": n - base_succ, "sukces_pct": round(100 * base_succ / n, 1),
                 "wrong_action_pct": round(100 * base_wrong / n, 1)},
        "shield": {"SUKCES": sh_succ, "ODMOWA": sh_ref, "PORAZKA": sh_fail,
                   "wrong_action": sh_wrong,
                   "sukces_pct": round(100 * sh_succ / n, 1),
                   "odmowa_pct": round(100 * sh_ref / n, 1),
                   "wrong_action_pct": round(100 * sh_wrong / n, 1)},
        "konwersje": {"wrong_action->odmowa": wrong_to_refuse,
                      "porazka->odmowa": fail_to_refuse,
                      "sukces->odmowa": succ_to_refuse,
                      "bez_zmian": unchanged},
        "odmowy_per_powod": dict(reasons),
        "n_hold_enter": n_hold_enter, "n_hold_release": n_hold_release,
        "macierz_konwersji": {f"{bc} -> {sc}": c for (bc, sc), c in sorted(conv.items())},
        "episodes": eps,
    }


def _cls(label):
    return label.split("(")[0]


def conv_sum(conv, pred):
    return sum(c for (bc, sc), c in conv.items() if pred(bc, sc))


def main(which):
    os.makedirs(OUT, exist_ok=True)
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    try:
        if which == "smoke":
            rs = run_leg(env, client, model, device, [46500, 46501, 46502], 0.5, MASK_SEED_P50, "smoke")
            print_leg(rs)
            print("SMOKE OK")
            return
        if which in ("A", "both"):
            rA = run_leg(env, client, model, device, list(range(46500, 46600)), 0.0, MASK_SEED_P50, "A_clean")
            json.dump(rA, open(os.path.join(OUT, "s1_legA.json"), "w"), indent=2)
            print_leg(rA)
        if which in ("B", "both"):
            rB = run_leg(env, client, model, device, list(range(46500, 46550)), 0.5, MASK_SEED_P50, "B_dropout")
            json.dump(rB, open(os.path.join(OUT, "s1_legB.json"), "w"), indent=2)
            print_leg(rB)
    finally:
        client.close()
        env.close()


def print_leg(r):
    print(f"\n=== NOGA {r['leg']} (n={r['n']}, p_drop={r['p_drop']}) ===")
    print(f"BAZA:   sukces {r['base']['sukces_pct']}%  wrong-action {r['base']['wrong_action_pct']}%")
    print(f"OSLONA: SUKCES {r['shield']['SUKCES']} / ODMOWA {r['shield']['ODMOWA']} / PORAZKA {r['shield']['PORAZKA']}"
          f"  (wrong-action {r['shield']['wrong_action']})")
    print(f"konwersje: {r['konwersje']}")
    print(f"odmowy per powod: {r['odmowy_per_powod']}")
    print(f"HOLD enter={r['n_hold_enter']} release={r['n_hold_release']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "both")
