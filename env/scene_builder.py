"""scene_builder — scena zadaniowa liquidsight (D1/D6) + kamera z pozy drona.

ADAPTACJA env/ (nie warstwa wykonawcza — ta jest importowana z frozen_v1/).
Port budowniczego z s0_scene_seg.py: cel (staly czerwony box) + tekstury z pul
(rodzina A / B wg poziomu osi) + dla poziomu T3 dystraktory o kolorze zblizonym
do celu. Kamera: przednia z pozy drona, flagi renderu IDENTYCZNE jak S0
(TinyRenderer, shadow=1, lightDirection=[0.4,0.4,1.0]).

Determinizm (kontrakt fazy 3): kazdy element z seeda, zero zrodel losowosci bez
seeda, render TinyRenderer (CPU). Tekstury = proceduralne PNG z seedowanego PRNG.
"""
from __future__ import annotations

import os

import numpy as np
import pybullet as p
from PIL import Image

RES_TEX = 128
TARGET_HALF = 0.08                       # pol-bok celu [m] (jak s0_scene_seg)
TARGET_RGBA = [0.85, 0.05, 0.05, 1.0]    # staly wyglad CELU przez wszystkie poziomy
LIGHT_DIR = [0.4, 0.4, 1.0]              # jak S0
K_DISTRACTORS_T3 = 4                     # D6: K=4 dystraktorow na T3

# --- ANEKS-1 (2026-07-23): rewizja obserwowalnosci ------------------------
CAM_LOOK_DZ = -0.41                      # Z1: look = eye + R@[1,0,-0.41] (pitch ~-22.3 st.)
SPAWN_AZ_DEG = 25.0                      # Z2: azymut celu wzgledem +x w [-25,+25] st.
SPAWN_D_MIN = 1.0                        # Z2: dystans poziomy od startu [m]
SPAWN_D_MAX = 2.0

# --- osie teksturowe D6 (poziom -> rodzina + pula seedow + K dystraktorow) ---
# ANEKS-2 (2026-07-23): os dystraktorowa parametryczna w K. Miedzy T2 (K=0) a
# T3 (K=4) drabina T2a/T2b/T2c (K=1/2/3). Dystraktory rodziny B, parametryzacja
# jak T3 (kolor +-0.1, rozmiar +-20%, placement z seeda -> zagniezdzone).
_B_POOL = list(range(42000, 42020))
LEVELS = {
    "T0":  {"family": "A", "pool": list(range(41000, 41050)), "K": 0},
    "T1":  {"family": "A", "pool": list(range(41500, 41520)), "K": 0},
    "T2":  {"family": "B", "pool": _B_POOL, "K": 0},
    "T2a": {"family": "B", "pool": _B_POOL, "K": 1},
    "T2b": {"family": "B", "pool": _B_POOL, "K": 2},
    "T2c": {"family": "B", "pool": _B_POOL, "K": 3},
    "T3":  {"family": "B", "pool": _B_POOL, "K": 4},
}
LEVEL_NAMES = ["T0", "T1", "T2", "T3"]                       # bazowe (kompat. wstecz)
LADDER_NAMES = ["T0", "T1", "T2", "T2a", "T2b", "T2c", "T3"]  # pelna drabina (ANEKS-2)


def _norm_level(level) -> str:
    if isinstance(level, int):
        return LEVEL_NAMES[level]
    return level


