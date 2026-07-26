"""grounder_server — serwer YOLO-World LIVE (uruchamiany w .venv_s3b0).

Izolacja (S3b3 pkt 3): grounder działa TU (z torch/ultralytics w .venv_s3b0),
klient w głównym .venv rozmawia po localhost. Konfiguracja YOLO-World FROZEN
z results/s3b0/configs/K1_yoloworld.json (set_classes=["{color} {shape}"], top-1,
próg 0.0) — REPLIKACJA minimalna (bez re-tuningu).

Wejście (per żądanie): klatka 256^2 RGB uint8 + komenda "fly to the {color} {shape}".
Wyjście: top-1 box [x0,y0,x1,y1] (px 256) + conf (live score) + infer_ms.

Uruchomienie: python s3b3/grounder_server.py <port>   (cwd = s3b0/, .venv_s3b0)
"""
import os
import socket
import sys
import time

import numpy as np
from PIL import Image

# ścieżki: repo root (dla s3b3.protocol) + cwd=s3b0 (dla wag .weights/)
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)
from s3b3.protocol import recv_msg, send_msg  # noqa: E402

WEIGHTS = os.path.join(_ROOT, "s3b0", ".weights", "yolov8s-worldv2.pt")


def load_model():
    from ultralytics import YOLOWorld
    os.chdir(os.path.join(_ROOT, "s3b0"))          # CLIP + cache w s3b0/ (gitignored)
    model = YOLOWorld(WEIGHTS)
    model.to("cuda")
    return model


def infer(model, frame: np.ndarray, command: str):
    """Replikacja K1.predict_raw (FROZEN): set_classes(fraza), top-1 po conf, próg 0.0."""
    phrase = command.replace("fly to the ", "").strip()
    model.set_classes([phrase])
    res = model.predict(Image.fromarray(frame), verbose=False, conf=0.001, device=0)[0]
    dets = [([float(x) for x in b.xyxy[0].tolist()], float(b.conf[0])) for b in res.boxes]
    if not dets:
        return None, None
    box, score = max(dets, key=lambda d: d[1])
    return box, score


def main():
    port = int(sys.argv[1])
    model = load_model()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    print(f"READY port={port}", flush=True)
    conn, _ = srv.accept()
    while True:
        try:
            header, blob = recv_msg(conn)
        except (ConnectionError, OSError):
            break
        if header.get("cmd") == "quit":
            break
        h, w = header["h"], header["w"]
        frame = np.frombuffer(blob, np.uint8).reshape(h, w, 3)
        t0 = time.perf_counter()
        box, conf = infer(model, frame, header["command"])
        infer_ms = (time.perf_counter() - t0) * 1000.0
        send_msg(conn, {"box": box, "conf": conf, "infer_ms": round(infer_ms, 3)})
    conn.close()
    srv.close()


if __name__ == "__main__":
    main()
