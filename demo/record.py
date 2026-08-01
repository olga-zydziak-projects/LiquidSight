"""demo/record.py — deterministyczny recorder epizodów dema (NAGRANIE != POMIAR).

Odtwarza wybrane seedy/maski (identyczne z pomiarem) na FROZEN polityce + grounderze + osłonie
i zrzuca per tick: render 3D (kamera zewnętrzna śledząca), klatkę 256² z bbox, klatkę 64²,
stan kanału (age), log osłony. Wyjście: results/demo/<akt>/{3d,cam256,cam64}/fNNN.jpg + trace.jsonl.

Maski i logika dropoutu 1:1 z train/s3b4.py (burst) i s3c1/measure_s1.py (Bernoulli) —
determinizm gwarantuje zgodność wyniku z etykietą prowieniencji (weryfikowane w manifescie).

shield_mode: apply (akty 1,2,4) | shadow (akt 3: G2 bez osłony — decyzje liczone i pokazane,
NIE stosowane, więc wynik = G2) | off.

CLI: .venv/bin/python -m demo.record [akt ...]   (domyślnie wszystkie)
"""
from __future__ import annotations
import json
import os
import sys

import numpy as np
import pybullet as p
import torch
from PIL import Image, ImageDraw

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import POLICY_STEPS  # noqa: E402
from env.scene_attr import scene_params, bbox_from_mask  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from models.policy_gc5 import PolicyGC5  # noqa: E402
from train.common import get_device, load_cfg, make_env  # noqa: E402
from task import split_state  # noqa: E402
from train.s3b2r import DT, AGE_MAX, K_DEL, Tracker5, CKPT  # noqa: E402
from s3b3.live_grounder import TICK_EVERY, GrounderClient, iou  # noqa: E402
from s3c1.shield import Shield, HOLD, REFUSE  # noqa: E402
from s3c1.traps import relocate_designated_beyond_geofence  # noqa: E402

OUT = os.path.join(_ROOT, "results", "demo")
N_TICKS = POLICY_STEPS // TICK_EVERY
TICK_PERIOD = TICK_EVERY * DT
NEAR = 0.5
W3D, H3D = 960, 540          # kamera zewnętrzna (qHD, downsample z 720p)
JPEG_Q = 72

# scenariusz FROZEN (DEMO.md). mask: {"type": clean|bernoulli|burst|geofence, ...}
EPISODES = [
    {"act": "act1", "seed": 46513, "mask": {"type": "clean"}, "mask_seed": None,
     "shield_mode": "shadow", "expect": "SUKCES"},   # baza (osłona transparentna) — sukces odporny
    {"act": "act2", "seed": 46505, "mask": {"type": "clean"}, "mask_seed": None,
     "shield_mode": "apply", "expect": "SUKCES", "saliency": True},
    {"act": "act3", "seed": 46507, "mask": {"type": "burst", "L": 5.0}, "mask_seed": 45105,
     "shield_mode": "shadow", "expect": "SUKCES"},
    {"act": "act4a", "seed": 47425, "mask": {"type": "geofence"}, "mask_seed": None,
     "shield_mode": "apply", "expect": "REFUSE(GEOFENCE)"},
    {"act": "act4b", "seed": 46503, "mask": {"type": "bernoulli", "p": 0.5}, "mask_seed": 45102,
     "shield_mode": "apply", "expect": "REFUSE(STALE_AT_DWELL)"},
]


def render_3d(env, drone_pos):
    eye = [drone_pos[0] - 1.6, drone_pos[1] - 1.6, drone_pos[2] + 1.25]
    view = p.computeViewMatrix(eye, list(drone_pos), [0, 0, 1])
    proj = p.computeProjectionMatrixFOV(55, W3D / H3D, 0.1, 12.0)
    w, h, rgb, _, _ = p.getCameraImage(W3D, H3D, view, proj,
                                       renderer=p.ER_TINY_RENDERER,
                                       physicsClientId=env.env.CLIENT)
    return np.reshape(np.asarray(rgb, np.uint8), (h, w, 4))[:, :, :3]


def save_jpg(arr, path, size=None):
    im = Image.fromarray(arr)
    if size:
        im = im.resize(size, Image.NEAREST)
    im.save(path, "JPEG", quality=JPEG_Q)


