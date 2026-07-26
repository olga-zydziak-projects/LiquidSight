"""s3b_env_det — determinizm sciezki atrybutowej 3b (kontrakt fazy 3b).

Env 3b pod ekspertem desygnowanym, 2 NIEZALEZNE przebiegi (swiezy env). SHA256
strumieni: rgb64 (kanal polityki) / rgb256 (kamera semantyczna 1 Hz) / kin /
setpoint. PASS = bit-w-bit identyczne w obu przebiegach dla KAZDEJ sceny.
FAIL -> STOP z diagnoza (nie "naprawiac" przez zmiane flag renderu).

Sceny: literalne z promptu T4 (46600, 46648) ORAZ realizujace intencje etykiet
(K=3/A0, K=8/A1) — bo formula D4 mapuje 46600/46648 na K=5/A1 (rozbieznosc
etykiet z promptem, odnotowana jawnie). Kazda scena raportuje swoje realne (K,A).

Wynik: results/s3b1/s3b_env_det.json ; kod wyjscia !=0 przy FAIL.
"""
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.liquidsight_env import DT_OBS, POLICY_STEPS, LiquidSightEnv  # noqa: E402
from env.scene_attr import scene_params  # noqa: E402
from expert.expert import make_expert_for  # noqa: E402

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "env_f3.json")
# literalne (prompt T4) + intencyjne (etykiety K3/A0, K8/A1)
SEEDS = [46600, 46648, 46602, 46601]


def load_cfg():
    with open(CFG_PATH) as f:
        j = json.load(f)
    e = j["env"]
    return {"r_goal": e["r_goal"], "z_hover": e["z_hover"], "t_dwell": e["t_dwell"],
            "v_max": j["ekspert"]["v_max"], "t_ramp_min": j["ekspert"]["t_ramp_min"]}


def run_streams(scene_seed, cfg):
    env = LiquidSightEnv(r_goal=cfg["r_goal"], z_hover=cfg["z_hover"], t_dwell=cfg["t_dwell"])
    obs, info = env.reset(scene_seed=scene_seed, level="T0", scene_type="3b")
    expert = make_expert_for(env, obs, info, cfg)
    h = {k: hashlib.sha256() for k in ("rgb64", "rgb256", "kin", "setpoint")}
    n_sem = 0
    done = False
    for k in range(POLICY_STEPS):
        sp = expert.setpoint(k * DT_OBS)
        obs, info, done = env.step(sp)
        h["rgb64"].update(np.ascontiguousarray(obs["rgb"], dtype=np.uint8).tobytes())
        h["kin"].update(np.ascontiguousarray(obs["kin"], dtype=np.float32).tobytes())
        h["setpoint"].update(np.ascontiguousarray(sp, dtype=np.float64).tobytes())
        if info.get("rgb256") is not None:
            h["rgb256"].update(np.ascontiguousarray(info["rgb256"], dtype=np.uint8).tobytes())
            n_sem += 1
        if done:
            break
    res = {"success": bool(info["success"]), "fail_type": info["fail_type"], "n_sem": n_sem}
    env.close()
    return {kk: hh.hexdigest() for kk, hh in h.items()}, res


def main():
    cfg = load_cfg()
    out = {"cases": [], "pass": True}
    for seed in SEEDS:
        K, A = scene_params(seed)
        d1, r1 = run_streams(seed, cfg)
        d2, r2 = run_streams(seed, cfg)
        ident = {k: d1[k] == d2[k] for k in d1}
        case_pass = all(ident.values())
        out["pass"] = out["pass"] and case_pass
        out["cases"].append({"scene_seed": seed, "K": K, "A": A, "wynik": r1,
                             "run1": d1, "run2": d2, "bit_w_bit": ident, "pass": case_pass})
        tag = "PASS" if case_pass else "FAIL"
        print(f"[{tag}] seed={seed} K={K} {A} wynik={r1} bit-w-bit={ident}")

    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results", "s3b1"), exist_ok=True)
    outpath = os.path.join(os.path.dirname(__file__), "..", "results", "s3b1", "s3b_env_det.json")
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2)
    print("WYNIK:", "PASS" if out["pass"] else "FAIL — STOP", "->", outpath)
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    main()
