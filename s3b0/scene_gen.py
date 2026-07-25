"""scene_gen — S3b0: generator sceny atrybutowej (standalone, offline).

Prototyp groundera fazy 3b (D4). Buduje scene "podloga + K obiektow z palety
kolor x ksztalt", w ktorej DOKLADNIE jeden obiekt pasuje do komendy
"fly to the {color} {shape}". Dwa poziomy trudnosci atrybutowej:
  A0 = kolor wskazanego UNIKALNY w scenie,
  A1 = kolor wskazanego WSPOLDZIELONY z >=1 innym obiektem (ksztalt rozstrzyga).

Kamera semantyczna 256^2 wg ANEKS-1 (port drone_camera z env/scene_builder.py:
eye=pos+R@[0.10,0,0.02], look=eye+R@[1,0,-0.41] pitch -22.3 st., FOV 60,
near 0.05/far 6.0, TinyRenderer, shadow=1, light [0.4,0.4,1.0]). Kamera
ustawiana na osi podejscia (+x) na dystansie d od srodka sceny.

WZORZEC: s0_scene_seg.py (seed->scena->render->maska->bbox). Nic z env/ nie jest
importowane — pelna replikacja, izolacja srodowiska S3b0.

Determinizm: wszystko z numpy default_rng(scene_seed). Render TinyRenderer (CPU).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile

import numpy as np
import pybullet as p
import pybullet_data
from PIL import Image

# --- paleta atrybutowa (D4) -------------------------------------------------
COLORS = {
    "red":   (0.85, 0.05, 0.05),
    "green": (0.05, 0.60, 0.05),
    "blue":  (0.10, 0.20, 0.85),
}
COLOR_NAMES = list(COLORS)                      # kolejnosc stala
SHAPES = ["box", "sphere", "cylinder"]
SHAPE_GEOM = {                                  # wymiary wg spec
    "box":      {"half": [0.08, 0.08, 0.08]},
    "sphere":   {"radius": 0.08},
    "cylinder": {"radius": 0.06, "length": 0.16},
}

# --- kamera / geometria (ANEKS-1) -------------------------------------------
CAM_LOOK_DZ = -0.41                             # pitch ~-22.3 st.
CAM_EYE_OFF = [0.10, 0.0, 0.02]                 # offset kamery od pozy drona
LIGHT_DIR = [0.4, 0.4, 1.0]
FOV, NEAR, FAR = 60, 0.05, 6.0
Z_HOVER = 0.5                                   # env/liquidsight_env.py
CAM_DISTS = [2.0, 1.4, 0.9, 0.5]                # dystanse wzdluz osi podejscia
SCENE_CENTER = (0.0, 0.0)                       # srodek klastra obiektow
MIN_SEP = 0.35                                  # min odstep obiektow [m]
RES_TEX = 128


# --- tekstura rodziny A (Wariant B) — port make_texture_A -------------------
def make_texture_A(path: str, seed: int) -> None:
    """Rodzina A: szum niskoczestotliwosciowy 8x8 -> kron 128, paleta [0.2,0.8]
    (identycznie jak env/scene_builder.make_texture_A / s0_scene_seg.make_texture)."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.2, 0.8, size=(8, 8, 3))
    img = np.kron(base, np.ones((RES_TEX // 8, RES_TEX // 8, 1)))
    img = np.clip(img + rng.normal(0, 0.03, img.shape), 0, 1)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)


# --- plan sceny (czysty, deterministyczny z seeda; bez pybullet) ------------
def plan_scene(scene_seed: int, K: int, a_level: str) -> dict:
    """Zwraca plan: designated {color,shape,pos}, distractors [{color,shape,pos}],
    command. Wymusza: (1) DOKLADNIE jeden obiekt (color,shape)==designated;
    (2) A0 kolor designated unikalny; A1 kolor designated wspoldzielony z >=1
    innym (o innym ksztalcie). Pozycje: klaster wokol SCENE_CENTER, min odstep
    MIN_SEP, designated blisko srodka (zawsze w kadrze), dystraktory w pierscieniu
    z biasem do przodu (x >= -0.2) by minimalizowac ucieczke z kadru przy d=0.5.
    """
    assert a_level in ("A0", "A1")
    rng = np.random.default_rng(scene_seed)

    color_d = COLOR_NAMES[int(rng.integers(0, 3))]
    shape_d = SHAPES[int(rng.integers(0, 3))]
    designated = (color_d, shape_d)

    # atrybuty dystraktorow
    n_distr = K - 1
    attrs: list[tuple[str, str]] = []
    if a_level == "A0":
        other_colors = [c for c in COLOR_NAMES if c != color_d]
        for _ in range(n_distr):
            c = other_colors[int(rng.integers(0, len(other_colors)))]
            s = SHAPES[int(rng.integers(0, 3))]
            attrs.append((c, s))
    else:  # A1: pierwszy dystraktor wspoldzieli kolor (inny ksztalt), reszta dowolna != designated
        other_shapes = [s for s in SHAPES if s != shape_d]
        attrs.append((color_d, other_shapes[int(rng.integers(0, len(other_shapes)))]))
        for _ in range(n_distr - 1):
            while True:
                c = COLOR_NAMES[int(rng.integers(0, 3))]
                s = SHAPES[int(rng.integers(0, 3))]
                if (c, s) != designated:          # nigdy duplikat pary designated
                    break
            attrs.append((c, s))

    # pozycje: designated blisko srodka, dystraktory w pierscieniu [0.35,0.65]
    cx, cy = SCENE_CENTER
    positions: list[np.ndarray] = []

    def far_enough(xy: np.ndarray) -> bool:
        return all(np.linalg.norm(xy - q) >= MIN_SEP for q in positions)

    # designated
    for _ in range(2000):
        ang = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(0.0, 0.15)
        xy = np.array([cx + r * np.cos(ang), cy + r * np.sin(ang)])
        if far_enough(xy):
            positions.append(xy)
            break
    # dystraktory
    for _ in range(n_distr):
        for _ in range(2000):
            ang = rng.uniform(0, 2 * np.pi)
            r = rng.uniform(0.35, 0.65)
            xy = np.array([cx + r * np.cos(ang), cy + r * np.sin(ang)])
            if xy[0] >= -0.2 and abs(xy[1] - cy) <= 0.5 and far_enough(xy):
                positions.append(xy)
                break
        else:                                      # awaryjnie: rozluznij bias
            for _ in range(2000):
                ang = rng.uniform(0, 2 * np.pi)
                r = rng.uniform(0.35, 0.7)
                xy = np.array([cx + r * np.cos(ang), cy + r * np.sin(ang)])
                if far_enough(xy):
                    positions.append(xy)
                    break

    def z_of(shape: str) -> float:
        if shape == "sphere":
            return SHAPE_GEOM["sphere"]["radius"]
        if shape == "cylinder":
            return SHAPE_GEOM["cylinder"]["length"] / 2
        return SHAPE_GEOM["box"]["half"][2]

    des_pos = [float(positions[0][0]), float(positions[0][1]), z_of(shape_d)]
    distr = []
    for i, (c, s) in enumerate(attrs):
        xy = positions[1 + i]
        distr.append({"color": c, "shape": s,
                      "pos": [float(xy[0]), float(xy[1]), z_of(s)]})

    return {
        "scene_seed": int(scene_seed), "K": int(K), "a_level": a_level,
        "command": f"fly to the {color_d} {shape_d}",
        "designated": {"color": color_d, "shape": shape_d, "pos": des_pos},
        "distractors": distr,
    }


# --- budowa w pybullet ------------------------------------------------------
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
    else:  # cylinder
        col = p.createCollisionShape(p.GEOM_CYLINDER, radius=g["radius"], height=g["length"],
                                     physicsClientId=client)
        vis = p.createVisualShape(p.GEOM_CYLINDER, radius=g["radius"], length=g["length"],
                                  rgbaColor=rgba, physicsClientId=client)
    return col, vis


def build_scene(client: int, plan: dict, floor_variant: str, tmpdir: str,
                floor_tex_seed: int | None = None) -> dict:
    """Wstrzykuje scene z planu do klienta. floor_variant: 'A' (neutralna szara)
    lub 'B' (tekstura rodziny A). Zwraca {designated_id, object_ids, order}.
    Kolejnosc tworzenia: [ground, designated, *distractors] -> body_id = 1..K.
    """
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=client)
    p.setGravity(0, 0, -9.81, physicsClientId=client)

    # podloga jako plaski box (pelna kontrola wygladu; neutralna vs teksturowana)
    gcol = p.createCollisionShape(p.GEOM_BOX, halfExtents=[3, 3, 0.01], physicsClientId=client)
    gvis = p.createVisualShape(p.GEOM_BOX, halfExtents=[3, 3, 0.01],
                               rgbaColor=[0.5, 0.5, 0.5, 1.0], physicsClientId=client)
    ground = p.createMultiBody(0.0, gcol, gvis, basePosition=[0, 0, -0.01],
                               physicsClientId=client)
    if floor_variant == "B":
        tpath = os.path.join(tmpdir, f"floorA_{floor_tex_seed}.png")
        make_texture_A(tpath, int(floor_tex_seed))
        tex = p.loadTexture(tpath, physicsClientId=client)
        p.changeVisualShape(ground, -1, textureUniqueId=tex, physicsClientId=client)

    order = []
    # designated
    d = plan["designated"]
    col, vis = _make_shape(client, d["shape"], list(COLORS[d["color"]]) + [1.0])
    des_id = p.createMultiBody(0.0, col, vis, basePosition=d["pos"], physicsClientId=client)
    order.append({"id": int(des_id), "color": d["color"], "shape": d["shape"],
                  "pos": d["pos"], "designated": True})
    # distractors
    for dd in plan["distractors"]:
        col, vis = _make_shape(client, dd["shape"], list(COLORS[dd["color"]]) + [1.0])
        bid = p.createMultiBody(0.0, col, vis, basePosition=dd["pos"], physicsClientId=client)
        order.append({"id": int(bid), "color": dd["color"], "shape": dd["shape"],
                      "pos": dd["pos"], "designated": False})

    return {"ground_id": int(ground), "designated_id": int(des_id), "objects": order}


# --- kamera z pozy drona (port ANEKS-1) -------------------------------------
def drone_pose(dist: float) -> tuple[list, list]:
    """Poza drona na osi podejscia (+x): pos=(cx-dist, cy, Z_HOVER), yaw=0.
    Zwraca (pos, quat)."""
    cx, cy = SCENE_CENTER
    pos = [cx - dist, cy, Z_HOVER]
    quat = p.getQuaternionFromEuler([0.0, 0.0, 0.0])   # roll=pitch=yaw=0
    return pos, quat


def render_frame(client: int, pos, quat, res: int, want_seg: bool = True):
    """Render z pozy drona (ANEKS-1). Zwraca (rgb[res,res,3] uint8, seg|None)."""
    R = np.array(p.getMatrixFromQuaternion(quat)).reshape(3, 3)
    eye = np.asarray(pos) + R @ np.array(CAM_EYE_OFF)
    look = eye + R @ np.array([1.0, 0.0, CAM_LOOK_DZ])
    up = R @ np.array([0.0, 0.0, 1.0])
    view = p.computeViewMatrix(eye.tolist(), look.tolist(), up.tolist(),
                               physicsClientId=client)
    proj = p.computeProjectionMatrixFOV(FOV, 1.0, NEAR, FAR, physicsClientId=client)
    w, h, rgb, dep, seg = p.getCameraImage(
        res, res, view, proj, renderer=p.ER_TINY_RENDERER, shadow=1,
        lightDirection=LIGHT_DIR, physicsClientId=client)
    rgb = np.asarray(rgb, np.uint8).reshape(res, res, 4)[:, :, :3]
    seg_arr = np.asarray(seg, np.int32).reshape(res, res) if want_seg else None
    return np.ascontiguousarray(rgb), seg_arr


def bbox_from_mask(seg: np.ndarray, body_id: int):
    """bbox [x0,y0,x1,y1] (piksele, x=kolumna, y=wiersz) lub None gdy 0 px."""
    mask = seg == body_id
    n = int(mask.sum())
    if n == 0:
        return None, 0
    ys, xs = np.nonzero(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], n


def extract_gt(seg: np.ndarray, scene: dict) -> list[dict]:
    """Lista obiektow z bbox/visible dla danej klatki."""
    out = []
    for o in scene["objects"]:
        bbox, npx = bbox_from_mask(seg, o["id"])
        out.append({"id": o["id"], "color": o["color"], "shape": o["shape"],
                    "designated": o["designated"], "bbox": bbox,
                    "visible": bbox is not None, "n_px": npx})
    return out


# --- selftest ---------------------------------------------------------------
def _selftest() -> None:
    print("scene_gen selftest")
    ok = True
    for a_level in ("A0", "A1"):
        plan = plan_scene(46900, K=5, a_level=a_level)
        des = (plan["designated"]["color"], plan["designated"]["shape"])
        pairs = [(d["color"], d["shape"]) for d in plan["distractors"]]
        # 1) dokladnie jeden match pary designated
        n_match = 1 + pairs.count(des)
        uniq = (n_match == 1)
        # 2) A0/A1 semantyka koloru
        colors_all = [plan["designated"]["color"]] + [d["color"] for d in plan["distractors"]]
        shared = colors_all.count(des[0]) - 1        # inne obiekty tego koloru
        sem = (shared == 0) if a_level == "A0" else (shared >= 1)
        print(f"  [{a_level}] cmd='{plan['command']}'  distr={pairs}")
        print(f"    dokladnie-jeden-match: {uniq}  kolor-semantyka({a_level}): {sem} "
              f"(inne tego koloru={shared})")
        ok = ok and uniq and sem

    # render + determinizm + widocznosc designated @ d=2.0
    hashes = []
    vis_at_far = None
    for run in range(2):
        cid = p.connect(p.DIRECT)
        try:
            plan = plan_scene(46901, K=8, a_level="A1")
            scene = build_scene(cid, plan, floor_variant="A", tmpdir=tempfile.gettempdir())
            pos, quat = drone_pose(2.0)
            rgb, seg = render_frame(cid, pos, quat, 256, want_seg=True)
            hashes.append(hashlib.sha256(rgb.tobytes()).hexdigest())
            if run == 0:
                gt = extract_gt(seg, scene)
                des_gt = [g for g in gt if g["designated"]][0]
                vis_at_far = des_gt["visible"]
                nvis = sum(g["visible"] for g in gt)
                print(f"  render K=8 A1 @d=2.0: designated visible={des_gt['visible']} "
                      f"bbox={des_gt['bbox']}; widocznych obiektow={nvis}/8")
        finally:
            p.disconnect(cid)
    det = hashes[0] == hashes[1]
    print(f"  determinizm RGB (2x seed 46901): {det}")
    print(f"  designated visible @d=2.0: {vis_at_far}")
    ok = ok and det and bool(vis_at_far)
    print(f"SELFTEST: {'PASS' if ok else 'FAIL'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        # demo: wypisz plan
        print(json.dumps(plan_scene(46900, 5, "A1"), indent=2))


if __name__ == "__main__":
    main()
