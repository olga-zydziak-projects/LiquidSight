"""observability — diagnostyka pierwotnej przyczyny P1 FAIL.

Mierzy, czy cel jest w ogole w kadrze kamery przedniej podczas zadania
(sterowanie ekspertem), i krzyzuje widocznosc z sukcesem polityki. Jesli
sukces nie przekracza sufitu widocznosci, waskim gardlem jest OBSERWOWALNOSC
(kanal percepcji), nie pojemnosc/trening instrumentu.

Wynik -> results/p1_observability.json
"""
import json
import os

import numpy as np
import torch

from env.liquidsight_env import DT_OBS, POLICY_STEPS
from expert.expert import make_expert_for
from models.policy import Policy
from train.common import eval_policy_episode, get_device, load_cfg, make_env

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEEDS = list(range(43000, 43100))     # te same sceny co P1
LEVEL = "T0"


def target_visible_frames(env, seed, cfg):
    obs, info = env.reset(scene_seed=seed, level=LEVEL)
    ex = make_expert_for(env, obs, info, cfg)
    vis = 0
    for k in range(POLICY_STEPS):
        o, i, d = env.step(ex.setpoint(k * DT_OBS), want_seg=True)
        if int(i["seg_mask"].sum()) > 0:
            vis += 1
        if d:
            break
    return vis


def main():
    cfg = load_cfg()
    device = get_device()
    env = make_env(cfg)

    vis = {s: target_visible_frames(env, s, cfg) for s in SEEDS}

    ckpts = {"bc": os.path.join(_ROOT, "ckpt", "gru", "bc.pt"),
             "dagger": os.path.join(_ROOT, "ckpt", "gru", "dagger.pt")}
    succ = {}
    for name, path in ckpts.items():
        m = Policy().to(device)
        m.load_state_dict(torch.load(path, map_location=device))
        m.eval()
        succ[name] = {s: eval_policy_episode(env, m, s, LEVEL, cfg, device)["success"]
                      for s in SEEDS}
    env.close()

    n = len(SEEDS)
    n_vis = sum(1 for s in SEEDS if vis[s] > 0)
    frames = np.array([vis[s] for s in SEEDS])
    out = {
        "n_scen": n, "level": LEVEL, "seeds": [SEEDS[0], SEEDS[-1]],
        "cel_widoczny_scen": n_vis, "cel_widoczny_pct": round(100 * n_vis / n, 1),
        "klatek_z_celem_srednia": round(float(frames.mean()), 2),
        "klatek_z_celem_mediana": int(np.median(frames)),
        "klatek_z_celem_max": int(frames.max()),
        "sufit_widocznosci_pct": round(100 * n_vis / n, 1),
    }
    for name in ckpts:
        ns = sum(succ[name].values())
        sv = sum(1 for s in SEEDS if succ[name][s] and vis[s] > 0)
        snv = sum(1 for s in SEEDS if succ[name][s] and vis[s] == 0)
        out[name] = {"sukces": ns, "sukces_pct": round(100 * ns / n, 1),
                     "sukces_przy_widocznym": sv, "sukces_przy_niewidocznym": snv}
    with open(os.path.join(_ROOT, "results", "p1_observability.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
