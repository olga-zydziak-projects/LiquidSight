"""s3b_expert_designated — ekspert desygnowany na scenie atrybutowej 3b (T3).

Ekspert privileged celuje w GT wskazanego (designated_id); logika najazdu bez
zmian (ta sama HoverExpert). 100 epizodow na scenach eval 46500-46599 (scene_type
3b). Raport: % sukcesu + rozklad porazek z wrong-lock jako OSOBNA kolumna (D5).
Oczekiwane: ~100% sukcesu, wrong-lock 0 z konstrukcji (ekspert nie celuje w inny).

Wynik: results/s3b1/s3b_expert_designated.json
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.liquidsight_env import LiquidSightEnv  # noqa: E402
from env.scene_attr import scene_params  # noqa: E402
from expert.expert import run_expert_episode  # noqa: E402

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "env_f3.json")
SEEDS = list(range(46500, 46600))


def main():
    with open(CFG_PATH) as f:
        j = json.load(f)
    e = j["env"]
    cfg = {"r_goal": e["r_goal"], "z_hover": e["z_hover"], "t_dwell": e["t_dwell"],
           "v_max": j["ekspert"]["v_max"], "t_ramp_min": j["ekspert"]["t_ramp_min"]}
    env = LiquidSightEnv(r_goal=cfg["r_goal"], z_hover=cfg["z_hover"], t_dwell=cfg["t_dwell"])

    succ = 0
    fails = collections.Counter()
    cat = 0
    cells = collections.Counter()
    per_cell_succ = collections.Counter()
    for s in SEEDS:
        K, A = scene_params(s)
        cells[(K, A)] += 1
        r = run_expert_episode(env, s, "T0", cfg, scene_type="3b")
        if r["success"]:
            succ += 1
            per_cell_succ[(K, A)] += 1
        else:
            fails[r["fail_type"]] += 1
            if r["catastrophe"]:
                cat += 1
    env.close()

    n = len(SEEDS)
    wrong_lock = fails.get("wrong_lock", 0)
    no_arrival = fails.get("no_arrival", 0)
    dwell = fails.get("dwell", 0)
    out = {
        "n": n, "sukces": succ, "sukces_pct": round(100 * succ / n, 1),
        "wrong_lock": wrong_lock, "no_arrival": no_arrival, "dwell": dwell,
        "katastrofy": cat, "fail_types": dict(fails),
        "per_cell": {f"K{K}_{A}": f"{per_cell_succ[(K,A)]}/{cells[(K,A)]}"
                     for (K, A) in sorted(cells)},
    }
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results", "s3b1"), exist_ok=True)
    outpath = os.path.join(os.path.dirname(__file__), "..", "results", "s3b1",
                           "s3b_expert_designated.json")
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2)
    print(f"ekspert desygnowany 3b: {succ}/{n} = {out['sukces_pct']}% | "
          f"wrong-lock={wrong_lock} no-arrival={no_arrival} dwell={dwell} katastrofy={cat}")
    print(f"per-cell: {out['per_cell']}")
    print(f"-> {outpath}")


if __name__ == "__main__":
    main()
