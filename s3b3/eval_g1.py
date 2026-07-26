"""eval_g1 — pomiar G1: polityka FROZEN (S3b2) + grounder LIVE (YOLO-World @1 Hz).

Subkomendy:
  unittest  — 5 klatek z results/s3b0/frames/: box serwera == wyniki S3b0 (sanity).
  smoke     — 10 ep EVAL 46500-46509: plumbing (kanały żywe, age, conf, wall-latencja).
  measure   — 50 ep sweep 46600-46649 wg G1_GATE: metryki + audyt + werdykt.
  traces    — 3 epizody (sukces / wrong-lock / min-conf): trace json + klatki z boxem.

Kontrakt D3 (jak trening): dostarczenie w czasie SYMULOWANYM (k_del=k_src+2);
conf = LIVE; no-detection -> brak dostarczenia. Wall-latencja logowana osobno.
"""
from __future__ import annotations

import collections
import json
import os
import statistics
import sys

import numpy as np
import torch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import DT_OBS, POLICY_STEPS  # noqa: E402
from env.scene_attr import scene_params  # noqa: E402
from models.policy_gc import PolicyGC  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from s3b3.live_grounder import (TICK_EVERY, GrounderClient, LiveTargetTracker,  # noqa: E402
                                gt_bboxes256, match_object)

OUT = os.path.join(_ROOT, "results", "s3b3")
CKPT = os.path.join(_ROOT, "ckpt", "s3b2", "policy_gc.pt")
DT = DT_OBS


def load_policy(device):
    m = PolicyGC().to(device)
    m.load_state_dict(torch.load(CKPT, map_location=device))
    m.eval()
    return m


def run_episode_live(env, policy, client, seed, cfg, device, trace=False):
    obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
    command, did, objects = info["command"], info["designated_id"], info["objects"]
    h = policy.init_hidden(1, device)
    tracker = LiveTargetTracker()
    ticks, wall, tr = [], [], ([] if trace else None)
    done = False
    for k in range(POLICY_STEPS):
        tgt, cur_src = tracker.vector(k)
        action, h = policy.act(obs, tgt, h, device)
        obs, info, done = env.step(action)
        if k % TICK_EVERY == 0:
            frame = info.get("rgb256")
            if frame is not None:
                box, conf, ims = client.query(frame, command)
                wall.append(ims)
                cat, oid = match_object(box, gt_bboxes256(env, objects), did)
                ticks.append({"k": k, "t": round(k * DT, 4), "box": box, "conf": conf,
                              "matched": cat, "obj_id": oid, "infer_ms": ims})
                tracker.observe(k, box, conf)
        if trace:
            tr.append({"k": k, "target": [round(float(x), 4) for x in tgt],
                       "cur_src": cur_src})
        if done:
            break
    delivered = [t["obj_id"] for t in ticks if t["box"] is not None]
    flips = sum(1 for a, b in zip(delivered, delivered[1:]) if a != b)
    confs = [t["conf"] for t in ticks if t["conf"] is not None]
    K, A = scene_params(seed)
    res = {"seed": seed, "K": K, "A": A, "success": bool(info["success"]),
           "fail_type": info["fail_type"], "catastrophe": env.is_catastrophe(info["fail_type"]),
           "flips": flips, "n_ticks": len(ticks),
           "n_detections": sum(1 for t in ticks if t["box"] is not None),
           "min_conf": (min(confs) if confs else None), "ticks": ticks, "wall_ms": wall}
    if trace:
        res["trace"] = tr
    return res


