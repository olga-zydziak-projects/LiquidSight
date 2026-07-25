"""make_gallery — S3b0 T5: galeria do inspekcji wzrokowej.

16 klatek eval (mix K/A/dystans) z boxem GT wskazanego (zielony) i predykcja
najlepszego kandydata (pomaranczowy) + komenda w naglowku.
-> results/s3b0/gallery/*.png

Najlepszy kandydat = najwyzsza precision@1 na EVAL sposrod nie-DNF (metrics/*.json).
Uruchomienie: python make_gallery.py
"""
from __future__ import annotations

import glob
import json
import os

from PIL import Image, ImageDraw

import eval_grounder as eg

OUT = "../results/s3b0"
GAL = os.path.join(OUT, "gallery")
METRICS = os.path.join(OUT, "metrics")
GREEN = (40, 200, 40)
ORANGE = (255, 150, 20)


def _best_candidate() -> tuple[str | None, dict]:
    best, best_p = None, -1.0
    for mp in glob.glob(os.path.join(METRICS, "*.json")):
        if mp.endswith("_preds.json"):
            continue
        d = json.load(open(mp))
        if d.get("dnf"):
            continue
        p1 = (d.get("eval", {}).get("overall", {}) or {}).get("precision@1") or -1
        if p1 > best_p:
            best_p, best = p1, d["name"]
    if best is None:
        return None, {}
    preds = json.load(open(os.path.join(METRICS, f"{best}_preds.json")))
    return best, preds


def _pick_frames(ev):
    """16 klatek: mix K/A/dystans (deterministyczny co n-ty po posortowaniu)."""
    ev_sorted = sorted(ev, key=lambda r: (r["K"], r["A_level"], r["dist"], r["seed"]))
    step = max(1, len(ev_sorted) // 16)
    return ev_sorted[::step][:16]


def _draw(img, box, color, label=None):
    d = ImageDraw.Draw(img)
    if box:
        d.rectangle([box[0], box[1], box[2], box[3]], outline=color, width=2)
        if label:
            d.text((box[0] + 1, max(0, box[1] - 10)), label, fill=color)


def main() -> None:
    os.makedirs(GAL, exist_ok=True)
    name, preds = _best_candidate()
    ev = eg.load_gt("A", "eval")
    frames = _pick_frames(ev)
    print(f"galeria: najlepszy kandydat = {name}; {len(frames)} klatek")

    for i, r in enumerate(frames):
        base = Image.open(os.path.join(OUT, r["frame_path"])).convert("RGB")
        # naglowek z komenda
        canvas = Image.new("RGB", (base.width, base.height + 22), (20, 20, 20))
        canvas.paste(base, (0, 22))
        ImageDraw.Draw(canvas).text(
            (3, 6), f"{r['command']}  [K{r['K']} {r['A_level']} d{r['dist']}]",
            fill=(230, 230, 230))
        # boxy (offset o naglowek +22 w y)
        des = [o for o in r["objects"] if o["designated"]][0]

        def shift(b):
            return [b[0], b[1] + 22, b[2], b[3] + 22] if b else None
        _draw(canvas, shift(des["bbox"]), GREEN, "GT")
        pb = preds.get(r["frame_path"], {}).get("box") if name else None
        _draw(canvas, shift(pb), ORANGE, name or "")
        canvas.save(os.path.join(GAL, f"gal_{i:02d}_K{r['K']}_{r['A_level']}_d{r['dist']}.png"))

    print(f"-> {GAL}/ ({len(frames)} PNG)")


if __name__ == "__main__":
    main()