# --- tekstury proceduralne --------------------------------------------------
def make_texture_A(path: str, seed: int) -> None:
    """Rodzina A: szum niskoczestotliwosciowy 8x8 -> kron do 128, paleta [0.2,0.8]
    (identycznie jak s0_scene_seg.make_texture)."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.2, 0.8, size=(8, 8, 3))
    img = np.kron(base, np.ones((RES_TEX // 8, RES_TEX // 8, 1)))
    img = np.clip(img + rng.normal(0, 0.03, img.shape), 0, 1)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)


def make_texture_B(path: str, seed: int) -> None:
    """Rodzina B: wzory strukturalne — pasy / szachownica o losowej orientacji
    i skali, paleta [0.1,0.9]."""
    rng = np.random.default_rng(seed)
    kind = int(rng.integers(0, 2))               # 0=pasy, 1=szachownica
    scale = int(rng.integers(4, 17))             # rozmiar komorki [px]
    theta = float(rng.uniform(0, np.pi))         # orientacja
    c1 = rng.uniform(0.1, 0.9, 3)
    c2 = rng.uniform(0.1, 0.9, 3)
    yy, xx = np.mgrid[0:RES_TEX, 0:RES_TEX]
    u = xx * np.cos(theta) + yy * np.sin(theta)
    if kind == 0:
        patt = (np.floor(u / scale).astype(int) % 2)
    else:
        v = -xx * np.sin(theta) + yy * np.cos(theta)
        patt = ((np.floor(u / scale).astype(int) + np.floor(v / scale).astype(int)) % 2)
    img = np.where(patt[..., None] == 0, c1, c2)
    img = np.clip(img, 0, 1)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)


def _make_texture(path: str, family: str, seed: int) -> None:
    (make_texture_A if family == "A" else make_texture_B)(path, seed)


# --- budowa sceny -----------------------------------------------------------
def build_task_scene(client: int, plane_id: int, scene_seed: int, level,
                     start_xy: np.ndarray, tmpdir: str,
                     arena_half: float = 2.0, min_target_dist: float = 1.0) -> dict:
    """Wstrzykuje scene zadaniowa do JUZ zresetowanego klienta CtrlAviary.

    Zwraca: {target_id, target_pos(3), hover_xy(2), distractor_ids, level}.
    Determinizm: wszystko z default_rng(scene_seed) i (scene_seed, poziom).
    Cel: czerwony box (staly wyglad). Poziom decyduje o rodzinie tekstur tla
    i (T3) o obecnosci dystraktorow zblizonych kolorem do celu.
    """
    lname = _norm_level(level)
    cfg = LEVELS[lname]
    rng = np.random.default_rng(scene_seed)

    # tekstura tla (plane) z puli rodziny wskazanej przez poziom, wybor z seeda
    pool = cfg["pool"]
    plane_tex_seed = int(pool[rng.integers(0, len(pool))])
    ppath = os.path.join(tmpdir, f"plane_{lname}_{plane_tex_seed}.png")
    _make_texture(ppath, cfg["family"], plane_tex_seed)
    tex_plane = p.loadTexture(ppath, physicsClientId=client)
    p.changeVisualShape(plane_id, -1, textureUniqueId=tex_plane, physicsClientId=client)

    # pozycja celu (ANEKS-1 Z2): stozek czolowy wzgledem +x (dron patrzy na +x,
    # yaw=0), azymut w [-25,+25] st., dystans poziomy [1.0,2.0] m od startu.
    # Region startu (env) gwarantuje, ze cel miesci sie w arenie -> bez retry.
    lim = arena_half - 0.3
    az = float(rng.uniform(-SPAWN_AZ_DEG, SPAWN_AZ_DEG)) * np.pi / 180.0
    d = float(rng.uniform(SPAWN_D_MIN, SPAWN_D_MAX))
    txy = start_xy + d * np.array([np.cos(az), np.sin(az)])
    target_pos = np.array([txy[0], txy[1], TARGET_HALF])
    tid = _box(client, [TARGET_HALF] * 3, target_pos.tolist(), TARGET_RGBA)

    # dystraktory (ANEKS-2): K wg poziomu (T2=0..T3=4) — kolor zblizony do celu
    # (jitter +-0.1), rozmiar celu +-20%, placement z seeda sceny. Drabina
    # zagniezdzona: dla danego scene_seed pierwsze K dystraktorow sa identyczne
    # przez poziomy (tekstura i cel losowane wczesniej, wiec niezalezne od K).
    distractor_ids = []
    n_distractors = int(cfg.get("K", K_DISTRACTORS_T3 if cfg.get("distractors") else 0))
    if n_distractors > 0:
        for _ in range(n_distractors):
            for _ in range(1000):
                dxy = rng.uniform(-lim, lim, size=2)
                if (np.linalg.norm(dxy - txy) >= 0.4 and
                        np.linalg.norm(dxy - start_xy) >= 0.5):
                    break
            jitter = rng.uniform(-0.1, 0.1, 3)
            rgba = np.clip(np.array(TARGET_RGBA[:3]) + jitter, 0, 1).tolist() + [1.0]
            half = TARGET_HALF * float(rng.uniform(0.8, 1.2))   # rozmiar celu +-20%
            did = _box(client, [half] * 3, [dxy[0], dxy[1], half], rgba)
            distractor_ids.append(did)

    return {"target_id": tid, "target_pos": target_pos,
            "hover_xy": txy.astype(np.float64), "distractor_ids": distractor_ids,
            "level": lname, "plane_tex_seed": plane_tex_seed, "K": n_distractors}


def _box(client: int, half, pos, rgba, mass: float = 0.0) -> int:
    col = p.createCollisionShape(p.GEOM_BOX, halfExtents=half, physicsClientId=client)
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=half, rgbaColor=rgba,
                              physicsClientId=client)
    return p.createMultiBody(mass, col, vis, basePosition=pos, physicsClientId=client)


# --- kamera z pozy drona ----------------------------------------------------
def drone_camera(client: int, pos, quat, res: int, want_seg: bool = False):
    """Kamera przednia z pozy drona (D2). Flagi renderu IDENTYCZNE jak S0.

    eye = pos + R@[0.10,0,0.02]; look = eye + R@[1,0,CAM_LOOK_DZ]; up = R@[0,0,1].
    ANEKS-1 Z1: CAM_LOOK_DZ=-0.41 (pitch ~-22.3 st.). Zwraca (rgb uint8, seg|None).
    """
    R = np.array(p.getMatrixFromQuaternion(quat)).reshape(3, 3)
    eye = np.asarray(pos) + R @ np.array([0.10, 0.0, 0.02])
    look = eye + R @ np.array([1.0, 0.0, CAM_LOOK_DZ])   # ANEKS-1 Z1: pitch ~-22.3 st.
    up = R @ np.array([0.0, 0.0, 1.0])
    view = p.computeViewMatrix(eye.tolist(), look.tolist(), up.tolist())
    proj = p.computeProjectionMatrixFOV(60, 1.0, 0.05, 6.0)
    w, h, rgb, dep, seg = p.getCameraImage(
        res, res, view, proj, renderer=p.ER_TINY_RENDERER, shadow=1,
        lightDirection=LIGHT_DIR, physicsClientId=client)
    rgb = np.asarray(rgb, np.uint8).reshape(res, res, 4)[:, :, :3]
    seg_arr = np.asarray(seg, np.int32).reshape(res, res) if want_seg else None
    return np.ascontiguousarray(rgb), seg_arr
