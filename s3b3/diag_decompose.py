"""diag_decompose — DIAG-3B T5(a): dekompozycja straty 88 pp na (i)/(ii)/(iii).

Frozen polityka (S3b2) + grounder LIVE (YOLO-World), trzy tryby BRAMKOWANIA kanału
(diagnostyka — polityka/config/kontrakt BEZ ZMIAN; różni się tylko, KTÓRE detekcje
trafiają do kanału, żeby przypisać składowe straty):

  live       : dostarczaj box+conf YOLO na KAŻDYM ticku (= G1, ~12%).
  gate_infov : dostarczaj tylko gdy wskazany W FOV (tłumi fałszywe locki poza-FOV).
  oracle     : dostarczaj tylko gdy W FOV I YOLO trafił we wskazanego (tylko poprawne locki).

Rozkład (dodaje się do 88 pp z konstrukcji):
  (i)  poza-FOV fałszywe locki  = gate_infov% − live%
  (ii) błędy groundera w FOV    = oracle% − gate_infov%
  (iii) conf-shift + polityka   = 100% (sufit GT-fed) − oracle%

50 ep sweep 46600-46649 (te same sceny). Uruchomienie:
  .venv/bin/python -m s3b3.diag_decompose
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
from env.liquidsight_env import DT_OBS, POLICY_STEPS  # noqa: E402
from env.scene_attr import bbox_from_mask, scene_params  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from models.policy_gc import PolicyGC  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from task import split_state  # noqa: E402
from s3b3.live_grounder import TICK_EVERY, GrounderClient, LiveTargetTracker, iou  # noqa: E402

OUT = os.path.join(_ROOT, "results", "diag3b")
CKPT = os.path.join(_ROOT, "ckpt", "s3b2", "policy_gc.pt")
MIN_PX = 3
SWEEP = list(range(46600, 46650))
MODES = ["live", "gate_infov", "oracle"]


def run_mode(env, policy, client, mode, device):
    succ = wl = na = 0
    fails = collections.Counter()
    for seed in SWEEP:
        obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
        command, did = info["command"], info["designated_id"]
        h = policy.init_hidden(1, device)
        tracker = LiveTargetTracker()
        done = False
        for k in range(POLICY_STEPS):
            tgt, _ = tracker.vector(k)
            action, h = policy.act(obs, tgt, h, device)
            obs, info, done = env.step(action)
            if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
                box, conf, _ = client.query(info["rgb256"], command)
                # GT: wskazany w FOV? (seg z biezacej pozy) + dopasowanie
                st = env.env._getDroneStateVector(0); s = split_state(st)
                _, seg = drone_camera(env.env.CLIENT, s["pos"], s["quat"], 256, want_seg=True)
                in_fov = int((seg == did).sum()) >= MIN_PX
                dbox = bbox_from_mask(seg, did)
                deliver = True
                if mode == "gate_infov":
                    deliver = in_fov
                elif mode == "oracle":
                    deliver = in_fov and (box is not None) and (iou(box, dbox) >= 0.5)
                if deliver:
                    tracker.observe(k, box, conf)
            if done:
                break
        if info["success"]:
            succ += 1
        else:
            fails[info["fail_type"]] += 1
    n = len(SWEEP)
    return {"mode": mode, "sukces_pct": round(100 * succ / n, 1),
            "wrong_lock": fails.get("wrong_lock", 0), "no_arrival": fails.get("no_arrival", 0),
            "dwell": fails.get("dwell", 0), "fail_types": dict(fails)}


def main():
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    policy = PolicyGC().to(device)
    policy.load_state_dict(torch.load(CKPT, map_location=device)); policy.eval()
    client = GrounderClient()
    res = {}
    try:
        for mode in MODES:
            r = run_mode(env, policy, client, mode, device)
            res[mode] = r
            print(f"  {mode}: sukces {r['sukces_pct']}% (wrong-lock {r['wrong_lock']}, "
                  f"no-arrival {r['no_arrival']}, dwell {r['dwell']})", flush=True)
    finally:
        client.close()
    env.close()

    ceiling = 100.0
    live, gate, oracle = res["live"]["sukces_pct"], res["gate_infov"]["sukces_pct"], res["oracle"]["sukces_pct"]
    decomp = {
        "sufit_GTfed_pct": ceiling, "live_pct": live,
        "strata_total_pp": round(ceiling - live, 1),
        "i_pozaFOV_falszywe_locki_pp": round(gate - live, 1),
        "ii_bledy_groundera_wFOV_pp": round(oracle - gate, 1),
        "iii_conf_shift_polityka_pp": round(ceiling - oracle, 1),
        "modes": res,
    }
    json.dump(decomp, open(os.path.join(OUT, "decompose.json"), "w"), indent=2)
    print(f"\nDEKOMPOZYCJA 88pp: (i) poza-FOV={decomp['i_pozaFOV_falszywe_locki_pp']}pp "
          f"(ii) grounder-in-FOV={decomp['ii_bledy_groundera_wFOV_pp']}pp "
          f"(iii) conf+polityka={decomp['iii_conf_shift_polityka_pp']}pp")


if __name__ == "__main__":
    main()
