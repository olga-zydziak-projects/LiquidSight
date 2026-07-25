"""run_candidate — S3b0 T3: wspolny driver kandydata groundera.

Procedura per kandydat (spec S3b0):
  1. laduj model (DNF z powodem gdy sie nie uda -> jedz dalej),
  2. tuning progu WYLACZNIE na DEV (max precision@1, tie-break min wrong-object),
  3. ZAMROZENIE configu -> results/s3b0/configs/{K}.json,
  4. ewaluacja na EVAL -> metryki (rozbicia per K/A/dist),
  5. latencja mean+p95 (batch=1, warmup 10, 100 klatek) + peak VRAM — TYLKO gdy GPU wolne,
  6. Wariant B: sama precision@1.
Wynik -> results/s3b0/metrics/{K}.json (+ {K}_preds.json dla galerii).

Kandydat implementuje interfejs Candidate:
  .name, .model_id, .prompt_template, .load(), .predict_raw(pil_img, command)
  gdzie predict_raw zwraca liste (box[x0,y0,x1,y1] w px 256, score float),
  posortowana lub nie. Pusta lista = brak detekcji.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import traceback

from PIL import Image

import eval_grounder as eg

OUT = "../results/s3b0"
CONFIGS = os.path.join(OUT, "configs")
METRICS = os.path.join(OUT, "metrics")
THR_GRID = [0.0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4]
LAT_WARMUP = 10
LAT_FRAMES = 100


def _abs(frame_path: str) -> str:
    return os.path.join(OUT, frame_path)


def _gpu_free_mib() -> tuple[bool, int]:
    """(wolne?, memory.used MiB). 'wolne' gdy <1000 MiB zajete przed zaladowaniem."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True).strip().splitlines()[0]
        used = int(out)
        return used < 1000, used
    except Exception:
        return False, -1


def _topk_with_thr(dets, thr):
    """Top-1 box o score >= thr (najwyzszy score). None gdy brak."""
    cand = [d for d in dets if d[1] >= thr]
    if not cand:
        return None
    best = max(cand, key=lambda d: d[1])
    return [int(round(x)) for x in best[0]]


def _dev_tune(raw_by_frame, dev_recs) -> tuple[float, dict]:
    """Wybor progu na DEV: max precision@1, tie-break min wrong-object, potem min no-det."""
    best = None
    trace = []
    for thr in THR_GRID:
        preds = {fp: {"box": _topk_with_thr(raw_by_frame[fp], thr)} for fp in raw_by_frame}
        m = eg.aggregate(preds, dev_recs)["overall"]
        key = (m["precision@1"] or 0, -(m["wrong_object"] or 0), -(m["no_detection"] or 0))
        trace.append({"thr": thr, "precision@1": m["precision@1"],
                      "wrong_object": m["wrong_object"], "no_detection": m["no_detection"]})
        if best is None or key > best[0]:
            best = (key, thr)
    return best[1], trace