# ---------------- unittest ----------------
def cmd_unittest():
    gt = {}
    with open(os.path.join(_ROOT, "results/s3b0/gt.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            gt[r["frame_path"]] = r["command"]
    preds = json.load(open(os.path.join(_ROOT, "results/s3b0/metrics/K1_yoloworld_preds.json")))
    from PIL import Image
    frames = [fp for fp in preds if preds[fp].get("box")][:5]
    client = GrounderClient()
    ok = True
    print("unittest: box serwera vs S3b0 K1 preds (te same klatki+config)")
    try:
        from s3b3.live_grounder import iou
        for fp in frames:
            arr = np.asarray(Image.open(os.path.join(_ROOT, "results/s3b0", fp)).convert("RGB"))
            box, conf, ims = client.query(arr, gt[fp])
            ref = preds[fp]["box"]
            v = iou(box, ref) if box else 0.0
            match = v >= 0.90          # YOLO na GPU nie jest bit-det.; box zgodny co do obiektu+lokalizacji
            ok = ok and match
            print(f"  {fp}: IoU(serwer,S3b0)={v:.3f} conf={conf:.3f} ({ims:.0f}ms) "
                  f"{'OK' if match else 'MISMATCH'}")
    finally:
        client.close()
    print(f"UNITTEST: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


# ---------------- smoke ----------------
def cmd_smoke():
    os.makedirs(OUT, exist_ok=True)
    device = get_device(); cfg = load_cfg(); env = make_env(cfg); policy = load_policy(device)
    client = GrounderClient()
    anomalies, wall_all, eps = [], [], []
    try:
        for seed in range(46500, 46510):
            r = run_episode_live(env, policy, client, seed, cfg, device)
            wall_all += r["wall_ms"]
            # sanity: konf w (0,1], kanał żył (jakieś detekcje), brak wyjątków
            for t in r["ticks"]:
                if t["conf"] is not None and not (0.0 < t["conf"] <= 1.0):
                    anomalies.append(["conf_out_of_range", seed, t["conf"]])
            if r["n_detections"] == 0:
                anomalies.append(["no_detections_whole_episode", seed])
            eps.append({"seed": seed, "success": r["success"], "n_det": r["n_detections"],
                        "n_ticks": r["n_ticks"], "min_conf": r["min_conf"]})
    finally:
        client.close()
    env.close()
    ws = sorted(wall_all)
    out = {"episodes": eps, "n_calls": len(wall_all),
           "wall_median_ms": round(statistics.median(wall_all), 1),
           "wall_p95_ms": round(ws[int(0.95 * (len(ws) - 1))], 1),
           "wall_ref_f1_ms": 63.1, "anomalies": anomalies}
    json.dump(out, open(os.path.join(OUT, "smoke.json"), "w"), indent=2)
    print(f"smoke: {len(eps)} ep, {len(wall_all)} wywołań groundera | "
          f"wall median {out['wall_median_ms']}ms p95 {out['wall_p95_ms']}ms (ref 63ms) | "
          f"anomalie: {len(anomalies)}")
    if anomalies:
        print(f"  ANOMALIE -> STOP: {anomalies[:5]}"); sys.exit(1)
    print("SMOKE OK")


# ---------------- measure ----------------
def cmd_measure():
    os.makedirs(OUT, exist_ok=True)
    device = get_device(); cfg = load_cfg(); env = make_env(cfg); policy = load_policy(device)
    ceiling = json.load(open(os.path.join(_ROOT, "results/s3b2/ceiling.json")))
    client = GrounderClient()
    episodes = []
    audit_f = open(os.path.join(OUT, "tick_audit.jsonl"), "w")
    try:
        for seed in range(46600, 46650):
            r = run_episode_live(env, policy, client, seed, cfg, device)
            for t in r["ticks"]:
                audit_f.write(json.dumps({"seed": seed, **t}) + "\n")
            episodes.append(r)
    finally:
        client.close(); audit_f.close()
    env.close()

    n = len(episodes)
    succ = sum(e["success"] for e in episodes)
    wl = sum(e["fail_type"] == "wrong_lock" for e in episodes)
    na = sum(e["fail_type"] == "no_arrival" for e in episodes)
    dw = sum(e["fail_type"] == "dwell" for e in episodes)
    cat = sum(e["catastrophe"] for e in episodes)
    succ_pct = round(100 * succ / n, 1); wl_pct = round(100 * wl / n, 1)
    # per-cell (sparowane z sufitem)
    cell = collections.defaultdict(lambda: [0, 0, 0])
    for e in episodes:
        c = cell[(e["K"], e["A"])]; c[0] += 1; c[1] += int(e["success"]); c[2] += int(e["fail_type"] == "wrong_lock")
    per_cell = {f"K{K}_{A}": {"n": v[0], "sukces_pct": round(100 * v[1] / v[0], 1),
                "wrong_lock": v[2], "sufit_pct": ceiling["per_cell"].get(f"K{K}_{A}", {}).get("sukces_pct")}
                for (K, A), v in sorted(cell.items())}
    # tick-precision (audyt)
    tp = collections.Counter(t["matched"] for e in episodes for t in e["ticks"])
    ntk = sum(tp.values())
    tick_prec = {k: round(100 * tp[k] / ntk, 1) for k in ("designated", "other", "background", "no_detection")}
    # flip-rate
    flips = [e["flips"] for e in episodes]
    # conf histogram
    allconf = [t["conf"] for e in episodes for t in e["ticks"] if t["conf"] is not None]
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    hist, _ = np.histogram(allconf, bins=bins)
    # wall latency
    wall = [ms for e in episodes for ms in e["wall_ms"]]; ws = sorted(wall)
    verdict = "PASS" if (succ_pct >= 85.0 and wl_pct <= 8.0) else "FAIL"
    offline = 86.8
    refresh_hyp = ("KOMPENSUJE (live > offline)" if succ_pct > offline
                   else "NIE kompensuje (live <= offline)")
    out = {"n": n, "sukces_pct": succ_pct, "wrong_lock_pct": wl_pct,
           "no_arrival": na, "dwell": dw, "katastrofy": cat, "verdict": verdict,
           "progi": {"sukces_min": 85.0, "wrong_lock_max": 8.0},
           "per_cell": per_cell, "sufit_ogolem_pct": ceiling["sukces_pct"],
           "strata_vs_sufit_pp": round(ceiling["sukces_pct"] - succ_pct, 1),
           "tick_precision_pct": tick_prec, "n_ticks": ntk,
           "flip_rate_median": statistics.median(flips), "flip_rate_mean": round(statistics.mean(flips), 2),
           "offline_precision_at1": offline, "hipoteza_odswiezania": refresh_hyp,
           "conf_hist_bins": bins, "conf_hist": hist.tolist(),
           "conf_median": round(statistics.median(allconf), 3),
           "wall_median_ms": round(statistics.median(wall), 1),
           "wall_p95_ms": round(ws[int(0.95 * (len(ws) - 1))], 1),
           "wall_L_deliver_s": 0.10}
    json.dump(out, open(os.path.join(OUT, "g1.json"), "w"), indent=2)
    json.dump([{k: e[k] for k in ("seed", "K", "A", "success", "fail_type", "flips",
                "n_detections", "min_conf")} for e in episodes],
              open(os.path.join(OUT, "g1_episodes.json"), "w"), indent=2)
    print(f"G1: sukces {succ_pct}% (prog>=85) | wrong-lock {wl_pct}% (prog<=8) -> {verdict}")
    print(f"  strata vs sufit {out['strata_vs_sufit_pp']}pp | tick-prec {tick_prec} | "
          f"flip median {out['flip_rate_median']} | live vs offline {offline}: {refresh_hyp}")
    print(f"  wall median {out['wall_median_ms']}ms p95 {out['wall_p95_ms']}ms | "
          f"conf median {out['conf_median']} | katastrofy {cat}")
    print(f"per-cell: {json.dumps(per_cell)}")


# ---------------- traces ----------------
def cmd_traces():
    from PIL import Image, ImageDraw
    tdir = os.path.join(OUT, "traces"); os.makedirs(tdir, exist_ok=True)
    eps = json.load(open(os.path.join(OUT, "g1_episodes.json")))
    pick = {}
    succ = [e for e in eps if e["success"]]
    wl = [e for e in eps if e["fail_type"] == "wrong_lock"]
    lowc = sorted([e for e in eps if e["min_conf"] is not None], key=lambda e: e["min_conf"])
    if succ: pick["sukces"] = succ[0]["seed"]
    if wl: pick["wrong_lock"] = wl[0]["seed"]
    if lowc: pick["min_conf"] = lowc[0]["seed"]
    device = get_device(); cfg = load_cfg(); env = make_env(cfg); policy = load_policy(device)
    client = GrounderClient()
    manifest = {}
    try:
        for tag, seed in pick.items():
            r = run_episode_live(env, policy, client, seed, cfg, device, trace=True)
            # oś czasu: lock-id / conf / age vs t
            timeline = []
            for fr in r["trace"]:
                timeline.append({"k": fr["k"], "t": round(fr["k"] * DT, 3),
                                 "cur_src": fr["cur_src"], "conf": fr["target"][4],
                                 "age": fr["target"][5]})
            json.dump({"tag": tag, "seed": seed, "command": None,
                       "timeline": timeline, "ticks": r["ticks"], "result": {
                        "success": r["success"], "fail_type": r["fail_type"]}},
                      open(os.path.join(tdir, f"{tag}_s{seed}.json"), "w"), indent=2)
            # klatki 256 z boxem w momentach zmian locka (kolejne ticki z detekcją)
            obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
            cmd = info["command"]; h = policy.init_hidden(1, device); tk = LiveTargetTracker()
            prev = None; saved = 0
            for k in range(POLICY_STEPS):
                tgt, _ = tk.vector(k)
                a, h = policy.act(obs, tgt, h, device)
                obs, info, done = env.step(a)
                if k % TICK_EVERY == 0 and info.get("rgb256") is not None and saved < 6:
                    box, conf, _ = client.query(info["rgb256"], cmd)
                    tk.observe(k, box, conf)
                    if box is not None and box != prev:
                        im = Image.fromarray(info["rgb256"]).convert("RGB")
                        d = ImageDraw.Draw(im)
                        d.rectangle(box, outline=(255, 150, 20), width=2)
                        d.text((3, 3), f"{cmd} k={k} conf={conf:.2f}", fill=(255, 255, 0))
                        im.save(os.path.join(tdir, f"{tag}_s{seed}_k{k:03d}.png")); saved += 1
                        prev = box
                if done: break
            manifest[tag] = {"seed": seed, "n_frames": saved}
    finally:
        client.close()
    env.close()
    json.dump(manifest, open(os.path.join(tdir, "manifest.json"), "w"), indent=2)
    print(f"traces: {manifest} -> {tdir}/")


if __name__ == "__main__":
    {"unittest": cmd_unittest, "smoke": cmd_smoke, "measure": cmd_measure,
     "traces": cmd_traces}[sys.argv[1]]()
