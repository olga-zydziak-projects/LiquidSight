"""C0 — zadanie: sledzenie okregu. Definicje wspolne dla eksperta, BC i ewaluacji.

Wszystko, co definiuje ZADANIE i KLIF, mieszka tutaj i nigdzie indziej.
Zmiana tego pliku po zamrozeniu C0_GATE.md = zlamanie zasady 1 (CLAUDE.md).
"""
from __future__ import annotations

import contextlib
import io
import warnings

import numpy as np
from gym_pybullet_drones.control.DSLPIDControl import DSLPIDControl
from gym_pybullet_drones.envs.CtrlAviary import CtrlAviary
from gym_pybullet_drones.utils.enums import DroneModel, Physics

warnings.filterwarnings("ignore", message=".*precision lowered.*")

# --- symulacja -------------------------------------------------------------
PYB_FREQ = 240          # Hz, fizyka
CTRL_FREQ = 48          # Hz, krok kontroli (= krok polityki)
CTRL_DT = 1.0 / CTRL_FREQ
EPISODE_S = 10.0
EPISODE_STEPS = int(EPISODE_S * CTRL_FREQ)   # 480

# --- trajektoria referencyjna ---------------------------------------------
CIRCLE_R = 0.5          # m
CIRCLE_Z = 1.0          # m
CIRCLE_T = 6.0          # s, okres
CENTER = np.array([0.0, 0.0, CIRCLE_Z])
RAMP_S = 2.0            # s, plynny najazd (bez skokow setpointu — patrz SMOKE §4)
HOVER_START = np.array([0.0, 0.0, CIRCLE_Z])   # punkt startowy przed najazdem

# --- losowosc demonstracji -------------------------------------------------
START_POS_JITTER = 0.05   # m, +-5 cm na kazda os pozycji poczatkowej
# faza startowa okregu: U(0, 2pi)

# --- KLIF (definicja porazki epizodu) --------------------------------------
FAIL_POS_ERR = 0.5        # m
FAIL_Z_MIN = 0.05         # m
FAIL_TILT_DEG = 60.0      # deg, |roll| lub |pitch|

# --- wymiary ---------------------------------------------------------------
OBS_KIN_DIM = 13   # pos(3) + quat(4) + vel(3) + ang_vel(3)
X_DIM = 20         # obs_kin(13) + ref_rel(3) + ref_vel(3) + dt_norm(1)
ACT_DIM = 4        # RPM x4

DT_NORM = CTRL_DT  # Δt podawane sieci jako wielokrotnosc kroku nominalnego


def _smoothstep(a: np.ndarray | float) -> tuple[float, float]:
    """s(a) = 3a^2 - 2a^3 oraz ds/da. s(0)=0, s(1)=1, s'(0)=s'(1)=0."""
    a = float(np.clip(a, 0.0, 1.0))
    return 3 * a**2 - 2 * a**3, 6 * a - 6 * a**2


def reference(t: float, p0: np.ndarray, phase0: float) -> tuple[np.ndarray, np.ndarray]:
    """Punkt referencyjny i jego pochodna w chwili t.

    Blend miedzy zawisem w p0 a pelnym okregiem:
        ref(t) = p0 + s(t/RAMP) * (circle(t) - p0)
    Dzieki s'(1)=0 predkosc referencji jest CIAGLA w t=RAMP i rowna predkosci
    okregu — brak skoku feedforwardu na sklejeniu. Start jest z zerowa
    predkoscia (s'(0)=0), wiec nie ma tez szarpniecia na t=0.
    """
    th = phase0 + 2 * np.pi * t / CIRCLE_T
    w = 2 * np.pi / CIRCLE_T
    c = CENTER + CIRCLE_R * np.array([np.cos(th), np.sin(th), 0.0])
    c_dot = CIRCLE_R * w * np.array([-np.sin(th), np.cos(th), 0.0])

    s, ds_da = _smoothstep(t / RAMP_S)
    s_dot = ds_da / RAMP_S if t < RAMP_S else 0.0

    ref = p0 + s * (c - p0)
    ref_dot = s_dot * (c - p0) + s * c_dot
    return ref, ref_dot


