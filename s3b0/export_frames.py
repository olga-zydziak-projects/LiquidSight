"""export_frames — S3b0 T2: eksport klatek 256^2 + GT do results/s3b0/.

WARIANT A (eval glowny): K in {3,5,8} x A in {A0,A1} x 8 seedow = 48 scen,
kazda z 4 dystansow {2.0,1.4,0.9,0.5} m = 192 klatki. Podloga neutralna szara.
WARIANT B (informacyjny): 8 scen x 4 dystanse = 32 klatki, podloga teksturowana
rodzina A. Raport osobno.

Seedy: pula 46900-46999 (pule pomiarowe 46000-46649 NIETKNIETE).
  Wariant A: 46900..46947 (6 komorek KxA x 8 seedow, alokacja sekwencyjna).
  Wariant B: 46950..46957.
SPLIT (Wariant A): dev = pierwsze 2 seedy KAZDEJ komorki KxA (12 scen -> 48 klatek),
  eval = pozostale 6 (36 scen -> 144 klatki). Wariant B: caly 'infoB'.

GT per klatka -> results/s3b0/gt.jsonl (1 rekord/klatke).
Uruchomienie: python export_frames.py
"""
from __future__ import annotations

import json
import os
import tempfile

import numpy as np
import pybullet as p

import scene_gen as sg

OUT = "../results/s3b0"                          # wzgledem s3b0/
FRAMES_A = os.path.join(OUT, "frames", "A")
FRAMES_B = os.path.join(OUT, "frames", "B")
GT_PATH = os.path.join(OUT, "gt.jsonl")

K_VALUES = [3, 5, 8]
A_LEVELS = ["A0", "A1"]
SEEDS_PER_CELL = 8
DEV_PER_CELL = 2                                 # pierwsze 2 seedy -> dev
A_SEED_BASE = 46900
B_SEED_BASE = 46950
B_TEX_POOL = list(range(41000, 41050))          # rodzina A (Wariant B)


def _save_png(rgb: np.ndarray, path: str) -> None:
    from PIL import Image
    Image.fromarray(rgb).save(path)


def _cells():
    """Zwraca liste komorek (K, A_level) w stalej kolejnosci."""
    return [(K, a) for K in K_VALUES for a in A_LEVELS]


def export_variant_A(records: list) -> None:
    os.makedirs(FRAMES_A, exist_ok=True)
    seed = A_SEED_BASE
    for (K, a) in _cells():
        for j in range(SEEDS_PER_CELL):
            split = "dev" if j < DEV_PER_CELL else "eval"
            plan = sg.plan_scene(seed, K, a)
            cid = p.connect(p.DIRECT)
            try:
                scene = sg.build_scene(cid, plan, floor_variant="A",
                                       tmpdir=tempfile.gettempdir())
                for dist in sg.CAM_DISTS:
                    pos, quat = sg.drone_pose(dist)
                    rgb, seg = sg.render_frame(cid, pos, quat, 256, want_seg=True)
                    key = f"K{K}_{a}_s{seed}_d{dist:.1f}"
                    rel = f"frames/A/{key}.png"
                    _save_png(rgb, os.path.join(OUT, rel))
                    gt = sg.extract_gt(seg, scene)
                    records.append({
                        "frame_path": rel, "variant": "A", "K": K, "A_level": a,
                        "seed": seed, "dist": dist, "command": plan["command"],
                        "designated_id": scene["designated_id"],
                        "objects": gt, "split": split,
                    })
            finally:
                p.disconnect(cid)
            seed += 1


def export_variant_B(records: list) -> None:
    os.makedirs(FRAMES_B, exist_ok=True)
    # 8 scen: K=5, na przemian A0/A1 (4+4)
    for i in range(8):
        seed = B_SEED_BASE + i
        a = "A0" if i % 2 == 0 else "A1"
        K = 5
        rng = np.random.default_rng(seed)
        tex_seed = int(B_TEX_POOL[rng.integers(0, len(B_TEX_POOL))])
        plan = sg.plan_scene(seed, K, a)
        cid = p.connect(p.DIRECT)
        try:
            scene = sg.build_scene(cid, plan, floor_variant="B",
                                   tmpdir=tempfile.gettempdir(), floor_tex_seed=tex_seed)
            for dist in sg.CAM_DISTS:
                pos, quat = sg.drone_pose(dist)
                rgb, seg = sg.render_frame(cid, pos, quat, 256, want_seg=True)
                key = f"K{K}_{a}_s{seed}_d{dist:.1f}"
                rel = f"frames/B/{key}.png"
                _save_png(rgb, os.path.join(OUT, rel))
                gt = sg.extract_gt(seg, scene)
                records.append({
                    "frame_path": rel, "variant": "B", "K": K, "A_level": a,
                    "seed": seed, "dist": dist, "command": plan["command"],
                    "designated_id": scene["designated_id"],
                    "objects": gt, "split": "infoB", "floor_tex_seed": tex_seed,
                })
        finally:
            p.disconnect(cid)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    records: list = []
    export_variant_A(records)
    export_variant_B(records)

    with open(GT_PATH, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    # --- podsumowanie / sanity ---
    va = [r for r in records if r["variant"] == "A"]
    vb = [r for r in records if r["variant"] == "B"]
    dev = [r for r in va if r["split"] == "dev"]
    ev = [r for r in va if r["split"] == "eval"]
    # sanity: designated visible @ d=2.0
    far = [r for r in va if r["dist"] == 2.0]
    des_vis_far = sum(1 for r in far
                      if [o for o in r["objects"] if o["designated"]][0]["visible"])
    # srednia widocznosc obiektow per dystans (Wariant A)
    vis_by_d = {}
    for d in sg.CAM_DISTS:
        rs = [r for r in va if r["dist"] == d]
        vis = np.mean([sum(o["visible"] for o in r["objects"]) / r["K"] for r in rs])
        vis_by_d[d] = round(float(vis), 3)

    print(f"Wariant A: {len(va)} klatek (dev {len(dev)}, eval {len(ev)})")
    print(f"Wariant B: {len(vb)} klatek (infoB)")
    print(f"gt.jsonl: {len(records)} rekordow -> {GT_PATH}")
    print(f"sanity designated visible @d=2.0: {des_vis_far}/{len(far)}")
    print(f"srednia frakcja widocznych obiektow per dystans (A): {vis_by_d}")
    assert len(va) == 192 and len(dev) == 48 and len(ev) == 144, "licznik Wariantu A"
    assert len(vb) == 32, "licznik Wariantu B"
    assert des_vis_far == len(far), "designated niewidoczny @d=2.0 w ktorejs scenie"
    print("EXPORT OK")


if __name__ == "__main__":
    main()
