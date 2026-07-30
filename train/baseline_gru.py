"""baseline_gru — B1: charakteryzacja A_GRU (D7) wg speców ZAMROŻONYCH.

Per seed (45010-45019, SEKWENCYJNIE SOLO): pełny cykl v2 (ANEKS-4, run_cycle) +
nominal 100 (43000-43099) + drabina 7×50 (43100-43149) + saliency IoU (F3_GATE
par.6 W3). Wznawialne: results/baseline_gru/progress.jsonl + checkpoint per seed.

Zero nowych decyzji: model/procedura/zbiory/drabina/saliency przez referencję.
Uruchomienie: python -m train.baseline_gru run   (GPU na wyłączność!)
"""
from __future__ import annotations

import collections
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.liquidsight_env import POLICY_STEPS  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from models.arms import build_arm, part_params  # noqa: E402
from models.policy import _scale_setpoint  # noqa: E402
from train.common import (EpisodeStore, eval_policy_episode, get_device,  # noqa: E402
                          load_cfg, make_env)
from train.procedure import run_cycle  # noqa: E402
from task import split_state  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BCDIR = os.path.join(_ROOT, "data", "bc")
OUT = os.path.join(_ROOT, "results", "baseline_gru")
CKDIR = os.path.join(OUT, "ckpt")
DGDIR = os.path.join(_ROOT, "data", "baseline_dagger")
PROG = os.path.join(OUT, "progress.jsonl")

ARM, LR = "A_GRU", 1e-3
SEEDS = list(range(45010, 45020))
NOMINAL = list(range(43000, 43100))          # 100 scen T0
SWEEP = list(range(43100, 43150))            # 50 scen drabiny
LEVELS = ["T0", "T1", "T2", "T2a", "T2b", "T2c", "T3"]
SAL_EP = list(range(43100, 43110))           # pierwsze 10 sweep/poziom/seed
SAL_EVERY, SAL_MAX = 4, 15


def _log(s=""):
    print(s, flush=True)


def _stores():
    with open(os.path.join(BCDIR, "split.json")) as f:
        split = json.load(f)
    store = EpisodeStore()
    for s in split["train"]:
        store.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))
    val = EpisodeStore()
    for s in split["val"]:
        val.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))
    return store, val


def load_progress():
    done = {}
    if os.path.exists(PROG):
        with open(PROG) as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    done[r["seed"]] = r
    return done


# --- saliency IoU (F3_GATE par.6 W3) ----------------------------------------
def _saliency_frame(model, obs, h, mask_target, device) -> float:
    rgb = torch.as_tensor(np.ascontiguousarray(obs["rgb"]), device=device).float()
    rgb = rgb.unsqueeze(0).requires_grad_(True)
    kin = torch.as_tensor(obs["kin"], dtype=torch.float32, device=device).unsqueeze(0)
    dt = torch.as_tensor(obs["dt"], dtype=torch.float32, device=device).unsqueeze(0)
    feat = model.encoder(rgb)
    x = torch.cat([feat, kin, dt], dim=-1)
    h2 = model.core.step(x, h.detach())
    sp = _scale_setpoint(model.head(h2))
    model.zero_grad(set_to_none=True)
    sp.abs().sum().backward()
    sal = rgb.grad.abs().squeeze(0).amax(dim=-1)          # (64,64) max po kanałach
    n = sal.numel()
    k2 = max(1, int(round(0.02 * n)))                     # top-2% pikseli
    thr = torch.kthvalue(sal.flatten(), n - k2).values
    pred = sal >= thr
    mt = torch.as_tensor(mask_target, device=device)
    inter = (pred & mt).sum().float()
    union = (pred | mt).sum().float()
    return float(inter / union) if union > 0 else 0.0


