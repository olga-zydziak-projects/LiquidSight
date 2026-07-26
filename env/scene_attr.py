"""scene_attr — spawner sceny atrybutowej fazy 3b (D4).

Port 1:1 palety/kształtów/logiki A0/A1 z s3b0/scene_gen.py (jeden generator, dwaj
konsumenci: s3b0 offline — nietknięty artefakt — oraz env live tutaj). Różnica:
budowa wstrzykiwana do JUŻ zresetowanego klienta CtrlAviary, a obiekt DESYGNOWANY
spawnowany w stożku czołowym +x (ANEKS-1 Z2), by ekspert privileged dolatywał
identycznie jak w 3a. Dystraktory rozmieszczane w stożku czołowym (widoczne w
kadrze), min odstęp 0.35 m, z ograniczeniami atrybutowymi A0/A1.

Determinizm: wszystko z numpy default_rng(scene_seed). Zero źródeł losowości bez
seeda. Ścieżka 3a (env/scene_builder.py) NIE jest tu dotykana.
"""
from __future__ import annotations

import os

import numpy as np
import pybullet as p
from PIL import Image

# --- paleta atrybutowa (RGBA i wymiary 1:1 z s3b0/scene_gen.py) -------------
COLORS = {
    "red":   (0.85, 0.05, 0.05),
    "green": (0.05, 0.60, 0.05),
    "blue":  (0.10, 0.20, 0.85),
}
COLOR_NAMES = list(COLORS)
SHAPES = ["box", "sphere", "cylinder"]
SHAPE_GEOM = {
    "box":      {"half": [0.08, 0.08, 0.08]},
    "sphere":   {"radius": 0.08},
    "cylinder": {"radius": 0.06, "length": 0.16},
}

# --- spawn (ANEKS-1 Z2) — desygnowany w stożku czołowym +x ------------------
SPAWN_AZ_DEG = 25.0          # desygnowany: azymut wzgledem +x
SPAWN_D_MIN = 1.0
SPAWN_D_MAX = 2.0
DISTR_AZ_DEG = 45.0          # dystraktory: szerszy stożek (widoczne w kadrze)
DISTR_D_MIN = 0.8
DISTR_D_MAX = 2.2
MIN_SEP = 0.35               # min odstep obiektow [m] (D4)
FLOOR_RGBA = [0.5, 0.5, 0.5, 1.0]   # neutralna szara (jak Wariant A s3b0)


def scene_params(scene_seed: int) -> tuple[int, str]:
    """Mapowanie deterministyczne seed->(K, poziom A) — DECYZJE_3B D4."""
    K = [3, 5, 8][scene_seed % 3]
    a_level = "A0" if (scene_seed // 3) % 2 == 0 else "A1"
    return K, a_level


def _z_of(shape: str) -> float:
    if shape == "sphere":
        return SHAPE_GEOM["sphere"]["radius"]
    if shape == "cylinder":
        return SHAPE_GEOM["cylinder"]["length"] / 2
    return SHAPE_GEOM["box"]["half"][2]


def plan_attr_scene(scene_seed: int, K: int, a_level: str, start_xy: np.ndarray,
                    arena_half: float = 2.0) -> dict:
    """Plan sceny atrybutowej (czysty, deterministyczny z seeda).

    Desygnowany: para (color,shape) z seeda, pozycja w stożku czołowym +x od startu.
    A0: kolor desygnowanego unikalny; A1: kolor współdzielony z >=1 innym (inny
    kształt). Gwarancja: DOKŁADNIE jeden obiekt pasuje do pary (color,shape).
    """
    assert a_level in ("A0", "A1")
    rng = np.random.default_rng(scene_seed)
    lim = arena_half - 0.3

    color_d = COLOR_NAMES[int(rng.integers(0, 3))]
    shape_d = SHAPES[int(rng.integers(0, 3))]
    designated = (color_d, shape_d)

    # atrybuty dystraktorow (identyczna logika jak scene_gen.plan_scene)
    n_distr = K - 1
    attrs: list[tuple[str, str]] = []
    if a_level == "A0":
        other_colors = [c for c in COLOR_NAMES if c != color_d]
        for _ in range(n_distr):
            c = other_colors[int(rng.integers(0, len(other_colors)))]
            s = SHAPES[int(rng.integers(0, 3))]
            attrs.append((c, s))
    else:  # A1
        other_shapes = [s for s in SHAPES if s != shape_d]
        attrs.append((color_d, other_shapes[int(rng.integers(0, len(other_shapes)))]))
        for _ in range(n_distr - 1):
            while True:
                c = COLOR_NAMES[int(rng.integers(0, 3))]
                s = SHAPES[int(rng.integers(0, 3))]
                if (c, s) != designated:
                    break
            attrs.append((c, s))

    placed: list[np.ndarray] = []

    def ok(xy: np.ndarray) -> bool:
        if abs(xy[0]) > lim or abs(xy[1]) > lim:
            return False
        if np.linalg.norm(xy - start_xy) < 0.5:
            return False
        return all(np.linalg.norm(xy - q) >= MIN_SEP for q in placed)

    # desygnowany: stożek czołowy +x (ANEKS-1 Z2)
    for _ in range(4000):
        az = np.deg2rad(rng.uniform(-SPAWN_AZ_DEG, SPAWN_AZ_DEG))
        d = rng.uniform(SPAWN_D_MIN, SPAWN_D_MAX)
        xy = start_xy + d * np.array([np.cos(az), np.sin(az)])
        if ok(xy):
            placed.append(xy)
            break
    # dystraktory: szerszy stożek czołowy
    for _ in range(n_distr):
        for _ in range(4000):
            az = np.deg2rad(rng.uniform(-DISTR_AZ_DEG, DISTR_AZ_DEG))
            d = rng.uniform(DISTR_D_MIN, DISTR_D_MAX)
            xy = start_xy + d * np.array([np.cos(az), np.sin(az)])
            if ok(xy):
                placed.append(xy)
                break

    des_xy = placed[0]
    des_pos = [float(des_xy[0]), float(des_xy[1]), _z_of(shape_d)]
    distr = []
    for i, (c, s) in enumerate(attrs):
        xy = placed[1 + i]
        distr.append({"color": c, "shape": s,
                      "pos": [float(xy[0]), float(xy[1]), _z_of(s)]})

    return {"scene_seed": int(scene_seed), "K": int(K), "a_level": a_level,
            "command": f"fly to the {color_d} {shape_d}",
            "designated": {"color": color_d, "shape": shape_d, "pos": des_pos},
            "distractors": distr}


def _make_shape(client: int, shape: str, rgba):
    g = SHAPE_GEOM[shape]
    if shape == "box":
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=g["half"], physicsClientId=client)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=g["half"], rgbaColor=rgba,
                                  physicsClientId=client)
    elif shape == "sphere":
        col = p.createCollisionShape(p.GEOM_SPHERE, radius=g["radius"], physicsClientId=client)
        vis = p.createVisualShape(p.GEOM_SPHERE, radius=g["radius"], rgbaColor=rgba,
                                  physicsClientId=client)
    else:
        col = p.createCollisionShape(p.GEOM_CYLINDER, radius=g["radius"], height=g["length"],
                                     physicsClientId=client)
        vis = p.createVisualShape(p.GEOM_CYLINDER, radius=g["radius"], length=g["length"],
                                  rgbaColor=rgba, physicsClientId=client)
    return col, vis


