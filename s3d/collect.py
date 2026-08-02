"""s3d/collect.py — kolektor danych OFFLINE do treningu filtrów (PRE_3D0 §4).

Ekspert leci scenę (jak BC 3b), żywy YOLO karmi kanał pod maskami degradacji; logujemy
per tik: wejście filtra [bx,by,bw,bh,has_delivery,age_n] (kanał ZOH) + etykietę GT box
(render seg256 per tik; None poza kadrem → maskowane). Pule: train 48000–48299,
val 48300–48399. Maski 45200–45209 (rodzina G2, ROZŁĄCZNE z pomiarowymi 45102/45105).
Reżimy mieszane: clean / bernoulli p=0.5 / burst L=5 (cykl po indeksie).

CLI: .venv/bin/python -m s3d.collect {train|val|smoke}
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
import time

import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import POLICY_STEPS  # noqa: E402
from expert.expert import make_expert_for  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from s3b3.live_grounder import GrounderClient  # noqa: E402
from s3d.rollout import run_episode  # noqa: E402

OUT = os.path.join(_ROOT, "results", "s3d")
# reżim -> (mode, param, mask_seed)   [maski 45200+ rozłączne z 45102/45105]
REGIMES = [("clean", 0.0, 45200), ("bernoulli", 0.5, 45201), ("burst", 5.0, 45202)]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def collect(pool_seeds, tag):
    os.makedirs(OUT, exist_ok=True)
    cfg = load_cfg(); env = make_env(cfg); device = get_device()
    ef = lambda e, o, i: make_expert_for(e, o, i, cfg)
    client = GrounderClient()
    T = POLICY_STEPS
    X = np.zeros((len(pool_seeds), T, 6), np.float32)
    Y = np.zeros((len(pool_seeds), T, 4), np.float32)
    M = np.zeros((len(pool_seeds), T), np.float32)
    meta = []
    t0 = time.time()
    try:
        for i, seed in enumerate(pool_seeds):
            mode, param, mseed = REGIMES[i % len(REGIMES)]
            r = run_episode(env, client, seed, controller="expert", mode=mode, param=param,
                            mask_seed=mseed, expert_factory=ef,
                            gt_every_tick=True, log_input=True)
            L = r["X"].shape[0]
            X[i, :L] = r["X"]; Y[i, :L] = r["Y"]; M[i, :L] = r["Ymask"]
            meta.append({"seed": seed, "regime": mode, "param": param, "mask_seed": mseed,
                         "length": int(L), "n_gt": int(r["Ymask"].sum()),
                         "success": r["success"], "fail_type": r["fail_type"]})
            if (i + 1) % 20 == 0:
                dt = time.time() - t0
                print(f"  [{tag}] {i+1}/{len(pool_seeds)}  ({dt/(i+1):.2f}s/ep)", flush=True)
    finally:
        client.close(); env.close()
    path = os.path.join(OUT, f"data_{tag}.npz")
    np.savez_compressed(path, X=X, Y=Y, M=M,
                        seeds=np.array(pool_seeds), regimes=np.array([m["regime"] for m in meta]))
    metapath = os.path.join(OUT, f"data_{tag}_meta.json")
    json.dump({"tag": tag, "n": len(pool_seeds), "seeds": [pool_seeds[0], pool_seeds[-1]],
               "regimes": REGIMES, "gt_coverage": float(M.mean()),
               "wall_s": round(time.time() - t0, 1), "episodes": meta},
              open(metapath, "w"), indent=2)
    print(f"[{tag}] zapisano {path}  sha256={sha256(path)[:16]}…  "
          f"GT-coverage={M.mean():.3f}  wall={time.time()-t0:.1f}s", flush=True)
    return path


def main(which):
    if which == "smoke":
        collect([48000, 48001, 48002], "smoke")
    elif which == "train":
        collect(list(range(48000, 48300)), "train")
    elif which == "val":
        collect(list(range(48300, 48400)), "val")
    else:
        raise SystemExit("usage: collect {train|val|smoke}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "smoke")
