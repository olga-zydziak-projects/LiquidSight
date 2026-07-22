"""s1_axis_render — podglad osi teksturowej OOD (D6).

Po 4 klatki z kamery drona (te same 4 sceny na kazdym poziomie -> jedyna
roznica to rodzina tekstur / dystraktory) dla T0/T1/T2/T3.
Klatka pobrana w locie (tik snapshot), gdy dron patrzy w scene.
Zapis: results/axis_preview/<level>_<seed>.png

Te same scene_seedy na wszystkich poziomach czynia porownanie osi czystym
(geometria identyczna; zmienia sie kontekst, nie cel — D6).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.liquidsight_env import DT_OBS, LiquidSightEnv  # noqa: E402
from env.scene_builder import LEVEL_NAMES  # noqa: E402
from expert.expert import make_expert_for  # noqa: E402

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "env_f3.json")
SEEDS = [43100, 43112, 43125, 43137]   # 4 sceny, te same na kazdym poziomie
T_SNAP = 40                            # tik polityki snapshotu (dron w locie)


def main():
    with open(CFG_PATH) as f:
        j = json.load(f)
    e = j["env"]
    cfg = {"r_goal": e["r_goal"], "z_hover": e["z_hover"], "t_dwell": e["t_dwell"],
           "v_max": j["ekspert"]["v_max"], "t_ramp_min": j["ekspert"]["t_ramp_min"]}
    env = LiquidSightEnv(r_goal=cfg["r_goal"], z_hover=cfg["z_hover"], t_dwell=cfg["t_dwell"])

    outdir = os.path.join(os.path.dirname(__file__), "..", "results", "axis_preview")
    os.makedirs(outdir, exist_ok=True)
    saved = []
    for level in LEVEL_NAMES:
        for seed in SEEDS:
            obs, info = env.reset(scene_seed=seed, level=level)
            expert = make_expert_for(env, obs, info, cfg)
            done = False
            for k in range(T_SNAP):
                obs, info, done = env.step(expert.setpoint(k * DT_OBS))
                if done:
                    break
            path = os.path.join(outdir, f"{level}_{seed}.png")
            Image.fromarray(np.ascontiguousarray(obs["rgb"], dtype=np.uint8)).save(path)
            saved.append(os.path.basename(path))
    env.close()
    print(f"zapisano {len(saved)} klatek do {outdir}")
    print("  poziomy:", LEVEL_NAMES, "| seedy:", SEEDS, "| snapshot tik:", T_SNAP)


if __name__ == "__main__":
    main()