def build_attr_scene(client: int, plane_id: int, scene_seed: int, level,
                     start_xy: np.ndarray, tmpdir: str, arena_half: float = 2.0,
                     min_target_dist: float = 1.0) -> dict:
    """Wstrzykuje scenę atrybutową do zresetowanego klienta CtrlAviary.

    Podpis zgodny z build_task_scene (zamienni konsumenci). K/poziom z mapowania
    D4 (scene_params). Zwraca dict kompatybilny z 3a (target_id/target_pos/hover_xy)
    + pola 3b (designated_id, command, objects, distractor_ids).
    """
    K, a_level = scene_params(int(scene_seed))
    plan = plan_attr_scene(int(scene_seed), K, a_level, np.asarray(start_xy, float),
                           arena_half=arena_half)

    # podłoga neutralna szara (jak Wariant A s3b0; grounder S3b2 widzi to samo tło).
    # Plaska szara TEKSTURA nadpisuje szachownice plane.urdf (sam rgbaColor jej nie
    # usuwa — tinctuje). Determinizm: staly plik, brak losowosci.
    gpath = os.path.join(tmpdir, "floor_gray.png")
    if not os.path.exists(gpath):
        Image.fromarray(np.full((8, 8, 3), 128, np.uint8)).save(gpath)
    tex_gray = p.loadTexture(gpath, physicsClientId=client)
    p.changeVisualShape(plane_id, -1, textureUniqueId=tex_gray, rgbaColor=FLOOR_RGBA,
                        physicsClientId=client)

    order = []
    d = plan["designated"]
    col, vis = _make_shape(client, d["shape"], list(COLORS[d["color"]]) + [1.0])
    des_id = int(p.createMultiBody(0.0, col, vis, basePosition=d["pos"], physicsClientId=client))
    order.append({"id": des_id, "color": d["color"], "shape": d["shape"],
                  "pos": d["pos"], "designated": True})
    distractor_ids = []
    for dd in plan["distractors"]:
        col, vis = _make_shape(client, dd["shape"], list(COLORS[dd["color"]]) + [1.0])
        bid = int(p.createMultiBody(0.0, col, vis, basePosition=dd["pos"], physicsClientId=client))
        order.append({"id": bid, "color": dd["color"], "shape": dd["shape"],
                      "pos": dd["pos"], "designated": False})
        distractor_ids.append(bid)

    target_pos = np.array(d["pos"], dtype=np.float64)
    return {"target_id": des_id, "target_pos": target_pos,
            "hover_xy": target_pos[:2].astype(np.float64),
            "distractor_ids": distractor_ids, "level": a_level, "K": K,
            "designated_id": des_id, "command": plan["command"], "objects": order}


def bbox_from_mask(seg: np.ndarray, body_id: int):
    """bbox [x0,y0,x1,y1] (piksele) lub None gdy obiekt niewidoczny."""
    mask = seg == body_id
    if not mask.any():
        return None
    ys, xs = np.nonzero(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
