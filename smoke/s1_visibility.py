"""s1_visibility — bramka obserwowalnosci celu (NOWA, po ANEKS-1; na stale).

100 epizodow eksperta, sceny 43000-43099, T0. Widocznosc = seg_mask celu >= 3 px.
  G1: 100/100 scen z celem w kadrze w klatce t=0.
  G2: mediana udzialu klatek z widocznym celem w fazie DOLOTU
      (dopoki dystans poziomy do hover > 0.35 m) >= 0.90.
FAIL ktorejkolwiek -> STOP (blad spawnera/kamery), bez strojenia.

Wynik: results/s1_visibility.json ; kod wyjscia !=0 przy FAIL.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.liquidsight_env import DT_OBS, POLICY_STEPS  # noqa: E402
from expert.expert import make_expert_for  # noqa: E402
from train.common import load_cfg, make_env  # noqa: E402

SEEDS = list(range(43000, 43100))
LEVEL = "T0"
MIN_PX = 3
DEAD_ZONE = 0.35        # martwe pole terminalne (ANEKS-1): d_hor < 0.35 m


def main():
    cfg = load_cfg()
    env = make_env(cfg)
    t0_visible = 0
    approach_shares = []
    for s in SEEDS:
        obs, info = env.reset(scene_seed=s, level=LEVEL)
        expert = make_expert_for(env, obs, info, cfg)
        hover_xy = env.hover[:2]
        vis_approach, n_approach = 0, 0
        first_px = None
        done = False
        for k in range(POLICY_STEPS):
            o, i, done = env.step(expert.setpoint(k * DT_OBS), want_seg=True)
            px = int(i["seg_mask"].sum())
            if first_px is None:
                first_px = px                       # klatka t~0 (setpoint(0) trzyma start)
            d_hor = float(np.linalg.norm(o["kin"][:2] - hover_xy))
            if d_hor > DEAD_ZONE:
                n_approach += 1
                vis_approach += int(px >= MIN_PX)
            if done:
                break
        t0_visible += int((first_px or 0) >= MIN_PX)
        approach_shares.append(vis_approach / n_approach if n_approach else 1.0)
    env.close()

    g1 = t0_visible
    g2_med = float(np.median(approach_shares))
    g1_pass = g1 == len(SEEDS)
    g2_pass = g2_med >= 0.90
    out = {"n": len(SEEDS), "level": LEVEL, "min_px": MIN_PX, "dead_zone_m": DEAD_ZONE,
           "G1_t0_widoczny": f"{g1}/{len(SEEDS)}", "G1_pass": g1_pass,
           "G2_mediana_udzialu_dolot": round(g2_med, 3), "G2_pass": g2_pass,
           "G2_srednia": round(float(np.mean(approach_shares)), 3),
           "G2_min": round(float(np.min(approach_shares)), 3),
           "pass": g1_pass and g2_pass, "seeds": [SEEDS[0], SEEDS[-1]]}
    outpath = os.path.join(os.path.dirname(__file__), "..", "results", "s1_visibility.json")
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2)
    print(f"G1 (t0 widoczny): {g1}/{len(SEEDS)} -> {'PASS' if g1_pass else 'FAIL'}")
    print(f"G2 (mediana udzialu dolotu): {g2_med:.3f} (>=0.90) -> {'PASS' if g2_pass else 'FAIL'} "
          f"| srednia {out['G2_srednia']} min {out['G2_min']}")
    print("WYNIK:", "PASS" if out["pass"] else "FAIL — STOP", "->", outpath)
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    main()
