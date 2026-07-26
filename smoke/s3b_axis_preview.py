"""s3b_axis_preview — siatka podgladow osi atrybutowej K x A (T4).

Po 2 sceny na komorke (K in {3,5,8} x A in {A0,A1}); klatka 256^2 z pozy STARTU
drona (wskazany widoczny w stozku czolowym) z bboxem GT wskazanego (zielony) +
komenda w naglowku. -> results/s3b1/preview/*.png

Seedy: pierwsze 2 realizujace kazda komorke z puli sweep 46600+.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.liquidsight_env import SEM_RES, LiquidSightEnv  # noqa: E402
from env.scene_attr import bbox_from_mask, scene_params  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from task import split_state  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results", "s3b1", "preview")
GREEN = (40, 200, 40)


def pick_seeds():
    """2 seedy na komorke K x A z puli 46600-46699 (mapowanie D4)."""
    cells = {(K, A): [] for K in (3, 5, 8) for A in ("A0", "A1")}
    for s in range(46600, 46700):
        K, A = scene_params(s)
        if len(cells[(K, A)]) < 2:
            cells[(K, A)].append(s)
    return cells


def render_start_256(env, seed):
    """Reset 3b + render 256^2 z pozy startu + bbox GT wskazanego."""
    obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
    state = env.env._getDroneStateVector(0)
    s = split_state(state)
    rgb, seg = drone_camera(env.env.CLIENT, s["pos"], s["quat"], SEM_RES, want_seg=True)
    bbox = bbox_from_mask(seg, info["designated_id"])
    return rgb, bbox, info["command"], info


def main():
    os.makedirs(OUT, exist_ok=True)
    env = LiquidSightEnv()
    cells = pick_seeds()
    n = 0
    for (K, A) in sorted(cells):
        for seed in cells[(K, A)]:
            rgb, bbox, cmd, info = render_start_256(env, seed)
            canvas = Image.new("RGB", (SEM_RES, SEM_RES + 22), (20, 20, 20))
            canvas.paste(Image.fromarray(rgb), (0, 22))
            d = ImageDraw.Draw(canvas)
            d.text((3, 6), f"{cmd}  [K{K} {A} s{seed}]", fill=(230, 230, 230))
            if bbox:
                d.rectangle([bbox[0], bbox[1] + 22, bbox[2], bbox[3] + 22],
                            outline=GREEN, width=2)
                d.text((bbox[0] + 1, max(22, bbox[1] + 22 - 10)), "GT", fill=GREEN)
            vis = "vis" if bbox else "OCCL"
            canvas.save(os.path.join(OUT, f"prev_K{K}_{A}_s{seed}_{vis}.png"))
            n += 1
    env.close()
    print(f"preview: {n} klatek -> {OUT}/")


if __name__ == "__main__":
    main()
