"""s3b2r — ANEKS-3B: retrening polityki BEZ conf + dane LIVE-FED + G1-R.

Kanał 5-dim (cx,cy,w,h,age_s), zrodlo = ZYWY YOLO przez serwer .venv_s3b0 (kontrakt
D3: tick 1 Hz, L_deliver 0.10 s -> k_del=k_src+2, ZOH, no-lock). conf LOGOWANY per
tick, NIE podawany polityce (assert). Przepis v2 (ANEKS-4), seed 45020, lr 1e-3.

CLI: python -m train.s3b2r {train|precond|g1r}
"""
from __future__ import annotations

import collections
import copy
import json
import math
import os
import statistics
import sys
import time

import numpy as np
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import DT_OBS, POLICY_STEPS  # noqa: E402
from env.scene_attr import bbox_from_mask, scene_params  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from expert.expert import make_expert_for  # noqa: E402
from models.policy_gc5 import PolicyGC5, param_report  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from task import split_state  # noqa: E402
from s3b3.live_grounder import TICK_EVERY, GrounderClient, iou  # noqa: E402

# kontrakt D3 (bez zmian)
L_DELIVER, AGE_MAX = 0.10, 8.0
K_DEL = int(math.ceil(L_DELIVER / DT_OBS))         # 2
DT = DT_OBS
# recepta v2
BATCH, CLIP, EPOCHS, ROUNDS, LR, SEED = 16, 1.0, 120, 3, 1e-3, 45020
BC_SEEDS = list(range(46000, 46270))               # 270 train
VAL_SEEDS = list(range(46270, 46300))              # 30 val
DAGGER_SEEDS = [list(range(46300, 46400)), list(range(46400, 46500)), list(range(47000, 47100))]
EVAL_SEEDS = list(range(46500, 46600))
SWEEP_SEEDS = list(range(46600, 46650))
CKDIR = os.path.join(_ROOT, "ckpt", "s3b2r")
OUT = os.path.join(_ROOT, "results", "s3b2r")
CKPT = os.path.join(CKDIR, "policy_gc5.pt")


class Tracker5:
    """Kanał 5-dim LIVE (bez conf); delivery k_src+2, ZOH, no-lock + asserty."""
    def __init__(self):
        self.sources = []
        self._cur = None; self._prev_age = None
        self.log = {"n_frames": 0, "n_deliveries": 0, "delivery_frame_ok": True,
                    "age_monotonic_ok": True}

    def observe(self, k, box):                     # conf NIE jest przyjmowany
        if box is not None:
            self.sources.append((int(k), list(box)))

    def vector(self, k):
        self.log["n_frames"] += 1
        deliv = [(ks, bb) for (ks, bb) in self.sources if ks + K_DEL <= k]
        if not deliv:
            self._cur = None; self._prev_age = None
            return np.array([0, 0, 0, 0, 1.0], np.float32)   # no-lock (5-dim)
        ks, bb = max(deliv, key=lambda x: x[0])
        cx = ((bb[0] + bb[2]) / 2) / 256.0; cy = ((bb[1] + bb[3]) / 2) / 256.0
        w = (bb[2] - bb[0]) / 256.0; h = (bb[3] - bb[1]) / 256.0
        age = (k - ks) * DT; age_n = min(age / AGE_MAX, 1.0)
        if ks != self._cur:
            self.log["n_deliveries"] += 1
            if k != ks + K_DEL:
                self.log["delivery_frame_ok"] = False
        elif self._prev_age is not None and age < self._prev_age - 1e-9:
            self.log["age_monotonic_ok"] = False
        self._cur, self._prev_age = ks, age
        return np.array([cx, cy, w, h, age_n], np.float32)


