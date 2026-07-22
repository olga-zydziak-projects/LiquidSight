"""s1_env_det — determinizm srodowiska (kontrakt fazy 3).

Pelny env pod ekspertem w petli. Dla scene_seed 43100 (T0) i 43149 (T3):
2 NIEZALEZNE przebiegi (swiezy env), SHA256 strumieni rgb / kin / setpoint.
PASS = bit-w-bit identyczne w obu przebiegach dla OBU seedow.
FAIL -> STOP z diagnoza (NIE "naprawiac" przez zmiane flag renderu).

Wynik: results/s1_env_det.json ; kod wyjscia !=0 przy FAIL.
"""
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.liquidsight_env import DT_OBS, POLICY_STEPS, LiquidSightEnv  # noqa: E402
from expert.expert import make_expert_for  # noqa: E402

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "env_f3.json")
CASES = [(43100, "T0"), (43149, "T3"), (43125, "T2b")]  # T2b: nowa sciezka ANEKS-2


def load_cfg():
    with open(CFG_PATH) as f:
        j = json.load(f)
    e = j["env"]
    return {"r_goal": e["r_goal"], "z_hover": e["z_hover"], "t_dwell": e["t_dwell"],
            "v_max": j["ekspert"]["v_max"], "t_ramp_min": j["ekspert"]["t_ramp_min"]}


def run_streams(scene_seed, level, cfg):
    """Jeden przebieg: zwraca (sha_rgb, sha_kin, sha_setpoint, n_tikow, wynik)."""
    env = LiquidSightEnv(r_goal=cfg["r_goal"], z_hover=cfg["z_hover"], t_dwell=cfg["t_dwell"])
    obs, info = env.reset(scene_seed=scene_seed, level=level)
    expert = make_expert_for(env, obs, info, cfg)
    h_rgb, h_kin, h_sp = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
    n = 0
    done = False
    for k in range(POLICY_STEPS):
        sp = expert.setpoint(k * DT_OBS)
        obs, info, done = env.step(sp)
        h_rgb.update(np.ascontiguousarray(obs["rgb"], dtype=np.uint8).tobytes())
        h_kin.update(np.ascontiguousarray(obs["kin"], dtype=np.float32).tobytes())
        h_sp.update(np.ascontiguousarray(sp, dtype=np.float64).tobytes())
        n += 1
        if done:
            break
    res = {"success": bool(info["success"]), "fail_type": info["fail_type"]}
    env.close()
    return h_rgb.hexdigest(), h_kin.hexdigest(), h_sp.hexdigest(), n, res


def main():
    cfg = load_cfg()
    out = {"cases": [], "pass": True}
    for scene_seed, level in CASES:
        r1 = run_streams(scene_seed, level, cfg)
        r2 = run_streams(scene_seed, level, cfg)
        ident = {"rgb": r1[0] == r2[0], "kin": r1[1] == r2[1], "setpoint": r1[2] == r2[2]}
        case_pass = all(ident.values())
        out["pass"] = out["pass"] and case_pass
        entry = {
            "scene_seed": scene_seed, "level": level,
            "n_tikow": r1[3], "wynik": r1[4],
            "run1": {"rgb": r1[0], "kin": r1[1], "setpoint": r1[2]},
            "run2": {"rgb": r2[0], "kin": r2[1], "setpoint": r2[2]},
            "bit_w_bit": ident, "pass": case_pass,
        }
        out["cases"].append(entry)
        tag = "PASS" if case_pass else "FAIL"
        print(f"[{tag}] seed={scene_seed} {level} n={r1[3]} wynik={r1[4]} bit-w-bit={ident}")

    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results"), exist_ok=True)
    outpath = os.path.join(os.path.dirname(__file__), "..", "results", "s1_env_det.json")
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2)
    print("WYNIK:", "PASS" if out["pass"] else "FAIL — STOP", "->", outpath)
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    main()
