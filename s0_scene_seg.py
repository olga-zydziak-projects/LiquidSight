"""s0_scene_seg — S0: budowniczy sceny z seeda + maska segmentacji + pule tekstur.

Sprawdza trzy warunki instrumentu fazy 3:
  (1) SEG:   maska segmentacji izoluje cel (>0 px) i jej centroid zgadza sie
             z projekcja GT srodka celu na piksele (tolerancja --tol_px),
  (2) POOL:  budowa sceny z tej samej puli tekstur (seed) jest bit-w-bit
             powtarzalna (hash RGB identyczny), a inna pula daje inny obraz,
  (3) GT:    pozycja celu z symulatora spojna z tym, co widzi kamera.

Pule tekstur: proceduralne PNG z seedowanego PRNG (przenosne, bez assetow).
Prototyp zweryfikowany w sandboxie (pybullet==3.2.7); wersja wiazaca w repo F3.
Uruchomienie: python s0_scene_seg.py [--res 96] [--json out.json]
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

RES_TEX = 128          # rozdzielczosc generowanych tekstur
N_DISTR = 3            # dystraktory


def make_texture(path: str, seed: int) -> None:
    """Proceduralna tekstura: seedowany szum niskiej czestotliwosci."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.2, 0.8, size=(8, 8, 3))
    img = np.kron(base, np.ones((RES_TEX // 8, RES_TEX // 8, 1)))
    img = np.clip(img + rng.normal(0, 0.03, img.shape), 0, 1)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)


def build(pool_seed: int, scene_seed: int, tmpdir: str) -> int:
    """Scena: plane z tekstura z puli + czerwony cel + dystraktory z teksturami."""
    rng = np.random.default_rng(scene_seed)
    tex_rng = np.random.default_rng(pool_seed)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    plane = p.loadURDF("plane.urdf")

    tex_ids = []
    for i in range(N_DISTR + 1):                        # +1 dla plane
        path = os.path.join(tmpdir, f"tex_{pool_seed}_{i}.png")
        make_texture(path, int(tex_rng.integers(0, 2**31)))
        tex_ids.append(p.loadTexture(path))
    p.changeVisualShape(plane, -1, textureUniqueId=tex_ids[0])

    def box(half, pos, rgba, tex=None):
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=half)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=half, rgbaColor=rgba)
        bid = p.createMultiBody(0.0, col, vis, basePosition=pos)
        if tex is not None:
            p.changeVisualShape(bid, -1, textureUniqueId=tex)
        return bid

    target = box([0.08, 0.08, 0.08], [0.5, 0.15, 0.08], [0.85, 0.05, 0.05, 1])
    for i in range(N_DISTR):
        xy = rng.uniform(-0.8, 0.8, size=2)
        box([0.07, 0.07, 0.07], [*xy, 0.07], [1, 1, 1, 1], tex=tex_ids[1 + i])
    return target


def render(res: int):
    eye, look = [1.4, -0.9, 0.9], [0.3, 0.0, 0.1]
    view = p.computeViewMatrix(eye, look, [0, 0, 1])
    proj = p.computeProjectionMatrixFOV(60, 1.0, 0.05, 6.0)
    w, h, rgb, dep, seg = p.getCameraImage(res, res, view, proj,
                                           renderer=p.ER_TINY_RENDERER,
                                           shadow=1, lightDirection=[0.4, 0.4, 1])
    return (np.asarray(rgb, np.uint8), np.asarray(seg, np.int32).reshape(res, res),
            np.asarray(view).reshape(4, 4, order="F"),
            np.asarray(proj).reshape(4, 4, order="F"))


def project(world_xyz, view, proj, res: int):
    clip = proj @ view @ np.array([*world_xyz, 1.0])
    ndc = clip[:3] / clip[3]
    return ((ndc[0] + 1) / 2 * res, (1 - ndc[1]) / 2 * res)


def one_pass(pool_seed: int, scene_seed: int, res: int, tmpdir: str):
    cid = p.connect(p.DIRECT)
    try:
        target = build(pool_seed, scene_seed, tmpdir)
        rgb, seg, view, proj = render(res)
        gt_pos, _ = p.getBasePositionAndOrientation(target)
        mask = seg == target
        n_px = int(mask.sum())
        if n_px:
            ys, xs = np.nonzero(mask)
            centroid = (float(xs.mean()), float(ys.mean()))
        else:
            centroid = (float("nan"), float("nan"))
        proj_px = project(gt_pos, view, proj, res)
        return {"hash_rgb": hashlib.sha256(rgb.tobytes()).hexdigest(),
                "mask_px": n_px, "centroid": centroid,
                "proj_px": (float(proj_px[0]), float(proj_px[1]))}
    finally:
        p.disconnect(cid)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=96)
    ap.add_argument("--scene_seed", type=int, default=40002)
    ap.add_argument("--tol_px", type=float, default=4.0)
    ap.add_argument("--json", type=str, default="s0_scene_seg.json")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        a1 = one_pass(41000, args.scene_seed, args.res, tmp)   # pula A
        a2 = one_pass(41000, args.scene_seed, args.res, tmp)   # pula A ponownie
        b1 = one_pass(42000, args.scene_seed, args.res, tmp)   # pula B

    d = float(np.hypot(a1["centroid"][0] - a1["proj_px"][0],
                       a1["centroid"][1] - a1["proj_px"][1]))
    checks = {
        "seg_niepusta": a1["mask_px"] > 0,
        "seg_centroid_vs_GT_px": d <= args.tol_px,
        "pula_powtarzalna": a1["hash_rgb"] == a2["hash_rgb"],
        "pule_rozne": a1["hash_rgb"] != b1["hash_rgb"],
    }
    ok = all(checks.values())
    print(f"s0_scene_seg [{args.res}x{args.res}]: {'PASS' if ok else 'FAIL'}")
    print(f"  maska celu: {a1['mask_px']} px; |centroid - proj(GT)| = {d:.2f} px "
          f"(tol {args.tol_px})")
    for k, v in checks.items():
        print(f"  {k}: {'OK' if v else 'FAIL'}")
    with open(args.json, "w") as f:
        json.dump({"res": args.res, "checks": checks, "dist_px": d,
                   "poolA": a1, "poolA_repeat": a2, "poolB": b1}, f, indent=2)
    print(f"-> {args.json}")


if __name__ == "__main__":
    main()