def episode_live(env, client, seed, cfg, controller, model=None, device=None, conf_log=None,
                 box_source="live"):
    obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
    command, did = info["command"], info["designated_id"]
    expert = make_expert_for(env, obs, info, cfg) if controller in ("expert", "dagger") else None
    h = model.init_hidden(1, device) if controller in ("dagger", "eval") else None
    tr = Tracker5()
    rgb, kin, dt, tgt, sp = [], [], [], [], []
    done = False
    for k in range(POLICY_STEPS):
        target5 = tr.vector(k)
        assert target5.shape[0] == 5, "kanal musi byc 5-dim (conf usuniety)"
        if controller in ("expert", "dagger"):
            label = expert.setpoint(k * DT)
            rgb.append(np.ascontiguousarray(obs["rgb"], np.uint8))
            kin.append(np.asarray(obs["kin"], np.float32)); dt.append(np.asarray(obs["dt"], np.float32))
            tgt.append(target5); sp.append(label.astype(np.float32))
        if controller == "expert":
            action = expert.setpoint(k * DT)
        else:
            action, h = model.act(obs, target5, h, device)
        obs, info, done = env.step(action)
        if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
            if box_source == "gt":                 # Z2' GT-fed: box zrodlowy = gt_bbox_256
                box, conf = info.get("gt_bbox_256"), None
            else:                                  # live: zywy YOLO
                box, conf, _ = client.query(info["rgb256"], command)
            tr.observe(k, box)                     # conf NIE wchodzi (kanal 5-dim)
            if conf_log is not None:
                conf_log.append({"seed": seed, "k": k, "conf": conf, "det": box is not None,
                                 "src": box_source})
        if done:
            break
    out = {"length": len(rgb) if rgb else (k + 1), "success": bool(info["success"]),
           "fail_type": info["fail_type"], "catastrophe": env.is_catastrophe(info["fail_type"]),
           "seed": seed, "assert_log": tr.log, "n_ticks_det": sum(1 for _ in tr.sources)}
    if controller in ("expert", "dagger"):
        out.update({"rgb": np.stack(rgb), "kin": np.stack(kin), "dt": np.stack(dt),
                    "target": np.stack(tgt), "setpoint": np.stack(sp)})
    return out


class Store5:
    def __init__(self):
        self.rgb, self.kin, self.dt, self.tgt, self.sp, self.mask = ([] for _ in range(6))

    def add(self, ep):
        T, L = POLICY_STEPS, ep["length"]
        pad = lambda a, sh, dt: torch.from_numpy(np.concatenate([a[:L], np.zeros((T - L, *sh), dt)]))
        self.rgb.append(pad(ep["rgb"], (64, 64, 3), np.uint8))
        self.kin.append(pad(ep["kin"], (13,), np.float32))
        self.dt.append(pad(ep["dt"], (1,), np.float32))
        self.tgt.append(pad(ep["target"], (5,), np.float32))
        self.sp.append(pad(ep["setpoint"], (6,), np.float32))
        m = np.zeros((T,), np.float32); m[:L] = 1.0; self.mask.append(torch.from_numpy(m))

    def __len__(self): return len(self.rgb)

    def batch(self, idx, device):
        g = lambda lst: torch.stack([lst[i] for i in idx]).to(device)
        return g(self.rgb), g(self.kin), g(self.dt), g(self.tgt), g(self.sp), g(self.mask)


def masked_mse(pred, target, mask):
    err = ((pred - target) ** 2).mean(dim=-1)
    return (err * mask).sum() / mask.sum().clamp_min(1.0)


def _val_mse(model, val, device):
    model.eval(); tot, n = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(val), BATCH):
            idx = list(range(i, min(i + BATCH, len(val))))
            rgb, kin, dt, tg, sp, mask = val.batch(idx, device)
            tot += float(masked_mse(model(rgb, kin, dt, tg), sp, mask)) * len(idx); n += len(idx)
    model.train(); return tot / max(n, 1)


def train_from_scratch(store, val, device):
    torch.manual_seed(SEED)
    model = PolicyGC5().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    rng = np.random.default_rng(SEED)
    best, best_state, best_ep, tc = float("inf"), None, -1, []
    for ep in range(EPOCHS):
        model.train(); order = rng.permutation(len(store)); tl, nb = 0.0, 0
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH].tolist()
            rgb, kin, dt, tg, sp, mask = store.batch(idx, device)
            loss = masked_mse(model(rgb, kin, dt, tg), sp, mask)
            if torch.isnan(loss):
                raise RuntimeError("NaN -> STOP")
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP); opt.step()
            tl += loss.item(); nb += 1
        vl = _val_mse(model, val, device); tc.append(round(tl / nb, 6))
        if vl < best:
            best, best_state, best_ep = vl, copy.deepcopy(model.state_dict()), ep
    model.load_state_dict(best_state)
    return model, {"best_val": round(best, 6), "best_epoch": best_ep,
                   "train_mse_start_end": [tc[0], tc[-1]]}


