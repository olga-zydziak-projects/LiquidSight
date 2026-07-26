"""live_grounder — klient groundera (główny .venv) + kanał celu LIVE + audyt GT.

- GrounderClient: uruchamia serwer-subprocess (.venv_s3b0), rozmawia po localhost.
- LiveTargetTracker: kanał celu wg kontraktu D3, ale źródło = LIVE box + LIVE conf;
  no-detection ticku -> brak źródła (ZOH; nigdy locka -> no-lock).
- audyt: dopasowanie boxu groundera do GT obiektów (IoU>=0.5) -> tożsamość.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)
from s3b3.protocol import recv_msg, send_msg  # noqa: E402

# kontrakt D3 (jak trening S3b2)
DT = 1.0 / 12.0
AGE_MAX = 8.0
K_DEL = 2                       # L_deliver 0.10 s / (1/12 s) = 1.2 -> ceil 2 (czas SYMULOWANY)
TICK_EVERY = 12
IOU_THR = 0.5
PORT = 47655
SRV_LOG = "/tmp/s3b3_grounder_server.log"


def iou(a, b) -> float:
    if a is None or b is None:
        return 0.0
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0, ix1, iy1 = max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0.0


class GrounderClient:
    def __init__(self, port: int = PORT):
        self.port = port
        py = os.path.join(_ROOT, "s3b0", ".venv_s3b0", "bin", "python")
        srv = os.path.join(_ROOT, "s3b3", "grounder_server.py")
        env = os.environ.copy()
        env["HF_HUB_DISABLE_TELEMETRY"] = "1"
        self._log = open(SRV_LOG, "w")
        self.proc = subprocess.Popen([py, srv, str(port)], stdout=self._log,
                                     stderr=subprocess.STDOUT, cwd=os.path.join(_ROOT, "s3b0"),
                                     env=env)
        self.sock = None
        for _ in range(400):                       # do ~80 s na załadowanie modelu
            if self.proc.poll() is not None:
                raise RuntimeError(f"serwer groundera padł (log: {SRV_LOG})")
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(("127.0.0.1", port))
                self.sock = s
                break
            except OSError:
                time.sleep(0.2)
        if self.sock is None:
            raise RuntimeError("nie połączono z serwerem groundera")

    def query(self, frame256: np.ndarray, command: str):
        f = np.ascontiguousarray(frame256, np.uint8)
        send_msg(self.sock, {"command": command, "h": int(f.shape[0]), "w": int(f.shape[1])},
                 f.tobytes())
        hdr, _ = recv_msg(self.sock)
        return hdr["box"], hdr["conf"], hdr["infer_ms"]

    def close(self):
        try:
            send_msg(self.sock, {"cmd": "quit"})
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
        self._log.close()


class LiveTargetTracker:
    """Kanał celu LIVE: (cx,cy,w,h,conf,age) znorm.; źródło = live box+conf; ZOH; no-lock."""

    def __init__(self):
        self.sources = []          # (k_src, box, conf)

    def observe(self, k, box, conf):
        if box is not None:
            self.sources.append((int(k), list(box), float(conf)))

    def vector(self, k):
        deliv = [(ks, bb, cf) for (ks, bb, cf) in self.sources if ks + K_DEL <= k]
        if not deliv:
            return np.array([0, 0, 0, 0, 0, 1.0], np.float32), None
        ks, bb, cf = max(deliv, key=lambda x: x[0])
        cx = ((bb[0] + bb[2]) / 2) / 256.0
        cy = ((bb[1] + bb[3]) / 2) / 256.0
        w = (bb[2] - bb[0]) / 256.0
        h = (bb[3] - bb[1]) / 256.0
        age_n = min(((k - ks) * DT) / AGE_MAX, 1.0)
        return np.array([cx, cy, w, h, cf, age_n], np.float32), ks


def gt_bboxes256(env, objects):
    """Renderuje seg256 z BIEŻĄCEJ pozy env -> {id: bbox|None} dla wszystkich obiektów."""
    from env.scene_attr import bbox_from_mask
    from env.scene_builder import drone_camera
    from task import split_state
    st = env.env._getDroneStateVector(0)
    s = split_state(st)
    _, seg = drone_camera(env.env.CLIENT, s["pos"], s["quat"], 256, want_seg=True)
    return {o["id"]: bbox_from_mask(seg, o["id"]) for o in objects}


def match_object(box, gtb: dict, designated_id: int):
    """Zwraca (kategoria, obj_id). kategoria: designated|other|background|no_detection."""
    if box is None:
        return "no_detection", None
    db = gtb.get(designated_id)
    if db is not None and iou(box, db) >= IOU_THR:
        return "designated", designated_id
    best_oid, best_iou = None, 0.0
    for oid, bb in gtb.items():
        if oid == designated_id or bb is None:
            continue
        v = iou(box, bb)
        if v >= IOU_THR and v > best_iou:
            best_iou, best_oid = v, oid
    if best_oid is not None:
        return "other", best_oid
    return "background", None
