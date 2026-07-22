"""common — wspolne narzedzia pipeline I2 (dane, rollouty, ewaluacja).

Determinizm: env/render/sceny/tekstury z seeda (kontrakt fazy 3). Bit-determinizm
kernelow CUDA NIE jest wymagany (P_SANITY / regula 4).
"""
from __future__ import annotations

import json
import os

import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CFG_PATH = os.path.join(_ROOT, "config", "env_f3.json")

import sys  # noqa: E402
sys.path.insert(0, _ROOT)
from env.liquidsight_env import DT_OBS, POLICY_STEPS, LiquidSightEnv  # noqa: E402
from expert.expert import make_expert_for  # noqa: E402


def load_cfg() -> dict:
    with open(CFG_PATH) as f:
        j = json.load(f)
    e = j["env"]
    return {"r_goal": e["r_goal"], "z_hover": e["z_hover"], "t_dwell": e["t_dwell"],
            "v_max": j["ekspert"]["v_max"], "t_ramp_min": j["ekspert"]["t_ramp_min"]}


def make_env(cfg: dict) -> LiquidSightEnv:
    return LiquidSightEnv(r_goal=cfg["r_goal"], z_hover=cfg["z_hover"], t_dwell=cfg["t_dwell"])


def get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


# --- kolekcja: ekspert (BC) ------------------------------------------------
def collect_expert_episode(env, scene_seed: int, level: str, cfg: dict) -> dict:
    """Ekspert steruje; probka na tik = (obs PRZED krokiem, setpoint eksperta w tym tiku).
    Zwraca tablice (T,...) + success/length."""
    obs, info = env.reset(scene_seed=scene_seed, level=level)
    expert = make_expert_for(env, obs, info, cfg)
    rgb, kin, dt, sp = [], [], [], []
    done = False
    for k in range(POLICY_STEPS):
        a = expert.setpoint(k * DT_OBS)
        rgb.append(np.ascontiguousarray(obs["rgb"], dtype=np.uint8))
        kin.append(np.asarray(obs["kin"], dtype=np.float32))
        dt.append(np.asarray(obs["dt"], dtype=np.float32))
        sp.append(a.astype(np.float32))
        obs, info, done = env.step(a)
        if done:
            break
    return {"rgb": np.stack(rgb), "kin": np.stack(kin), "dt": np.stack(dt),
            "setpoint": np.stack(sp), "length": len(rgb),
            "success": bool(info["success"]), "fail_type": info["fail_type"],
            "scene_seed": scene_seed}


# --- kolekcja: polityka steruje, ekspert etykietuje (DAgger) ---------------
def collect_dagger_episode(env, model, scene_seed: int, level: str, cfg: dict, device) -> dict:
    """Polityka steruje env; etykieta na tiku = setpoint eksperta (privileged) w tym tiku.
    DAgger: uczymy dzialania eksperta w stanach ODWIEDZANYCH przez polityke."""
    obs, info = env.reset(scene_seed=scene_seed, level=level)
    expert = make_expert_for(env, obs, info, cfg)
    h = model.init_hidden(1, device)
    rgb, kin, dt, sp = [], [], [], []
    done = False
    for k in range(POLICY_STEPS):
        lab = expert.setpoint(k * DT_OBS)                # etykieta eksperta w tym stanie/tiku
        rgb.append(np.ascontiguousarray(obs["rgb"], dtype=np.uint8))
        kin.append(np.asarray(obs["kin"], dtype=np.float32))
        dt.append(np.asarray(obs["dt"], dtype=np.float32))
        sp.append(lab.astype(np.float32))
        act, h = model.act(obs, h, device)               # polityka steruje
        obs, info, done = env.step(act)
        if done:
            break
    return {"rgb": np.stack(rgb), "kin": np.stack(kin), "dt": np.stack(dt),
            "setpoint": np.stack(sp), "length": len(rgb),
            "success": bool(info["success"]), "fail_type": info["fail_type"],
            "scene_seed": scene_seed}


# --- ewaluacja polityki ----------------------------------------------------
def eval_policy_episode(env, model, scene_seed: int, level: str, cfg: dict, device) -> dict:
    obs, info = env.reset(scene_seed=scene_seed, level=level)
    h = model.init_hidden(1, device)
    done = False
    for _ in range(POLICY_STEPS):
        act, h = model.act(obs, h, device)
        obs, info, done = env.step(act)
        if done:
            break
    return {"scene_seed": scene_seed, "level": level,
            "success": bool(info["success"]), "fail_type": info["fail_type"],
            "catastrophe": env.is_catastrophe(info["fail_type"])}


# --- dataset BC/DAgger (pelne epizody, padding do POLICY_STEPS) -------------
class EpisodeStore:
    """Trzyma epizody jako tensory CPU; batch = pelne epizody z maska waznosci."""

    def __init__(self):
        self.rgb, self.kin, self.dt, self.sp, self.mask = [], [], [], [], []

    def add_npz(self, path: str):
        d = np.load(path)
        self._add(d["rgb"], d["kin"], d["dt"], d["setpoint"], int(d["length"]))

    def _add(self, rgb, kin, dt, sp, length):
        T = POLICY_STEPS
        r = np.zeros((T, 64, 64, 3), np.uint8); r[:length] = rgb[:length]
        k = np.zeros((T, 13), np.float32); k[:length] = kin[:length]
        dd = np.zeros((T, 1), np.float32); dd[:length] = dt[:length]
        s = np.zeros((T, 6), np.float32); s[:length] = sp[:length]
        m = np.zeros((T,), np.float32); m[:length] = 1.0
        self.rgb.append(torch.from_numpy(r))
        self.kin.append(torch.from_numpy(k))
        self.dt.append(torch.from_numpy(dd))
        self.sp.append(torch.from_numpy(s))
        self.mask.append(torch.from_numpy(m))

    def __len__(self):
        return len(self.rgb)

    def batch(self, idx, device):
        rgb = torch.stack([self.rgb[i] for i in idx]).to(device)
        kin = torch.stack([self.kin[i] for i in idx]).to(device)
        dt = torch.stack([self.dt[i] for i in idx]).to(device)
        sp = torch.stack([self.sp[i] for i in idx]).to(device)
        mask = torch.stack([self.mask[i] for i in idx]).to(device)
        return rgb, kin, dt, sp, mask


def masked_mse(pred, target, mask):
    """pred/target (B,T,6), mask (B,T). Srednia po waznych tikach."""
    err = ((pred - target) ** 2).mean(dim=-1)            # (B,T)
    return (err * mask).sum() / mask.sum().clamp_min(1.0)