def cmd_train():
    os.makedirs(CKDIR, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    print(f"S3b2-R live-fed | device={device} | params: {json.dumps(param_report(PolicyGC5()))}", flush=True)
    client = GrounderClient()
    conf_log, alog = [], []
    try:
        t0 = time.perf_counter()
        store, val = Store5(), Store5()
        for s in BC_SEEDS:
            ep = episode_live(env, client, s, cfg, "expert", conf_log=conf_log); store.add(ep); alog.append(ep["assert_log"])
        for s in VAL_SEEDS:
            ep = episode_live(env, client, s, cfg, "expert", conf_log=conf_log); val.add(ep); alog.append(ep["assert_log"])
        t_bc = time.perf_counter() - t0
        print(f"BC live-fed: train={len(store)} val={len(val)} ({t_bc:.0f}s)", flush=True)

        stages, model = [], None
        for rnd in range(ROUNDS + 1):
            n_succ, t_roll = None, 0.0
            if rnd > 0:
                t1 = time.perf_counter(); model.eval(); n_succ = 0
                for s in DAGGER_SEEDS[rnd - 1]:
                    ep = episode_live(env, client, s, cfg, "dagger", model, device, conf_log)
                    n_succ += int(ep["success"]); store.add(ep); alog.append(ep["assert_log"])
                t_roll = time.perf_counter() - t1
            t2 = time.perf_counter(); model, m = train_from_scratch(store, val, device)
            t_tr = time.perf_counter() - t2
            pct = round(100 * n_succ / len(DAGGER_SEEDS[rnd - 1]), 1) if rnd > 0 else None
            stages.append({"round": rnd, "store": len(store), "rollout_succ_pct": pct,
                           "best_val": m["best_val"], "best_epoch": m["best_epoch"],
                           "sec_rollout": round(t_roll, 1), "sec_train": round(t_tr, 1)})
            print(f"[r{rnd}] store={len(store)} best_val={m['best_val']:.5f}@{m['best_epoch']} "
                  f"rollout={pct} ({t_roll:.0f}+{t_tr:.0f}s)", flush=True)
    finally:
        client.close()
    env.close()
    torch.save(model.state_dict(), CKPT)
    # asserty (w tym: conf NIE w wejsciu -> target_dim==5)
    asserts = {"n_frames": sum(a["n_frames"] for a in alog),
               "n_deliveries": sum(a["n_deliveries"] for a in alog),
               "delivery_frame_ok": all(a["delivery_frame_ok"] for a in alog),
               "age_monotonic_ok": all(a["age_monotonic_ok"] for a in alog),
               "conf_nie_w_wejsciu": PolicyGC5.TARGET_DIM == 5}
    total = round(t_bc + sum(s["sec_rollout"] + s["sec_train"] for s in stages), 1)
    json.dump({"params": param_report(PolicyGC5()), "bc_collect_s": round(t_bc, 1),
               "stages": stages, "total_cycle_s": total, "total_cycle_h": round(total / 3600, 2),
               "contract_asserts": asserts, "ckpt": CKPT},
              open(os.path.join(OUT, "train_log.json"), "w"), indent=2)
    with open(os.path.join(OUT, "conf_log.jsonl"), "w") as f:
        for r in conf_log:
            f.write(json.dumps(r) + "\n")
    print(f"ZAPIS -> {CKPT} ; cykl {total:.0f}s ({total/3600:.2f}h) ; "
          f"asserty {json.dumps(asserts)}", flush=True)


def _load(device):
    m = PolicyGC5().to(device); m.load_state_dict(torch.load(CKPT, map_location=device)); m.eval(); return m


def _eval_live(seeds, tag, want_secondary=False):
    device = get_device(); cfg = load_cfg(); env = make_env(cfg); model = _load(device)
    client = GrounderClient()
    succ = 0; fails = collections.Counter(); cat = 0
    per_cell = collections.defaultdict(lambda: [0, 0, 0]); flips = []; tickmatch = collections.Counter(); ages = []
    audit_f = open(os.path.join(OUT, f"{tag}_tick_audit.jsonl"), "w") if want_secondary else None
    try:
        for s in seeds:
            K, A = scene_params(s)
            obs, info = env.reset(scene_seed=s, level="T0", scene_type="3b")
            command, did, objects = info["command"], info["designated_id"], info["objects"]
            h = model.init_hidden(1, device); tr = Tracker5(); delivered = []
            for k in range(POLICY_STEPS):
                tgt = tr.vector(k); ages.append(float(tgt[4]))
                action, h = model.act(obs, tgt, h, device)
                obs, info, done = env.step(action)
                if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
                    box, conf, _ = client.query(info["rgb256"], command)
                    tr.observe(k, box)
                    if want_secondary:
                        st = env.env._getDroneStateVector(0); ss = split_state(st)
                        _, seg = drone_camera(env.env.CLIENT, ss["pos"], ss["quat"], 256, want_seg=True)
                        gtb = {o["id"]: bbox_from_mask(seg, o["id"]) for o in objects}
                        if box is None:
                            m = "no_detection"; oid = None
                        elif gtb.get(did) and iou(box, gtb[did]) >= 0.5:
                            m = "designated"; oid = did
                        else:
                            oid = next((i for i, b in gtb.items() if i != did and b and iou(box, b) >= 0.5), None)
                            m = "other" if oid else "background"
                        tickmatch[m] += 1
                        if box is not None: delivered.append(oid)
                        audit_f.write(json.dumps({"seed": s, "k": k, "conf": conf, "matched": m}) + "\n")
                if done: break
            flips.append(sum(1 for a, b in zip(delivered, delivered[1:]) if a != b))
            c = per_cell[(K, A)]; c[0] += 1; c[1] += int(info["success"]); c[2] += int(info["fail_type"] == "wrong_lock")
            if info["success"]: succ += 1
            else:
                fails[info["fail_type"]] += 1; cat += int(env.is_catastrophe(info["fail_type"]))
    finally:
        client.close()
        if audit_f: audit_f.close()
    env.close()
    n = len(seeds); wl = fails.get("wrong_lock", 0)
    res = {"tag": tag, "n": n, "sukces_pct": round(100 * succ / n, 1), "wrong_lock_pct": round(100 * wl / n, 1),
           "no_arrival": fails.get("no_arrival", 0), "dwell": fails.get("dwell", 0), "katastrofy": cat,
           "per_cell": {f"K{K}_{A}": {"n": v[0], "sukces_pct": round(100 * v[1] / v[0], 1), "wrong_lock": v[2]}
                        for (K, A), v in sorted(per_cell.items())}}
    if want_secondary:
        ntk = sum(tickmatch.values())
        res["tick_precision_pct"] = {k: round(100 * tickmatch[k] / ntk, 1) for k in
                                     ("designated", "other", "background", "no_detection")}
        res["flip_rate_median"] = statistics.median(flips)
        res["age_hist_bins"] = [0, .1, .25, .5, .75, 1.01]
        res["age_hist"] = np.histogram(ages, bins=res["age_hist_bins"])[0].tolist()
    return res


def cmd_precond():
    r = _eval_live(EVAL_SEEDS, "precond_R")
    r["verdict"] = "PASS" if (r["sukces_pct"] >= 85.0 and r["wrong_lock_pct"] <= 8.0) else "FAIL"
    json.dump(r, open(os.path.join(OUT, "precond_R.json"), "w"), indent=2)
    print(f"PRECONDITION-R: sukces {r['sukces_pct']}% (>=85) wrong-lock {r['wrong_lock_pct']}% (<=8) "
          f"-> {r['verdict']} | per-cell {json.dumps(r['per_cell'])}", flush=True)


def cmd_g1r():
    ceil = json.load(open(os.path.join(_ROOT, "results/s3b2/ceiling.json")))
    r = _eval_live(SWEEP_SEEDS, "G1_R", want_secondary=True)
    r["verdict"] = "PASS" if (r["sukces_pct"] >= 85.0 and r["wrong_lock_pct"] <= 8.0) else "FAIL"
    r["sufit_pct"] = ceil["sukces_pct"]; r["strata_vs_sufit_pp"] = round(ceil["sukces_pct"] - r["sukces_pct"], 1)
    r["vs_G1_FAIL"] = {"live_12pct": 12.0, "wrong_lock_20pct": 20.0}
    json.dump(r, open(os.path.join(OUT, "g1_R.json"), "w"), indent=2)
    print(f"G1-R: sukces {r['sukces_pct']}% (>=85) wrong-lock {r['wrong_lock_pct']}% (<=8) -> {r['verdict']}", flush=True)
    print(f"  strata vs sufit {r['strata_vs_sufit_pp']}pp | tick-prec {r['tick_precision_pct']} | "
          f"flip {r['flip_rate_median']} | vs G1-FAIL 12%/20%", flush=True)
    print(f"  per-cell {json.dumps(r['per_cell'])}", flush=True)


if __name__ == "__main__":
    {"train": cmd_train, "precond": cmd_precond, "g1r": cmd_g1r}[sys.argv[1]]()