def saliency_overlay(model, obs, target5, h, device):
    """|grad(Σ|setpoint|, rgb64)| max po kanałach; top-2% pikseli na czerwono (F3_GATE par.6 W3)."""
    import torch.nn.functional as _F  # noqa
    rgb = torch.as_tensor(np.ascontiguousarray(obs["rgb"]), device=device).float().unsqueeze(0).requires_grad_(True)
    kin = torch.as_tensor(obs["kin"], dtype=torch.float32, device=device).unsqueeze(0)
    dt = torch.as_tensor(obs["dt"], dtype=torch.float32, device=device).unsqueeze(0)
    tg = torch.as_tensor(np.asarray(target5, np.float32), device=device).unsqueeze(0)
    feat = model.encoder(rgb)
    x = torch.cat([feat, kin, dt, tg], dim=-1)
    h2 = model.core(x, h.detach())
    from models.policy import _scale_setpoint
    sp = _scale_setpoint(model.head(h2))
    model.zero_grad(set_to_none=True)
    sp.abs().sum().backward()
    sal = rgb.grad.abs().squeeze(0).amax(dim=-1).cpu().numpy()      # (64,64)
    n = sal.size; k2 = max(1, int(round(0.02 * n)))
    thr = np.partition(sal.flatten(), n - k2)[n - k2]
    base = np.asarray(obs["rgb"], np.uint8).astype(np.float32)
    hot = sal >= thr
    # przyciemnij tło, nałóż czerwień na top-2%
    over = base * 0.55
    over[hot] = over[hot] * 0.3 + np.array([255, 40, 40]) * 0.7
    return over.clip(0, 255).astype(np.uint8)


def draw_bbox256(rgb256, box, color):
    im = Image.fromarray(rgb256).convert("RGB")
    if box is not None:
        d = ImageDraw.Draw(im)
        d.rectangle([box[0], box[1], box[2], box[3]], outline=color, width=3)
    return np.asarray(im)


def burst_window(u, L, first_lock):
    Lt = int(round(L / TICK_PERIOD))
    earliest, latest = first_lock + 1, N_TICKS - Lt
    start = earliest if latest < earliest else earliest + int(u * (latest - earliest + 1))
    return (start, start + Lt)


