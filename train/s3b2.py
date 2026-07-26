"""s3b2 — trening polityki GOAL-CONDITIONED (3b) + kanał celu (D3) + P-SANITY-3B.

Przepis v2 (ANEKS-4): BC (runda 0) + DAgger 3 rundy, retrening OD ZERA na
agregacie każdą rundę, best-val, 120 epok/etap, lr 1e-3, seed 45020.
Rdzeń goal-conditioned (models/policy_gc, wejście 84). Scena 3b (scene_type='3b').

Kanał celu (kontrakt DECYZJE_3B D3): źródło = gt_bbox_256 wskazanego (conf=1.0),
tick co 12 klatek, dostarczenie na klatce t >= t_zrodla + L_deliver (k_del=k_src+2
bo 0.10/(1/12)=1.2 -> ceil 2), age_s=t-t_zrodla znormalizowany /AGE_MAX=8.0,
ZOH między dostarczeniami, przed pierwszym dostarczeniem no-lock (zera+age=AGE_MAX).
Znana różnica train/live: conf=1.0 (GT) — weryfikuje G1.

CLI: python -m train.s3b2 {train|eval|ceiling}
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env.liquidsight_env import DT_OBS, POLICY_STEPS, SEM_EVERY  # noqa: E402
from env.scene_attr import scene_params  # noqa: E402
from expert.expert import make_expert_for  # noqa: E402
from models.policy_gc import PolicyGC, param_report  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402

# --- kontrakt kanału celu (D3) ----------------------------------------------
L_DELIVER = 0.10
AGE_MAX = 8.0
TICK_EVERY = SEM_EVERY                              # 12 klatek polityki (1 Hz)
DT = DT_OBS                                         # 1/12 s
K_DEL_OFFSET = int(math.ceil((L_DELIVER) / DT))    # = 2 (dostarczenie po 2 klatkach)

# --- recepta v2 (ANEKS-4) ---------------------------------------------------
BATCH = 16
CLIP = 1.0
EPOCHS = 120
ROUNDS = 3
LR = 1e-3
SEED = 45020
BC_SEEDS = list(range(46000, 46270))               # 270 (train); val = holdout 10%
VAL_SEEDS = list(range(46270, 46300))              # 30 (10% z 300) — best-val
DAGGER_SEEDS = [list(range(46300, 46400)),         # r1
                list(range(46400, 46500)),         # r2
                list(range(47000, 47100))]         # r3
EVAL_SEEDS = list(range(46500, 46600))             # P1-3b
SWEEP_SEEDS = list(range(46600, 46650))            # sufit per-komórka (T6)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CKDIR = os.path.join(_ROOT, "ckpt", "s3b2")
OUT = os.path.join(_ROOT, "results", "s3b2")
CKPT = os.path.join(CKDIR, "policy_gc.pt")


# --- tracker kanału celu (online, causal) + asserty kontraktu ---------------
class TargetTracker:
    def __init__(self):
        self.sources = []          # (k_src, bbox256) — widoczne ticki
        self._cur = None           # k_src aktualnie dostarczonego locka
        self._prev_age = None
        self.log = {"n_deliveries": 0, "delivery_frame_ok": True,
                    "age_monotonic_ok": True, "reset_on_delivery_ok": True,
                    "n_frames": 0, "violations": []}

    def observe(self, k_src: int, bbox):
        if bbox is not None:
            self.sources.append((int(k_src), list(bbox)))

    def vector(self, k: int) -> np.ndarray:
        self.log["n_frames"] += 1
        delivered = [(ks, bb) for (ks, bb) in self.sources if ks + K_DEL_OFFSET <= k]
        if not delivered:
            self._prev_age = None
            self._cur = None
            return np.array([0, 0, 0, 0, 0, 1.0], np.float32)   # no-lock
        ks, bb = max(delivered, key=lambda x: x[0])
        cx = ((bb[0] + bb[2]) / 2) / 256.0
        cy = ((bb[1] + bb[3]) / 2) / 256.0
        w = (bb[2] - bb[0]) / 256.0
        h = (bb[3] - bb[1]) / 256.0
        age = (k - ks) * DT
        age_n = min(age / AGE_MAX, 1.0)
        # asserty
        if ks != self._cur:                          # nowe dostarczenie
            self.log["n_deliveries"] += 1
            if k != ks + K_DEL_OFFSET:               # delivery na właściwej klatce
                self.log["delivery_frame_ok"] = False
                self.log["violations"].append(["delivery_frame", k, ks])
            if self._prev_age is not None and not (age <= self._prev_age + 1e-9):
                self.log["reset_on_delivery_ok"] = False   # age powinien spaść
                self.log["violations"].append(["no_reset", k])
        else:                                        # ten sam lock -> age monotoniczny
            if self._prev_age is not None and age < self._prev_age - 1e-9:
                self.log["age_monotonic_ok"] = False
                self.log["violations"].append(["age_nonmono", k])
        self._cur, self._prev_age = ks, age
        return np.array([cx, cy, w, h, 1.0, age_n], np.float32)


def merge_asserts(logs: list) -> dict:
    out = {"n_frames": 0, "n_deliveries": 0, "delivery_frame_ok": True,
           "age_monotonic_ok": True, "reset_on_delivery_ok": True,
           "n_episodes": len(logs), "example_violations": []}
    for lg in logs:
        out["n_frames"] += lg["n_frames"]
        out["n_deliveries"] += lg["n_deliveries"]
        for k in ("delivery_frame_ok", "age_monotonic_ok", "reset_on_delivery_ok"):
            out[k] = out[k] and lg[k]
        if lg["violations"] and len(out["example_violations"]) < 10:
            out["example_violations"].extend(lg["violations"][:3])
    return out


# --- kolektory 3b goal-conditioned ------------------------------------------
def _episode(env, seed, cfg, controller, device=None, model=None):
    """controller: 'expert' (BC) | 'dagger' (model steruje, ekspert etykietuje) |
    'eval' (model steruje). Zwraca dict z tablicami + success/fail + assert log."""
    obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
    expert = make_expert_for(env, obs, info, cfg) if controller in ("expert", "dagger") else None
    h = model.init_hidden(1, device) if controller in ("dagger", "eval") else None
    tr = TargetTracker()
    rgb, kin, dt, tgt, sp = [], [], [], [], []
    done = False
    for k in range(POLICY_STEPS):
        target_k = tr.vector(k)
        if controller in ("expert", "dagger"):
            label = expert.setpoint(k * DT)
            rgb.append(np.ascontiguousarray(obs["rgb"], np.uint8))
            kin.append(np.asarray(obs["kin"], np.float32))
            dt.append(np.asarray(obs["dt"], np.float32))
            tgt.append(target_k)
            sp.append(label.astype(np.float32))
        if controller == "expert":
            action = expert.setpoint(k * DT)
        else:                                        # dagger / eval: model steruje
            action, h = model.act(obs, target_k, h, device)
        obs, info, done = env.step(action)
        if k % TICK_EVERY == 0:                      # tick: zarejestruj źródło (delivery k+2)
            tr.observe(k, info.get("gt_bbox_256"))
        if done:
            break
    out = {"length": len(rgb) if rgb else (k + 1), "success": bool(info["success"]),
           "fail_type": info["fail_type"], "catastrophe": env.is_catastrophe(info["fail_type"]),
           "scene_seed": seed, "assert_log": tr.log}
    if controller in ("expert", "dagger"):
        out.update({"rgb": np.stack(rgb), "kin": np.stack(kin), "dt": np.stack(dt),
                    "target": np.stack(tgt), "setpoint": np.stack(sp)})
    return out


# --- store z kanałem celu ---------------------------------------------------
class StoreGC:
    def __init__(self):
        self.rgb, self.kin, self.dt, self.tgt, self.sp, self.mask = [], [], [], [], [], []

    def add(self, ep):
        T = POLICY_STEPS
        L = ep["length"]
        def pad(a, shape, dtype):
            z = np.zeros((T, *shape), dtype); z[:L] = a[:L]; return torch.from_numpy(z)
        self.rgb.append(pad(ep["rgb"], (64, 64, 3), np.uint8))
        self.kin.append(pad(ep["kin"], (13,), np.float32))
        self.dt.append(pad(ep["dt"], (1,), np.float32))
        self.tgt.append(pad(ep["target"], (6,), np.float32))
        self.sp.append(pad(ep["setpoint"], (6,), np.float32))
        m = np.zeros((T,), np.float32); m[:L] = 1.0
        self.mask.append(torch.from_numpy(m))

    def __len__(self):
        return len(self.rgb)

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
            rgb, kin, dt, tgt, sp, mask = val.batch(idx, device)
            tot += float(masked_mse(model(rgb, kin, dt, tgt), sp, mask)) * len(idx); n += len(idx)
    model.train(); return tot / max(n, 1)


def train_from_scratch(store, val, device, log=print):
    torch.manual_seed(SEED)
    model = PolicyGC().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    rng = np.random.default_rng(SEED)
    tcurve, vcurve, best, best_state, best_ep = [], [], float("inf"), None, -1
    for ep in range(EPOCHS):
        model.train(); order = rng.permutation(len(store)); tl, nb = 0.0, 0
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH].tolist()
            rgb, kin, dt, tgt, sp, mask = store.batch(idx, device)
            loss = masked_mse(model(rgb, kin, dt, tgt), sp, mask)
            if torch.isnan(loss):
                raise RuntimeError("NaN w stracie -> STOP")
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP); opt.step()
            tl += loss.item(); nb += 1
        vl = _val_mse(model, val, device)
        tcurve.append(round(tl / nb, 6)); vcurve.append(round(vl, 6))
        if vl < best:
            best, best_state, best_ep = vl, copy.deepcopy(model.state_dict()), ep
    model.load_state_dict(best_state)
    return model, {"best_val": round(best, 6), "best_epoch": best_ep,
                   "train_mse_start_end": [tcurve[0], tcurve[-1]]}


# ============================ SUBKOMENDY ====================================
def cmd_train():
    os.makedirs(CKDIR, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    print(f"S3b2 trening goal-conditioned | device={device} seed={SEED} lr={LR}", flush=True)
    print(f"params: {json.dumps(param_report(PolicyGC()))}", flush=True)

    # BC collect (train 270 + val 30)
    t0 = time.perf_counter()
    store, val = StoreGC(), StoreGC(); alog = []
    for s in BC_SEEDS:
        ep = _episode(env, s, cfg, "expert"); store.add(ep); alog.append(ep["assert_log"])
    for s in VAL_SEEDS:
        ep = _episode(env, s, cfg, "expert"); val.add(ep); alog.append(ep["assert_log"])
    t_bc_collect = time.perf_counter() - t0
    print(f"BC collect: train={len(store)} val={len(val)} ({t_bc_collect:.0f}s)", flush=True)

    stages = []
    model = None
    for rnd in range(ROUNDS + 1):
        n_succ, t_roll = None, 0.0
        if rnd > 0:
            t1 = time.perf_counter(); model.eval(); n_succ = 0
            for s in DAGGER_SEEDS[rnd - 1]:
                ep = _episode(env, s, cfg, "dagger", device, model)
                n_succ += int(ep["success"]); store.add(ep); alog.append(ep["assert_log"])
            t_roll = time.perf_counter() - t1
        t2 = time.perf_counter()
        model, m = train_from_scratch(store, val, device)
        t_tr = time.perf_counter() - t2
        pct = round(100 * n_succ / len(DAGGER_SEEDS[rnd - 1]), 1) if rnd > 0 else None
        rec = {"round": rnd, "store": len(store), "rollout_succ_pct": pct,
               "best_val": m["best_val"], "best_epoch": m["best_epoch"],
               "train_mse_start_end": m["train_mse_start_end"],
               "sec_rollout": round(t_roll, 1), "sec_train": round(t_tr, 1)}
        stages.append(rec)
        print(f"[r{rnd}] store={len(store)} best_val={m['best_val']:.5f}@{m['best_epoch']} "
              f"rollout={pct} ({t_roll:.0f}+{t_tr:.0f}s)", flush=True)

    torch.save(model.state_dict(), CKPT)
    asserts = merge_asserts(alog)
    total_s = round(t_bc_collect + sum(s["sec_rollout"] + s["sec_train"] for s in stages), 1)
    log = {"seed": SEED, "lr": LR, "params": param_report(PolicyGC()),
           "bc_collect_s": round(t_bc_collect, 1), "stages": stages,
           "total_cycle_s": total_s, "total_cycle_h": round(total_s / 3600, 2),
           "contract_asserts": asserts, "ckpt": CKPT,
           "known_diff_train_live": "conf=1.0 (GT-fed); grounder live conf<1 — G1"}
    json.dump(log, open(os.path.join(OUT, "train_log.json"), "w"), indent=2)
    json.dump(asserts, open(os.path.join(OUT, "contract_asserts.json"), "w"), indent=2)
    env.close()
    print(f"ZAPIS -> {CKPT} ; log -> {OUT}/train_log.json ; cykl {total_s:.0f}s "
          f"({total_s/3600:.2f}h)", flush=True)
    print(f"ASSERTY: {json.dumps({k: asserts[k] for k in ('n_frames','n_deliveries','delivery_frame_ok','age_monotonic_ok','reset_on_delivery_ok')})}", flush=True)


def _load_model(device):
    model = PolicyGC().to(device)
    model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    return model


def _eval_set(seeds, tag):
    import collections
    device = get_device(); cfg = load_cfg(); env = make_env(cfg); model = _load_model(device)
    succ = 0; fails = collections.Counter(); cat = 0
    per_cell = collections.defaultdict(lambda: [0, 0, 0])   # [n, succ, wrong]
    for s in seeds:
        K, A = scene_params(s)
        ep = _episode(env, s, cfg, "eval", device, model)
        cell = per_cell[(K, A)]; cell[0] += 1
        if ep["success"]:
            succ += 1; cell[1] += 1
        else:
            fails[ep["fail_type"]] += 1
            if ep["catastrophe"]:
                cat += 1
            if ep["fail_type"] == "wrong_lock":
                cell[2] += 1
    env.close()
    n = len(seeds); wl = fails.get("wrong_lock", 0)
    res = {"tag": tag, "n": n, "sukces": succ, "sukces_pct": round(100 * succ / n, 1),
           "wrong_lock": wl, "wrong_lock_pct": round(100 * wl / n, 1),
           "no_arrival": fails.get("no_arrival", 0), "dwell": fails.get("dwell", 0),
           "katastrofy": cat, "fail_types": dict(fails),
           "per_cell": {f"K{K}_{A}": {"n": v[0], "sukces": v[1],
                        "sukces_pct": round(100 * v[1] / v[0], 1) if v[0] else None,
                        "wrong_lock": v[2]} for (K, A), v in sorted(per_cell.items())}}
    return res


def cmd_eval():
    res = _eval_set(EVAL_SEEDS, "P1-3b (eval 46500-46599)")
    verdict = "PASS" if (res["sukces_pct"] >= 90.0 and res["wrong_lock_pct"] < 2.0) else "FAIL"
    res["verdict"] = verdict
    json.dump(res, open(os.path.join(OUT, "p1_3b.json"), "w"), indent=2)
    print(f"P1-3b: {res['sukces_pct']}% sukces | wrong-lock {res['wrong_lock_pct']}% "
          f"| no-arrival {res['no_arrival']} dwell {res['dwell']} kat {res['katastrofy']} "
          f"-> {verdict}", flush=True)
    print(f"per-cell: {json.dumps(res['per_cell'])}", flush=True)


def cmd_ceiling():
    res = _eval_set(SWEEP_SEEDS, "sufit sweep 46600-46649")
    json.dump(res, open(os.path.join(OUT, "ceiling.json"), "w"), indent=2)
    print(f"SUFIT sweep: {res['sukces_pct']}% sukces (wrong-lock {res['wrong_lock_pct']}%)", flush=True)
    print(f"per-cell: {json.dumps(res['per_cell'])}", flush=True)


if __name__ == "__main__":
    {"train": cmd_train, "eval": cmd_eval, "ceiling": cmd_ceiling}[sys.argv[1]]()
