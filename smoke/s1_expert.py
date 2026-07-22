"""s1_expert — obwiednia eksperta privileged na T0.

% sukcesu na 100 epizodach (sceny 43000-43099, poziom T0) + rozklad typow
porazki rozdzielnie: brak-dolotu/dwell vs katastrofa (tilt/crash/geofence/
contact). Oczekiwane ~0 katastrof (D1b).

Wynik: results/s1_expert.json
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.liquidsight_env import LiquidSightEnv  # noqa: E402
from expert.expert import run_expert_episode  # noqa: E402

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "env_f3.json")
SEEDS = list(range(43000, 43100))
LEVEL = "T0"


def main():
    with open(CFG_PATH) as f:
        j = json.load(f)
    e = j["env"]
    cfg = {"r_goal": e["r_goal"], "z_hover": e["z_hover"], "t_dwell": e["t_dwell"],
           "v_max": j["ekspert"]["v_max"], "t_ramp_min": j["ekspert"]["t_ramp_min"]}
    env = LiquidSightEnv(r_goal=cfg["r_goal"], z_hover=cfg["z_hover"], t_dwell=cfg["t_dwell"])

    succ = 0
    fail_types = collections.Counter()
    catastrophe = 0
    non_arrival = 0
    for s in SEEDS:
        r = run_expert_episode(env, s, LEVEL, cfg)
        if r["success"]:
            succ += 1
        else:
            fail_types[r["fail_type"]] += 1
            if r["catastrophe"]:
                catastrophe += 1
            else:
                non_arrival += 1
    env.close()

    n = len(SEEDS)
    out = {
        "level": LEVEL, "seeds": [SEEDS[0], SEEDS[-1]], "n": n,
        "sukces": succ, "sukces_pct": round(100 * succ / n, 1),
        "porazki_typy": dict(fail_types),
        "katastrofy": catastrophe, "brak_dolotu_dwell": non_arrival,
        "config": cfg,
    }
    outpath = os.path.join(os.path.dirname(__file__), "..", "results", "s1_expert.json")
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2)
    print(f"ekspert T0: {succ}/{n} = {out['sukces_pct']}% | "
          f"katastrofy={catastrophe} brak-dolotu/dwell={non_arrival} | typy={dict(fail_types)}")
    print("->", outpath)


if __name__ == "__main__":
    main()