def episode_init(seed: int) -> tuple[np.ndarray, float]:
    """Deterministyczne warunki poczatkowe epizodu: (pozycja startowa, faza okregu)."""
    rng = np.random.default_rng(seed)
    p0 = HOVER_START + rng.uniform(-START_POS_JITTER, START_POS_JITTER, size=3)
    phase0 = float(rng.uniform(0.0, 2 * np.pi))
    return p0, phase0


def make_env(p0: np.ndarray) -> CtrlAviary:
    # BaseAviary.__init__ drukuje 10 linii [INFO] z .urdf przy kazdym epizodzie —
    # tlumimy, zeby logi setek epizodow byly czytelne. Zero wplywu na dynamike.
    with contextlib.redirect_stdout(io.StringIO()):
        return CtrlAviary(
            drone_model=DroneModel.CF2X, num_drones=1,
            initial_xyzs=p0.reshape(1, 3), physics=Physics.PYB,
            pyb_freq=PYB_FREQ, ctrl_freq=CTRL_FREQ, gui=False,
        )


def make_expert() -> DSLPIDControl:
    return DSLPIDControl(drone_model=DroneModel.CF2X)


def split_state(state: np.ndarray) -> dict:
    """CtrlAviary state (20,) -> nazwane pola."""
    return {
        "pos": state[0:3], "quat": state[3:7], "rpy": state[7:10],
        "vel": state[10:13], "ang_vel": state[13:16], "last_rpm": state[16:20],
    }


def obs_kin(state: np.ndarray) -> np.ndarray:
    """Czesc kinematyczna obserwacji: pos(3) + quat(4) + vel(3) + ang_vel(3) = 13."""
    return np.concatenate([state[0:3], state[3:7], state[10:16]])


def dt_feature(dt: float | np.ndarray):
    """Δt -> cecha wejsciowa. log1p(dt/CTRL_DT - 1): 0 przy nominale, ~3.0 przy luce 20x.

    Skala logarytmiczna, bo luki siegaja kilkudziesieciu krokow nominalnych, a surowe
    "20" wchodzace w MLP z tanh natychmiast nasyca pierwsza warstwe. Ta sama cecha
    trafia do OBU modeli (symetria). CfC dostaje ponadto `ts` w SEKUNDACH (fizycznie).
    """
    return np.log1p(np.maximum(dt / DT_NORM - 1.0, 0.0))


def policy_input(state: np.ndarray, ref: np.ndarray, ref_vel: np.ndarray,
                 dt: float) -> np.ndarray:
    """x = [obs_kin(13), ref_rel(3), ref_vel(3), dt_feat(1)] -> (20,)

    dt = czas od OSTATNIEJ obserwacji (s). Przy p=0 zawsze CTRL_DT -> dt_feat=0.
    Dostaja to OBA modele (symetria); CfC uzywa dt dodatkowo natywnie jako ts.
    """
    s = split_state(state)
    ref_rel = ref - s["pos"]
    return np.concatenate([
        obs_kin(state), ref_rel, ref_vel, [dt_feature(dt)],
    ]).astype(np.float32)


def check_fail(state: np.ndarray, ref: np.ndarray) -> str | None:
    """Zwraca typ FAIL ('err' | 'crash' | 'tilt') albo None, jesli krok OK."""
    s = split_state(state)
    if np.linalg.norm(s["pos"] - ref) > FAIL_POS_ERR:
        return "err"
    if s["pos"][2] < FAIL_Z_MIN:
        return "crash"
    if max(abs(s["rpy"][0]), abs(s["rpy"][1])) > np.deg2rad(FAIL_TILT_DEG):
        return "tilt"
    return None
