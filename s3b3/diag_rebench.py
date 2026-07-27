"""diag_rebench — DIAG-3B T3: re-benchmark YOLO-World + OWLv2 (FROZEN) na
dystrybucji klatek z pozy drona (500 tików z T2).

Rozdzielnie [wskazany W FOV] vs [POZA FOV], per komórka K×A. Metryki:
  in-FOV : precision@1 (top-1 IoU>=0.5 do wskazanego), wrong-object, no-det.
  poza-FOV: no-det (dobrze — brak fałszywego locka), wrong-object (źle — box na
            dystraktorze rejestruje fałszywy lock). precision@1 nieokreślone.
+ histogramy conf obu grounderów (in-FOV vs poza). Offline (latencja nieistotna).

Uruchomienie: .venv_s3b0/bin/python s3b3/diag_rebench.py   (cwd=s3b0, po B1)
"""
import json
import os
import sys

import numpy as np
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(_ROOT, "results", "diag3b")
IOU_THR = 0.5
YOLO_W = os.path.join(_ROOT, "s3b0", ".weights", "yolov8s-worldv2.pt")
OWLV2_ID = "google/owlv2-base-patch16-ensemble"


def iou(a, b):
    if a is None or b is None:
        return 0.0
    ax0, ay0, ax1, ay1 = a; bx0, by0, bx1, by1 = b
    ix0, iy0, ix1, iy1 = max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0.0


def classify(box, rec):
    """designated | other | background | no_detection (wg GT-IoU z ticks.jsonl)."""
    if box is None:
        return "no_detection"
    did = rec["designated_id"]
    gtb = {o["id"]: o["bbox"] for o in rec["objects"]}
    if gtb.get(did) is not None and iou(box, gtb[did]) >= IOU_THR:
        return "designated"
    for oid, bb in gtb.items():
        if oid == did or bb is None:
            continue
        if iou(box, bb) >= IOU_THR:
            return "other"
    return "background"


class YoloW:
    def load(self):
        from ultralytics import YOLOWorld
        os.chdir(os.path.join(_ROOT, "s3b0"))
        self.m = YOLOWorld(YOLO_W); self.m.to("cuda")

    def predict(self, img, command):
        phrase = command.replace("fly to the ", "").strip()
        self.m.set_classes([phrase])
        res = self.m.predict(img, verbose=False, conf=0.001, device=0)[0]
        dets = [([float(x) for x in b.xyxy[0].tolist()], float(b.conf[0])) for b in res.boxes]
        if not dets:
            return None, None
        box, conf = max(dets, key=lambda d: d[1]); return box, conf


class Owlv2:
    def load(self):
        import torch
        from transformers import Owlv2ForObjectDetection, Owlv2Processor
        self.torch = torch
        self.proc = Owlv2Processor.from_pretrained(OWLV2_ID)
        self.model = Owlv2ForObjectDetection.from_pretrained(OWLV2_ID).to("cuda").eval()

    def predict(self, img, command):
        phrase = command.replace("fly to the ", "").strip()
        with self.torch.no_grad():
            inp = self.proc(text=[[phrase]], images=img, return_tensors="pt").to("cuda")
            out = self.model(**inp)
            ts = self.torch.tensor([(img.height, img.width)]).to("cuda")
            res = self.proc.post_process_grounded_object_detection(out, threshold=0.0,
                                                                   target_sizes=ts)[0]
        if len(res["boxes"]) == 0:
            return None, None
        i = int(self.torch.argmax(res["scores"]))
        return res["boxes"][i].tolist(), float(res["scores"][i])


def bench(grounder, recs):
    import collections
    # akumulatory: per (in_fov) i per (in_fov, cell)
    cat_fov = {True: collections.Counter(), False: collections.Counter()}
    cat_cell = collections.defaultdict(collections.Counter)
    conf = {True: [], False: []}
    for r in recs:
        img = Image.open(os.path.join(OUT, "frames", r["frame"])).convert("RGB")
        box, cf = grounder.predict(img, r["command"])
        cat = classify(box, r)
        fov = bool(r["in_fov"])
        cat_fov[fov][cat] += 1
        cat_cell[(fov, f"K{r['K']}_{r['A']}")][cat] += 1
        if cf is not None:
            conf[fov].append(cf)

    def rates(c):
        n = sum(c.values())
        return {"n": n, "designated": round(100 * c["designated"] / n, 1),
                "other": round(100 * c["other"] / n, 1),
                "background": round(100 * c["background"] / n, 1),
                "no_detection": round(100 * c["no_detection"] / n, 1)} if n else {}
    bins = [0, .05, .1, .2, .3, .5, .7, 1.01]
    return {
        "in_fov": rates(cat_fov[True]), "out_fov": rates(cat_fov[False]),
        "per_cell_in_fov": {c: rates(cat_cell[(True, c)]) for c in
                            sorted({k[1] for k in cat_cell if k[0]})},
        "conf_median_in_fov": round(float(np.median(conf[True])), 4) if conf[True] else None,
        "conf_median_out_fov": round(float(np.median(conf[False])), 4) if conf[False] else None,
        "conf_hist_bins": bins,
        "conf_hist_in_fov": np.histogram(conf[True], bins=bins)[0].tolist(),
        "conf_hist_out_fov": np.histogram(conf[False], bins=bins)[0].tolist(),
    }


def main():
    recs = [json.loads(l) for l in open(os.path.join(OUT, "ticks.jsonl"))]
    print(f"rebench na {len(recs)} klatkach (in-FOV {sum(r['in_fov'] for r in recs)})")
    out = {}
    y = YoloW(); y.load()
    out["YOLO_World"] = bench(y, recs)
    print(f"  YOLO in-FOV: {out['YOLO_World']['in_fov']}")
    print(f"  YOLO out-FOV: {out['YOLO_World']['out_fov']}")
    o = Owlv2(); o.load()
    out["OWLv2"] = bench(o, recs)
    print(f"  OWLv2 in-FOV: {out['OWLv2']['in_fov']}")
    print(f"  OWLv2 out-FOV: {out['OWLv2']['out_fov']}")
    json.dump(out, open(os.path.join(OUT, "rebench.json"), "w"), indent=2)
    print(f"-> {OUT}/rebench.json")


if __name__ == "__main__":
    main()