def saliency_level(model, env, level, cfg, device) -> list:
    ious = []
    for s in SAL_EP:
        obs, info = env.reset(scene_seed=s, level=level)   # 3a
        h = model.init_hidden(1, device)
        used, entered = 0, False
        for k in range(POLICY_STEPS):
            st = env.env._getDroneStateVector(0)
            pos = split_state(st)["pos"]
            quat = split_state(st)["quat"]
            dist = float(np.linalg.norm(pos - env.hover))
            if (not entered) and (k % SAL_EVERY == 0) and used < SAL_MAX:
                _, seg = drone_camera(env.env.CLIENT, pos, quat, env.res, want_seg=True)
                mask = (seg == env.scene["target_id"])
                with torch.enable_grad():
                    ious.append(_saliency_frame(model, obs, h, mask, device))
                used += 1
            if dist <= cfg["r_goal"]:
                entered = True
            act, h = model.act(obs, h, device)
            obs, info, done = env.step(act)
            if done:
                break
    return ious


# --- pełny bieg per seed ----------------------------------------------------
def run_seed(seed, cfg, device):
    store, val = _stores()
    env = make_env(cfg)
    dg = os.path.join(DGDIR, str(seed))
    t0 = time.perf_counter()
    model, stages = run_cycle(ARM, LR, seed, cfg, env, store, val, device, dg, log=_log)
    sec_cykl = time.perf_counter() - t0

    model.eval()
    # nominal 100
    succ, fails = 0, collections.Counter()
    for s in NOMINAL:
        r = eval_policy_episode(env, model, s, "T0", cfg, device)
        succ += int(r["success"])
        if not r["success"]:
            fails[r["fail_type"]] += 1
    nominal_pct = round(100 * succ / len(NOMINAL), 1)

    # drabina 7×50
    t_lad = time.perf_counter()
    drabina = {}
    for level in LEVELS:
        n = 0
        for s in SWEEP:
            n += int(eval_policy_episode(env, model, s, level, cfg, device)["success"])
        drabina[level] = round(100 * n / len(SWEEP), 1)
    sec_drabina = time.perf_counter() - t_lad

    # saliency IoU per poziom
    t_sal = time.perf_counter()
    saliency = {}
    for level in LEVELS:
        ious = saliency_level(model, env, level, cfg, device)
        saliency[level] = {"mean": round(float(np.mean(ious)), 4),
                           "sd": round(float(np.std(ious)), 4), "n": len(ious)}
    sec_sal = time.perf_counter() - t_sal
    env.close()

    os.makedirs(CKDIR, exist_ok=True)
    ckpt = os.path.join(CKDIR, f"A_GRU_s{seed}.pt")
    torch.save(model.state_dict(), ckpt)

    return {"arm": ARM, "lr": LR, "seed": seed, "nominal_pct": nominal_pct,
            "nominal_succ": succ, "porazki": dict(fails), "drabina": drabina,
            "saliency": saliency,
            "stages": [{"round": s["round"], "best_val": s["best_val"],
                        "rollout_succ_pct": s["rollout_succ_pct"],
                        "sec_rollout": s["sec_rollout"], "sec_train": s["sec_train"]}
                       for s in stages],
            "sec_cykl": round(sec_cykl, 1), "sec_drabina": round(sec_drabina, 1),
            "sec_saliency": round(sec_sal, 1), "ckpt": ckpt}


def main():
    os.makedirs(OUT, exist_ok=True)
    device = get_device()
    cfg = load_cfg()
    if device != "cuda":
        _log("UWAGA: brak CUDA — bieg na CPU (czasy niemiarodajne).")
    done = load_progress()
    _log(f"B1 baseline A_GRU @1e-3 | device={device} | ukończone: {sorted(done)}")
    for i, seed in enumerate(SEEDS, 1):
        if seed in done:
            r = done[seed]
            _log(f"[{i}/10] seed {seed} WCZYTANY nominal={r['nominal_pct']}% "
                 f"({r['sec_cykl']:.0f}s)")
            continue
        _log(f"[{i}/10] seed {seed}: pełny cykl v2 + nominal + drabina + saliency ...")
        rec = run_seed(seed, cfg, device)
        with open(PROG, "a") as f:
            f.write(json.dumps(rec) + "\n")
        _log(f"[{i}/10] seed {seed}: nominal={rec['nominal_pct']}% "
             f"drabina={rec['drabina']} cykl={rec['sec_cykl']:.0f}s "
             f"(drabina {rec['sec_drabina']:.0f}s sal {rec['sec_saliency']:.0f}s)")
    _log("B1 KONIEC — wszystkie seedy ukończone.")


if __name__ == "__main__":
    main()
