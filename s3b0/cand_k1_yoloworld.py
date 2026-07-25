"""cand_k1_yoloworld — S3b0 T3 K1: YOLO-World (ultralytics) grounder.

Klasy tekstowe = fraza komendy ("{color} {shape}"); top-1 box po conf.
Wagi -> s3b0/.weights/ (gitignored). Uruchomienie: python cand_k1_yoloworld.py
"""
from __future__ import annotations

import os

import run_candidate

os.environ.setdefault("YOLO_VERBOSE", "False")
WEIGHTS = ".weights/yolov8s-worldv2.pt"


class K1:
    name = "K1_yoloworld"
    model_id = "yolov8s-worldv2.pt (ultralytics YOLO-World)"
    prompt_template = 'set_classes=["{color} {shape}"]; top-1 box po conf'

    def load(self):
        from ultralytics import YOLOWorld
        os.makedirs(".weights", exist_ok=True)
        self.model = YOLOWorld(WEIGHTS)          # pobiera przy braku pliku
        self.model.to("cuda")

    def predict_raw(self, img, command):
        phrase = command.replace("fly to the ", "").strip()
        self.model.set_classes([phrase])
        res = self.model.predict(img, verbose=False, conf=0.001, device=0)[0]
        dets = []
        for b in res.boxes:
            xyxy = b.xyxy[0].tolist()
            dets.append((xyxy, float(b.conf[0])))
        return dets


if __name__ == "__main__":
    run_candidate.run(K1())