def run(candidate) -> None:
    os.makedirs(CONFIGS, exist_ok=True)
    os.makedirs(METRICS, exist_ok=True)
    name = candidate.name
    mpath = os.path.join(METRICS, f"{name}.json")
    print(f"\n=== KANDYDAT {name} ({candidate.model_id}) ===")

    free_before, used_before = _gpu_free_mib()
    print(f"GPU przed zaladowaniem: {used_before} MiB used, wolne={free_before}")

    # --- 1. laduj model (DNF gdy sie nie uda) ---
    try:
        t0 = time.perf_counter()
        candidate.load()
        load_s = time.perf_counter() - t0
        print(f"model zaladowany w {load_s:.1f} s")
    except Exception as e:
        reason = f"{type(e).__name__}: {e}"
        print(f"DNF (load): {reason}")
        with open(mpath, "w") as f:
            json.dump({"name": name, "model_id": candidate.model_id, "dnf": True,
                       "stage": "load", "reason": reason,
                       "traceback": traceback.format_exc()[-1500:]}, f, indent=2)
        return

    dev = eg.load_gt("A", "dev")
    ev = eg.load_gt("A", "eval")
    vb = eg.load_gt("B", "infoB")

    try:
        # smoke: 1 predykcja
        r0 = dev[0]
        _ = candidate.predict_raw(Image.open(_abs(r0["frame_path"])).convert("RGB"),
                                  r0["command"])

        # --- 2. raw DEV -> tuning progu ---
        raw_dev = {}
        for r in dev:
            img = Image.open(_abs(r["frame_path"])).convert("RGB")
            raw_dev[r["frame_path"]] = candidate.predict_raw(img, r["command"])
        thr, thr_trace = _dev_tune(raw_dev, dev)
        print(f"zamrozony prog (dev): {thr}")

        # --- 3. freeze config ---
        cfg = {"name": name, "model_id": candidate.model_id,
               "prompt_template": candidate.prompt_template, "score_threshold": thr,
               "iou_thr_metric": eg.IOU_THR, "thr_grid": THR_GRID,
               "dev_trace": thr_trace, "frozen": True}
        with open(os.path.join(CONFIGS, f"{name}.json"), "w") as f:
            json.dump(cfg, f, indent=2)

        # --- 4. EVAL ---
        raw_eval, preds_eval = {}, {}
        for r in ev:
            img = Image.open(_abs(r["frame_path"])).convert("RGB")
            dets = candidate.predict_raw(img, r["command"])
            raw_eval[r["frame_path"]] = dets
            preds_eval[r["frame_path"]] = {"box": _topk_with_thr(dets, thr),
                                           "score": (max((d[1] for d in dets), default=None))}
        metrics_eval = eg.aggregate(preds_eval, ev)

        # --- 5. latencja + VRAM (tylko gdy GPU wolne) ---
        lat = {"measured": False, "reason": None}
        if free_before:
            import torch
            frames = [Image.open(_abs(r["frame_path"])).convert("RGB")
                      for r in ev[:LAT_FRAMES]]
            cmds = [r["command"] for r in ev[:LAT_FRAMES]]
            for i in range(LAT_WARMUP):
                candidate.predict_raw(frames[i % len(frames)], cmds[i % len(cmds)])
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
            times = []
            for img, cmd in zip(frames, cmds):
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                t = time.perf_counter()
                candidate.predict_raw(img, cmd)
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                times.append((time.perf_counter() - t) * 1000.0)
            times.sort()
            peak_vram = (torch.cuda.max_memory_allocated() / 2**20
                         if torch.cuda.is_available() else None)
            lat = {"measured": True, "n": len(times),
                   "mean_ms": round(sum(times) / len(times), 2),
                   "p95_ms": round(times[int(0.95 * (len(times) - 1))], 2),
                   "min_ms": round(times[0], 2), "max_ms": round(times[-1], 2),
                   "peak_vram_mib": round(peak_vram, 1) if peak_vram else None}
        else:
            lat["reason"] = f"GPU zajete ({used_before} MiB) — latencja odlozona (spec pkt 5)"
            print(f"  {lat['reason']}")

        # --- 6. Wariant B (precision@1 only) ---
        preds_b = {}
        for r in vb:
            img = Image.open(_abs(r["frame_path"])).convert("RGB")
            dets = candidate.predict_raw(img, r["command"])
            preds_b[r["frame_path"]] = {"box": _topk_with_thr(dets, thr)}
        metrics_b = eg.precision_only(preds_b, vb)

        result = {"name": name, "model_id": candidate.model_id, "dnf": False,
                  "score_threshold": thr, "eval": metrics_eval,
                  "latency": lat, "variantB": metrics_b, "load_s": round(load_s, 1)}
        with open(mpath, "w") as f:
            json.dump(result, f, indent=2)
        # zapis predykcji EVAL do galerii
        with open(os.path.join(METRICS, f"{name}_preds.json"), "w") as f:
            json.dump({fp: pv for fp, pv in preds_eval.items()}, f)

        o = metrics_eval["overall"]
        print(f"EVAL {name}: precision@1={o['precision@1']} wrong={o['wrong_object']} "
              f"no_det={o['no_detection']} | latencja={lat.get('p95_ms')} p95 ms "
              f"VRAM={lat.get('peak_vram_mib')} MiB | B prec@1={metrics_b['precision@1']}")

    except Exception as e:
        reason = f"{type(e).__name__}: {e}"
        print(f"DNF (eval): {reason}")
        with open(mpath, "w") as f:
            json.dump({"name": name, "model_id": candidate.model_id, "dnf": True,
                       "stage": "eval", "reason": reason,
                       "traceback": traceback.format_exc()[-1500:]}, f, indent=2)
