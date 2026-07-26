"""expert — nauczyciel privileged fazy 3 (D5): gladki najazd na punkt zawisu.

Ekspert zna GT pozycji celu (z sim) — pikseli NIE widzi (P3: sufit osi ma byc
niezalezny od percepcji). Produkuje setpoint 6D (target_pos, target_vel) na
KAZDYM tiku polityki (12 Hz); env trzyma go ZOH przez 4 tiki kontroli.

Profil: gladka rampa smoothstep od pozycji startowej do [target_xy, z_hover].
Uzywa WYLACZNIE prymitywu wykonawczego _smoothstep z frozen_v1/task.py
(3a^2-2a^3, s'(0)=s'(1)=0 -> zero skokow setpointu ani predkosci: D5).
Czas rampy adaptowany do dystansu (staly limit predkosci szczytowej v_max),
zeby cele bliskie i dalekie mialy jednakowo lagodny najazd.

Strojone w I1 (T6): r_goal, z_hover, t_dwell (env) + v_max, t_ramp_min (rampa).
Po strojeniu -> config/env_f3.json (zamrozone).
"""
from __future__ import annotations

import os
import sys

import numpy as np

# --- prymityw rampy z frozen_v1/ (warstwa wykonawcza, verbatim v1.0) --------
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_FROZEN = os.path.join(_ROOT, "frozen_v1")
for _pth in (_ROOT, _FROZEN):
    if _pth not in sys.path:
        sys.path.insert(0, _pth)
from task import _smoothstep  # noqa: E402  (frozen_v1/task.py)

from env.liquidsight_env import DT_OBS, POLICY_STEPS  # noqa: E402

# --- domyslne parametry rampy eksperta (strojone w T6) ----------------------
EXPERT_DEFAULTS = {
    "v_max": 1.0,        # m/s, limit predkosci szczytowej najazdu
    "t_ramp_min": 2.0,   # s, dolny prog czasu rampy (cele bliskie)
}


class HoverExpert:
    """Gladki najazd na staly punkt zawisu z pelnym feedforwardem predkosci.

    setpoint(t): pos = start + s(t/T)*(hover-start); vel = s'(t/T)/T*(hover-start).
    T = max(t_ramp_min, 1.5*|hover-start|/v_max)  (1.5 = szczyt s'(a) w a=0.5).
    Po T: s=1, s'=0 -> pos=hover, vel=0 (zawis).
    """

    def __init__(self, start_pos, hover, v_max: float, t_ramp_min: float):
        self.start = np.asarray(start_pos, dtype=np.float64)
        self.hover = np.asarray(hover, dtype=np.float64)
        self.delta = self.hover - self.start
        dist = float(np.linalg.norm(self.delta))
        self.T = max(float(t_ramp_min), 1.5 * dist / float(v_max))

    def setpoint(self, t: float) -> np.ndarray:
        s, ds_da = _smoothstep(t / self.T)
        pos = self.start + s * self.delta
        s_dot = ds_da / self.T           # _smoothstep klipuje a -> po T ds_da=0
        vel = s_dot * self.delta
        return np.concatenate([pos, vel])


def make_expert_for(env, obs, info, cfg: dict) -> HoverExpert:
    """Buduje eksperta dla zresetowanego env: start = biezaca poza drona (obs),
    hover = [GT target_xy, z_hover] (privileged)."""
    start_pos = np.asarray(obs["kin"][0:3], dtype=np.float64)
    gt = np.asarray(info["gt_target_pos"], dtype=np.float64)
    hover = np.array([gt[0], gt[1], float(cfg["z_hover"])])
    return HoverExpert(start_pos, hover, cfg["v_max"], cfg["t_ramp_min"])


def run_expert_episode(env, scene_seed: int, level: str, cfg: dict,
                       scene_type: str = "3a") -> dict:
    """Jeden epizod pod kontrola eksperta. Zwraca {success, fail_type, catastrophe}.

    scene_type='3b' -> scena atrybutowa; ekspert celuje w GT wskazanego (info
    gt_target_pos = designated), logika najazdu bez zmian."""
    obs, info = env.reset(scene_seed=scene_seed, level=level, scene_type=scene_type)
    expert = make_expert_for(env, obs, info, cfg)
    done = False
    for k in range(POLICY_STEPS):
        sp = expert.setpoint(k * DT_OBS)
        obs, info, done = env.step(sp)
        if done:
            break
    return {"scene_seed": scene_seed, "level": level,
            "success": bool(info["success"]), "fail_type": info["fail_type"],
            "catastrophe": env.is_catastrophe(info["fail_type"])}
