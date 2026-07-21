"""s0_render_det — KRYTYCZNY test S0: determinizm renderu TinyRenderer (DIRECT, CPU).

Dwa w pelni niezalezne przebiegi tej samej sceny (swiezy klient kazdy):
fizyka (spadajaca kula) + kamera na luku + getCameraImage(rgb, depth, seg).
PASS <=> SHA256 strumieni rgb/depth/seg bit-w-bit identyczne miedzy przebiegami.

Jesli mismatch z shadow=1, skrypt automatycznie powtarza test z shadow=0
i raportuje, ktora konfiguracja jest deterministyczna (diagnoza, nie ratunek).

Prototyp zweryfikowany w sandboxie (pybullet==3.2.7). Wersja wiazaca: repo F3,
srodowisko uv, ten sam pinowany pybullet. Uruchomienie: python s0_render_det.py
[--res 64] [--frames 30] [--json out.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math

import numpy as np
import pybullet as p
import pybullet_data


def build_scene(seed: int) -> int:
    """Scena z seeda: plane + cel (czerwony box) + 3 dystraktory + dynamiczna kula."""
    rng = np.random.default_rng(seed)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    p.setTimeStep(1.0 / 240.0)
    p.loadURDF("plane.urdf")

    def box(half, pos, rgba, mass=0.0):
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=half)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=half, rgbaColor=rgba)
        return p.createMultiBody(mass, col, vis, basePosition=pos)

    target = box([0.08, 0.08, 0.08], [0.6, 0.2, 0.08], [0.85, 0.05, 0.05, 1])
    for _ in range(3):                                   # dystraktory (szare)
        xy = rng.uniform(-0.9, 0.9, size=2)
        g = float(rng.uniform(0.3, 0.7))
        box([0.07, 0.07, 0.07], [*xy, 0.07], [g, g, g, 1])
    colS = p.createCollisionShape(p.GEOM_SPHERE, radius=0.06)
    visS = p.createVisualShape(p.GEOM_SPHERE, radius=0.06,
                               rgbaColor=[0.1, 0.3, 0.8, 1])
    p.createMultiBody(0.2, colS, visS, basePosition=[-0.3, -0.3, 1.2])  # dynamika
    return target


def camera(t_frac: float, res: int):
    ang = 2 * math.pi * 0.25 * t_frac                    # cwierc luku
    eye = [1.6 * math.cos(ang), 1.6 * math.sin(ang), 1.0]
    view = p.computeViewMatrix(eye, [0, 0, 0.2], [0, 0, 1])
    proj = p.computeProjectionMatrixFOV(fov=60, aspect=1.0,
                                        nearVal=0.05, farVal=6.0)
    return view, proj


def run_once(seed: int, res: int, frames: int, shadow: int) -> dict[str, str]:
    cid = p.connect(p.DIRECT)
    try:
        build_scene(seed)
        h_rgb, h_dep, h_seg = (hashlib.sha256() for _ in range(3))
        for f in range(frames):
            for _ in range(5):
                p.stepSimulation()
            view, proj = camera(f / max(frames - 1, 1), res)
            w, h, rgb, dep, seg = p.getCameraImage(
                res, res, view, proj,
                renderer=p.ER_TINY_RENDERER, shadow=shadow,
                lightDirection=[0.4, 0.4, 1.0])
            h_rgb.update(np.asarray(rgb, dtype=np.uint8).tobytes())
            h_dep.update(np.asarray(dep, dtype=np.float32).tobytes())
            h_seg.update(np.asarray(seg, dtype=np.int32).tobytes())
        return {"rgb": h_rgb.hexdigest(), "depth": h_dep.hexdigest(),
                "seg": h_seg.hexdigest()}
    finally:
        p.disconnect(cid)


def compare(seed: int, res: int, frames: int, shadow: int):
    a = run_once(seed, res, frames, shadow)
    b = run_once(seed, res, frames, shadow)
    per = {k: a[k] == b[k] for k in a}
    return all(per.values()), per, a


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=64)
    ap.add_argument("--frames", type=int, default=30)
    ap.add_argument("--seed", type=int, default=40001)
    ap.add_argument("--json", type=str, default="s0_render_det.json")
    args = ap.parse_args()

    ok1, per1, hashes = compare(args.seed, args.res, args.frames, shadow=1)
    out = {"res": args.res, "frames": args.frames, "seed": args.seed,
           "pybullet": p.getAPIVersion(),
           "shadow1": {"pass": ok1, "per_buffer": per1, "hashes": hashes}}
    if not ok1:                                          # diagnoza: czy winne cienie
        ok0, per0, _ = compare(args.seed, args.res, args.frames, shadow=0)
        out["shadow0"] = {"pass": ok0, "per_buffer": per0}
    verdict = "PASS" if ok1 else "FAIL(shadow=1)"
    print(f"s0_render_det [{args.res}x{args.res}, {args.frames} klatek]: {verdict}")
    for k, v in per1.items():
        print(f"  {k}: {'identyczne' if v else 'ROZJAZD'}")
    if not ok1 and "shadow0" in out:
        print(f"  diagnoza shadow=0: "
              f"{'PASS' if out['shadow0']['pass'] else 'FAIL'}")
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2)
    print(f"-> {args.json}")


if __name__ == "__main__":
    main()