def record_episode(env, client, model, device, ep):
    act, seed, mask = ep["act"], ep["seed"], ep["mask"]
    d3 = os.path.join(OUT, act, "3d"); c256 = os.path.join(OUT, act, "cam256")
    c64 = os.path.join(OUT, act, "cam64")
    for d in (d3, c256, c64):
        os.makedirs(d, exist_ok=True)
    do_saliency = bool(ep.get("saliency"))
    sal_dir = os.path.join(OUT, act, "saliency")
    if do_saliency:
        os.makedirs(sal_dir, exist_ok=True)
    sal_img = None
    obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
    if mask["type"] == "geofence":
        relocate_designated_beyond_geofence(env, coord=2.2)
    command, did, objects = info["command"], info["designated_id"], info["objects"]
    K, A = scene_params(seed)
    h = model.init_hidden(1, device); tr = Tracker5()
    # maska dropoutu (determinizm jak w pomiarze)
    drops = np.zeros(N_TICKS, bool); u = None; window = None; first_lock = None
    if mask["type"] in ("bernoulli", "burst"):
        rng = np.random.default_rng([ep["mask_seed"], seed])
        if mask["type"] == "bernoulli":
            drops = rng.random(N_TICKS) < mask["p"]
        else:
            u = float(rng.random())
    sh = Shield(arena_half=env.cfg["arena_half"], margin=0.2, near=NEAR,
                theta_age_s=2.0, t_acq_s=3.0, t_hold_s=3.0, dt=DT)
    sh.reset(hover_xy=(float(env.hover[0]), float(env.hover[1])))
    apply_shield = ep["shield_mode"] == "apply"
    conf_latest = None; last256 = None; last_box = None; last_box_color = "#22c55e"
    wrong_lock_seen = 0
    trace = []; fidx = 0

    def dump(k, dec, done_flag):
        nonlocal fidx, last256
        st = env.env._getDroneStateVector(0); sp = split_state(st)
        pos = np.asarray(sp["pos"], float)
        img3d = render_3d(env, pos)
        save_jpg(img3d, os.path.join(d3, f"f{fidx:03d}.jpg"))
        # 256 z bbox (held ZOH); 64 = obs rgb
        rgb256 = info.get("rgb256")
        if rgb256 is not None:
            last256 = rgb256
        frame256 = last256 if last256 is not None else np.zeros((256, 256, 3), np.uint8)
        save_jpg(draw_bbox256(frame256, last_box, last_box_color),
                 os.path.join(c256, f"f{fidx:03d}.jpg"))
        save_jpg(np.asarray(obs["rgb"], np.uint8), os.path.join(c64, f"f{fidx:03d}.jpg"),
                 size=(192, 192))
        if do_saliency and sal_img is not None:
            save_jpg(sal_img, os.path.join(sal_dir, f"f{fidx:03d}.jpg"), size=(192, 192))
        trace.append({"f": fidx, "k": k, "t": round(k * DT, 3),
                      "pos": [round(float(x), 3) for x in pos],
                      "age_s": (None if dec.get("_age") is None else round(dec["_age"], 2)),
                      "conf": (None if conf_latest is None else round(conf_latest, 4)),
                      "link": dec.get("_link"), "wrong_lock": wrong_lock_seen,
                      "state": dec["state"], "rule": dec.get("rule"),
                      "decision": dec["decision"], "reason": dec.get("reason"),
                      "shadow": (not apply_shield)})
        fidx += 1

    refused = None; k = 0
    for k in range(POLICY_STEPS):
        target5 = tr.vector(k)
        if do_saliency:
            sal_img = saliency_overlay(model, obs, target5, h, device)
        action, h = model.act(obs, target5, h, device)
        st = env.env._getDroneStateVector(0); pos = np.asarray(split_state(st)["pos"], float)
        has_lock = any(ks + K_DEL <= k for (ks, _) in tr.sources)
        age_s = float(target5[4]) * AGE_MAX
        dist = float(np.linalg.norm(pos - env.hover))
        dec = sh.step(k, pos, has_lock, age_s if has_lock else None, conf_latest, dist)
        dec["_age"] = age_s if has_lock else None
        dec["_link"] = ("frozen" if (has_lock and age_s > 6.0) else
                        ("stale" if (has_lock and age_s > 2.0) else
                         ("live" if has_lock else "seeking")))
        applied = action
        if apply_shield and dec["decision"] == REFUSE:
            refused = dec
        elif apply_shield and dec["decision"] == HOLD:
            applied = np.array([pos[0], pos[1], pos[2], 0.0, 0.0, 0.0], np.float32)
        dump(k, dec, False)
        if refused is not None:
            break
        obs, info, done = env.step(applied)
        # grounder tick + dostarczenie wg maski
        if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
            t = k // TICK_EVERY
            box, conf, _ = client.query(info["rgb256"], command)
            if conf is not None:
                conf_latest = conf
            if mask["type"] == "burst" and first_lock is None and box is not None:
                first_lock = t; window = burst_window(u, mask["L"], first_lock)
            dropped = bool(drops[t]) if mask["type"] == "bernoulli" else \
                      bool(window is not None and window[0] <= t < window[1]) if mask["type"] == "burst" else False
            delivered = None if (dropped or box is None) else box
            if delivered is not None:
                tr.observe(k, delivered)
                last_box = delivered
                # audyt GT (wrong-lock / kolor bbox) — te same reguły co pomiar
                _, seg = drone_camera(env.env.CLIENT, split_state(st)["pos"],
                                      split_state(st)["quat"], 256, want_seg=True)
                gtb = {o["id"]: bbox_from_mask(seg, o["id"]) for o in objects}
                if gtb.get(did) and iou(delivered, gtb[did]) >= 0.5:
                    last_box_color = "#22c55e"
                elif any(i != did and b and iou(delivered, b) >= 0.5 for i, b in gtb.items()):
                    last_box_color = "#ef4444"; wrong_lock_seen = 1
                else:
                    last_box_color = "#eab308"
        if done:
            break
    # epizod geofence: refuse @k=0 -> dograj kilka statycznych klatek sceny z banerem
    if refused is not None and k == 0:
        for _ in range(24):
            dump(0, refused, True)

    success = bool(info["success"]); ft = info["fail_type"]
    if refused is not None:
        wynik = f"REFUSE({refused['reason']})"
    elif success:
        wynik = "SUKCES"
    elif ft == "wrong_lock":
        wynik = "PORAZKA(wrong_action)"
    else:
        wynik = f"PORAZKA({ft})"
    json.dump({"trace": trace}, open(os.path.join(OUT, act, "trace.jsonl"), "w"))
    meta = {"act": act, "seed": seed, "K": K, "A": A, "command": command,
            "mask": mask, "mask_seed": ep["mask_seed"], "shield_mode": ep["shield_mode"],
            "wynik": wynik, "expect": ep["expect"], "match": wynik == ep["expect"],
            "n_frames": fidx}
    print(f"[{act}] seed {seed} {K}/{A} mask={mask['type']} -> {wynik} "
          f"(oczek. {ep['expect']}, match={meta['match']}) frames={fidx}", flush=True)
    return meta


def main(acts):
    os.makedirs(OUT, exist_ok=True)
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    manifest = []
    try:
        for ep in EPISODES:
            if acts and ep["act"] not in acts:
                continue
            manifest.append(record_episode(env, client, model, device, ep))
    finally:
        client.close(); env.close()
    # scal z istniejącym manifestem (gdy nagrywamy pojedynczy akt)
    mpath = os.path.join(OUT, "manifest.json")
    prev = {m["act"]: m for m in json.load(open(mpath))["episodes"]} if os.path.exists(mpath) else {}
    for m in manifest:
        prev[m["act"]] = m
    order = ["act1", "act2", "act3", "act4a", "act4b"]
    merged = [prev[a] for a in order if a in prev]
    json.dump({"episodes": merged}, open(mpath, "w"), indent=2)
    bad = [m["act"] for m in manifest if not m["match"]]
    print("\nMANIFEST:", os.path.join(OUT, "manifest.json"))
    print("NIEZGODNE z prowieniencją:", bad if bad else "BRAK (wszystkie match)")


if __name__ == "__main__":
    main(sys.argv[1:])
