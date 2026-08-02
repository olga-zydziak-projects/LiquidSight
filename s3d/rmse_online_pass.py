"""s3d/rmse_online_pass.py — wtórna metryka: RMSE boxa ONLINE w pętli zamkniętej (PRE_3D0 §6).

Metryka pierwotna (sukces) nie potrzebuje GT → measure.py biega szybko (render seg tylko na
dostarczeniach). RMSE-online wymaga gęstego GT (render seg per tik), więc liczymy go osobno na
UDOKUMENTOWANYM PODZBIORZE n=30 (46500–46529, brak cichego capu) dla A0/A1 + po jednym seedzie
A2/A3 (mediana-precondition), na 3 nogach. Dense closed-loop RMSE = filtr/ZOH vs GT (mask*lock).

CLI: .venv/bin/python -m s3d.rmse_online_pass
"""
from __future__ import annotations
import json
import os
import sys

import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from models.policy_gc5 import PolicyGC5  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from train.s3b2r import CKPT  # noqa: E402
from s3b3.live_grounder import GrounderClient  # noqa: E402
from s3d.rollout import run_episode  # noqa: E402
from s3d.measure import build_filter, LEGS  # noqa: E402

OUT = os.path.join(_ROOT, "results", "s3d")
SUBSET = list(range(46500, 46530))            # n=30, udokumentowany podzbior
ARMS = [("A0", None), ("A1", None), ("A2", 45041), ("A3", 45041)]   # reprezentatywny seed


def main():
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    res = {"subset": [SUBSET[0], SUBSET[-1]], "n": len(SUBSET), "arms": {}}
    try:
        for arm, fseed in ARMS:
            res["arms"][arm] = {}
            for leg, (mode, param, mseed) in LEGS.items():
                filt = build_filter(arm, fseed, device)
                rmses = []
                for seed in SUBSET:
                    r = run_episode(env, client, seed, controller="policy", mode=mode, param=param,
                                    mask_seed=mseed, model=model, device=device, filt=filt,
                                    gt_every_tick=True)
                    if "rmse_online" in r:
                        rmses.append(r["rmse_online"])
                m = round(float(np.mean(rmses)), 5) if rmses else None
                res["arms"][arm][leg] = m
                print(f"[{arm} {leg}] rmse_online={m} (n={len(rmses)})", flush=True)
    finally:
        client.close(); env.close()
    json.dump(res, open(os.path.join(OUT, "rmse_online.json"), "w"), indent=2)
    print("zapisano rmse_online.json", flush=True)


if __name__ == "__main__":
    main()
