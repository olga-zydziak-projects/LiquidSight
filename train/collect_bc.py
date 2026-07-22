"""collect_bc — dane BC (T2): 300 epizodow eksperta na T0, sceny 44000-44299.

Probka na tik kamery: (rgb, kin, dt) -> setpoint eksperta. Zapis npz per epizod
do data/bc/. 10% epizodow (co 10-ty) oznaczone jako walidacja monitoringowa
(bez strojenia na niej) w data/bc/split.json.
"""
import json
import os
import time

import numpy as np

from train.common import collect_expert_episode, load_cfg, make_env

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTDIR = os.path.join(_ROOT, "data", "bc")
SEEDS = list(range(44000, 44300))       # 300 epizodow T0
LEVEL = "T0"
VAL_EVERY = 10                          # co 10-ty -> walidacja monitoringowa (10%)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    cfg = load_cfg()
    env = make_env(cfg)
    train_ids, val_ids = [], []
    n_succ = 0
    t0 = time.perf_counter()
    for i, s in enumerate(SEEDS):
        ep = collect_expert_episode(env, s, LEVEL, cfg)
        n_succ += int(ep["success"])
        path = os.path.join(OUTDIR, f"ep_{s}.npz")
        np.savez_compressed(path, rgb=ep["rgb"], kin=ep["kin"], dt=ep["dt"],
                            setpoint=ep["setpoint"], length=ep["length"],
                            success=ep["success"])
        (val_ids if i % VAL_EVERY == 0 else train_ids).append(s)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(SEEDS)} | success dotad {n_succ}/{i+1} | {time.perf_counter()-t0:.0f}s")
    env.close()
    dt = time.perf_counter() - t0
    split = {"train": train_ids, "val": val_ids, "level": LEVEL,
             "n_total": len(SEEDS), "n_success": n_succ,
             "seconds": round(dt, 1)}
    with open(os.path.join(OUTDIR, "split.json"), "w") as f:
        json.dump(split, f, indent=2)
    print(f"BC dane: {len(SEEDS)} epizodow | success {n_succ}/{len(SEEDS)} | "
          f"train {len(train_ids)} / val {len(val_ids)} | {dt:.0f}s")


if __name__ == "__main__":
    main()
