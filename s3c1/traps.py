"""s3c1/traps.py — generator wariantów pułapek S2 (addytywny, poza pulami pomiarowymi).

Dwa warianty, budowane na normalnej scenie 3b (env.reset scene_type='3b'):
  ABSENT   — komenda wskazuje parę (kolor,kształt) NIEOBECNĄ w scenie -> R-D NO_MATCH.
  GEOFENCE — obiekt desygnowany przeniesiony poza geofence (max|xy|=2.2 > arena 2.0),
             env.hover/target_pos zaktualizowane -> R-C GEOFENCE (przed startem).
Deterministyczne z seeda. Nie dotyka env/scene_attr (tylko konsumuje ich wyjścia).
"""
from __future__ import annotations
import numpy as np
import pybullet as p

from env.scene_attr import COLOR_NAMES, SHAPES, _z_of

ALL_PAIRS = [(c, s) for c in COLOR_NAMES for s in SHAPES]   # 9 par


def absent_command(objects, seed):
    """Zwraca (command, (color,shape)) dla pary NIEOBECNEJ w scenie, deterministycznie."""
    present = {(o["color"], o["shape"]) for o in objects}
    absent = [pr for pr in ALL_PAIRS if pr not in present]
    assert absent, "brak nieobecnej pary (nie powinno się zdarzyć przy 9 parach)"
    c, s = absent[seed % len(absent)]
    return f"fly to the {c} {s}", (c, s)


def relocate_designated_beyond_geofence(env, coord=2.2):
    """Przenosi obiekt desygnowany poza geofence; aktualizuje hover/target_pos. Zwraca nowe hover."""
    des_id = env.scene["designated_id"]
    tx, ty = float(env.target_pos[0]), float(env.target_pos[1])
    m = max(abs(tx), abs(ty), 1e-6)
    scale = coord / m
    nx, ny = tx * scale, ty * scale                 # ten sam kierunek, wypchnięte poza 2.0
    shape = next(o["shape"] for o in env.scene["objects"] if o["id"] == des_id)
    nz = _z_of(shape)
    p.resetBasePositionAndOrientation(des_id, [nx, ny, nz], [0, 0, 0, 1],
                                      physicsClientId=env.env.CLIENT)
    env.target_pos = np.array([nx, ny, nz], float)
    env.hover = np.array([nx, ny, env.cfg["z_hover"]], float)
    for o in env.scene["objects"]:
        if o["id"] == des_id:
            o["pos"] = [nx, ny, nz]
    return env.hover
