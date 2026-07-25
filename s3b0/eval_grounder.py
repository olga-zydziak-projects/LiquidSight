"""eval_grounder — S3b0 T3: wspolny harness metryk groundera.

Biblioteka + CLI. Metryki na EVAL (rozbicia per K, per A0/A1, per dystans):
  designation-precision@1  = top-1 box vs GT bbox WSKAZANEGO, IoU >= 0.5
  wrong-object rate        = top-1 pasuje (IoU>=0.5) do INNEGO obiektu
  no-detection rate        = brak predykcji (None)
  other-miss rate          = predykcja jest, ale nie pasuje do nikogo >=0.5
Kazda klatka trafia do DOKLADNIE jednej kategorii (correct/wrong/no-det/other).
Precision@1 = correct / N (N = klatki z widocznym wskazanym).

Predykcja kandydata: box [x0,y0,x1,y1] w pikselach 256^2, lub None. Tuning progu
WYLACZNIE na dev; liczby raportowane z eval.
"""
from __future__ import annotations

import json
import os

IOU_THR = 0.5
OUT = "../results/s3b0"
GT_PATH = os.path.join(OUT, "gt.jsonl")


def load_gt(variant: str = "A", split: str | None = None) -> list[dict]:
    recs = []
    with open(GT_PATH) as f:
        for line in f:
            r = json.loads(line)
            if r["variant"] != variant:
                continue
            if split is not None and r["split"] != split:
                continue
            recs.append(r)
    return recs


def iou(a, b) -> float:
    if a is None or b is None:
        return 0.0
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0.0


def classify(pred_box, rec: dict) -> str:
    """Kategoria klatki: 'correct' | 'wrong' | 'no_det' | 'other' | 'des_invis'.
    des_invis = wskazany niewidoczny w GT (wykluczony z mianownika precision)."""
    des = [o for o in rec["objects"] if o["designated"]][0]
    if not des["visible"]:
        return "des_invis"
    if pred_box is None:
        return "no_det"
    if iou(pred_box, des["bbox"]) >= IOU_THR:
        return "correct"
    # czy pasuje do innego widocznego obiektu?
    for o in rec["objects"]:
        if o["designated"] or not o["visible"]:
            continue
        if iou(pred_box, o["bbox"]) >= IOU_THR:
            return "wrong"
    return "other"


def _rate(cats: list[str]) -> dict:
    n = sum(1 for c in cats if c != "des_invis")     # mianownik = widoczne wskazane
    if n == 0:
        return {"n": 0, "precision@1": None, "wrong_object": None,
                "no_detection": None, "other_miss": None, "des_invisible": len(cats)}
    correct = cats.count("correct")
    wrong = cats.count("wrong")
    nodet = cats.count("no_det")
    other = cats.count("other")
    return {
        "n": n,
        "precision@1": round(correct / n, 4),
        "wrong_object": round(wrong / n, 4),
        "no_detection": round(nodet / n, 4),
        "other_miss": round(other / n, 4),
        "des_invisible": cats.count("des_invis"),
    }


def aggregate(preds: dict, gt_recs: list[dict]) -> dict:
    """preds: frame_path -> {'box': [...]|None, 'score': float|None}.
    Zwraca metryki overall + rozbicia per K, per A_level, per dist."""
    cats_all, by_K, by_A, by_d = [], {}, {}, {}
    for rec in gt_recs:
        fp = rec["frame_path"]
        pb = preds.get(fp, {}).get("box")
        c = classify(pb, rec)
        cats_all.append(c)
        by_K.setdefault(rec["K"], []).append(c)
        by_A.setdefault(rec["A_level"], []).append(c)
        by_d.setdefault(rec["dist"], []).append(c)
    return {
        "overall": _rate(cats_all),
        "per_K": {str(k): _rate(v) for k, v in sorted(by_K.items())},
        "per_A": {k: _rate(v) for k, v in sorted(by_A.items())},
        "per_dist": {str(k): _rate(v) for k, v in sorted(by_d.items())},
    }


def precision_only(preds: dict, gt_recs: list[dict]) -> dict:
    """Wariant B: sama precision@1 (informacyjnie)."""
    cats = [classify(preds.get(r["frame_path"], {}).get("box"), r) for r in gt_recs]
    r = _rate(cats)
    return {"n": r["n"], "precision@1": r["precision@1"]}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True, help="JSON: frame_path -> {box,score}")
    ap.add_argument("--variant", default="A")
    ap.add_argument("--split", default="eval")
    args = ap.parse_args()
    with open(args.preds) as f:
        preds = json.load(f)
    gt = load_gt(args.variant, args.split)
    print(json.dumps(aggregate(preds, gt), indent=2))


if __name__ == "__main__":
    main()
