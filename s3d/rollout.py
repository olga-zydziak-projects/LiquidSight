"""s3d/rollout.py — wspólny bieg epizodu dla fazy 3d (kolektor + harness).

Reużywa ZAMROŻONE komponenty read-only: env, Tracker5 (kanał D3), live YOLO, ekspert,
polityka. Dodaje: (1) maskę dropoutu dostarczeń (mechanika G2, kontrakt D3 nietknięty),
(2) detekcję has_delivery, (3) drop-in filtra na target5[0:4] (age_n nietknięte),
(4) opcjonalny render GT boxa (per tik = etykieta filtra, lub per dostarczenie = wrong-lock).

Determinizm: maska = default_rng([mask_seed, seed]) (rodzina G2). MIERZĘ = RAPORTUJE.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (_ROOT, os.path.join(_ROOT, "frozen_v1")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import env.liquidsight_env  # noqa: E402,F401  (dokłada frozen_v1 na path + inicjalizacja)
from env.scene_attr import bbox_from_mask  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from task import split_state  # noqa: E402
from train.s3b2r import DT, AGE_MAX, K_DEL, Tracker5
from s3b3.live_grounder import TICK_EVERY, iou
from env.liquidsight_env import POLICY_STEPS

N_TICKS = POLICY_STEPS // TICK_EVERY          # 10 (1 Hz)
TICK_PERIOD = TICK_EVERY * DT                 # 1.0 s
R_GOAL, NEAR = 0.25, 0.5


# --- maska dropoutu (mechanika G2, s3b4) -----------------------------------
def make_dropout(mode, param, mask_seed, seed):
    """Zwraca (drops_or_None, burst_ctx). Bernoulli: drops[t]. Burst: ctx=(L, u)."""
    rng = np.random.default_rng([int(mask_seed), int(seed)])
    if mode == "clean":
        return None, None
    if mode == "bernoulli":
        return (rng.random(N_TICKS) < param), None
    if mode == "burst":
        return None, (float(param), float(rng.random()))
    raise ValueError(mode)


def _gt_box_norm(env, did):
    """GT box celu w kadrze 256², znormalizowany /256; None gdy poza kadrem."""
    st = env.env._getDroneStateVector(0)
    s = split_state(st)
    _, seg = drone_camera(env.env.CLIENT, s["pos"], s["quat"], 256, want_seg=True)
    bb = bbox_from_mask(seg, did)
    if bb is None:
        return None
    return np.array([((bb[0] + bb[2]) / 2) / 256.0, ((bb[1] + bb[3]) / 2) / 256.0,
                     (bb[2] - bb[0]) / 256.0, (bb[3] - bb[1]) / 256.0], np.float32)


def _match_delivered(env, did, objects, delivered):
    """Kategoria dostarczonego boxa vs GT: designated|other|background."""
    st = env.env._getDroneStateVector(0)
    s = split_state(st)
    _, seg = drone_camera(env.env.CLIENT, s["pos"], s["quat"], 256, want_seg=True)
    gtb = {o["id"]: bbox_from_mask(seg, o["id"]) for o in objects}
    if gtb.get(did) and iou(delivered, gtb[did]) >= 0.5:
        return "designated"
    if any(i != did and b and iou(delivered, b) >= 0.5 for i, b in gtb.items()):
        return "other"
    return "background"


def run_episode(env, client, seed, *, controller, mode="clean", param=0.0,
                mask_seed=45200, model=None, device=None, expert_factory=None,
                filt=None, gt_every_tick=False, log_input=False):
    """Jeden epizod 3d.

    controller: 'expert' (kolektor) | 'policy' (harness).
    filt: obiekt filtra (reset/step) wpięty na target5[0:4] gdy controller='policy'.
    gt_every_tick: render GT boxa co tik (etykieta filtra — kolektor).
    log_input: loguj wejście filtra [bx,by,bw,bh,has_delivery,age_n] per tik.

    Zwraca dict: success/fail_type + (opcjonalnie) X (T,6), Y (T,4), Ymask (T,),
    wrong-lock decomp, age_at_dwell_entry, rmse-online.
    """
    obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
    command, did, objects = info["command"], info["designated_id"], info["objects"]
    tr = Tracker5()
    drops, burst = make_dropout(mode, param, mask_seed, seed)
    expert = expert_factory(env, obs, info) if controller == "expert" else None
    h = model.init_hidden(1, device) if controller == "policy" else None
    if filt is not None:
        filt.reset()

    X, Y, Ymask = [], [], []
    src_matched = []
    first_lock = None; window = None
    prev_cur = None
    entered = False; age_at_entry = None
    rmse_num = 0.0; rmse_den = 0
    done = False
    k = 0
    for k in range(POLICY_STEPS):
        target5 = tr.vector(k)
        has_lock = tr._cur is not None
        has_delivery = has_lock and (tr._cur != prev_cur)
        prev_cur = tr._cur
        age_n = float(target5[4])
        box4 = target5[:4].astype(np.float32)

        # drop-in filtra (tylko harness/policy; kolektor liczy wejście, nie podmienia)
        applied_target = target5
        filt_out = None
        if filt is not None and controller == "policy":
            filt_out = filt.step(box4, has_lock, has_delivery, age_n)
            applied_target = np.array([filt_out[0], filt_out[1], filt_out[2], filt_out[3],
                                       target5[4]], np.float32)   # age_n NIETKNIETE

        # akcja
        if controller == "expert":
            action = expert.setpoint(k * DT)
        else:
            action, h = model.act(obs, applied_target, h, device)

        # pozycja/dwell-entry
        st = env.env._getDroneStateVector(0)
        pos = np.asarray(split_state(st)["pos"], float)
        if not entered and float(np.linalg.norm(pos - env.hover)) <= R_GOAL:
            entered = True; age_at_entry = age_n

        # etykieta / wejscie
        if log_input:
            X.append(np.array([box4[0], box4[1], box4[2], box4[3],
                               1.0 if has_delivery else 0.0, age_n], np.float32))
        gt_now = _gt_box_norm(env, did) if gt_every_tick else None
        if gt_every_tick:
            if gt_now is None:
                Y.append(np.zeros(4, np.float32)); Ymask.append(0.0)
            else:
                Y.append(gt_now); Ymask.append(1.0)
                # RMSE online estymaty (filtr lub ZOH) vs GT, na tickach z etykieta i lockiem
                if has_lock:
                    est = filt_out if filt_out is not None else box4
                    rmse_num += float(np.sum((np.asarray(est) - gt_now) ** 2)); rmse_den += 4

        obs, info, done = env.step(action)

        # dostarczenie groundera (1 Hz) + maska dropoutu
        if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
            t = k // TICK_EVERY
            box, conf, _ = client.query(info["rgb256"], command)
            if mode == "bernoulli":
                dropped = bool(drops[t])
            elif mode == "burst":
                dropped = bool(window is not None and window[0] <= t < window[1])
            else:
                dropped = False
            delivered = None if (dropped or box is None) else box
            if delivered is not None:
                tr.observe(k, delivered)
                if controller == "policy":
                    src_matched.append(_match_delivered(env, did, objects, delivered))
                if mode == "burst" and first_lock is None:
                    first_lock = t
                    Lt = int(round(param / TICK_PERIOD))
                    earliest, latest = t + 1, N_TICKS - Lt
                    start = earliest if latest < earliest else earliest + int(burst[1] * (latest - earliest + 1))
                    window = (start, start + Lt)
        if done:
            break

    out = {"seed": seed, "success": bool(info["success"]), "fail_type": info["fail_type"],
           "catastrophe": env.is_catastrophe(info["fail_type"]),
           "n_steps": k + 1, "age_at_dwell_entry": age_at_entry,
           "src_matched": src_matched}
    if rmse_den:
        out["rmse_online"] = (rmse_num / rmse_den) ** 0.5
    if log_input:
        out["X"] = np.stack(X)
    if gt_every_tick:
        out["Y"] = np.stack(Y); out["Ymask"] = np.array(Ymask, np.float32)
    return out
