"""demo_proof/mc_smoke.py — B0 recon smoke (RZUCANY, poza pulami pomiarowymi).

Testuje wykonalność misji wielonogowej: (a) mechanizm reset-per-leg + teleport carry-over,
(b) czy zamrożona polityka LECI z nogi startującej z POZYCJI POPRZEDNIEGO CELU (poza rozkładem
spawnu). Scena K8 seed 49502 (49xxx nieużywane). ZERO zapisu klatek, zero pomiaru — tylko min-dist
per noga na ekran. NIE commitowane do wyników.

CLI: .venv/bin/python -m demo_proof.mc_smoke
"""
from __future__ import annotations
import os
import sys
import numpy as np
import pybullet as p
import torch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import POLICY_STEPS  # noqa
from env.scene_attr import scene_params  # noqa
from models.policy_gc5 import PolicyGC5  # noqa
from train.common import get_device, load_cfg, make_env  # noqa
from task import split_state  # noqa
from train.s3b2r import DT, AGE_MAX, K_DEL, Tracker5, CKPT  # noqa
from s3b3.live_grounder import TICK_EVERY, GrounderClient  # noqa
from s3c1.shield import Shield, HOLD, REFUSE  # noqa

SEED = 49502
Z_HOVER = 0.5
R_GOAL = 0.25


def fly_leg(env, client, model, device, target_obj, teleport_to, max_ticks=140, home=False):
    """Jedna noga: teleport drona (carry-over) -> lot do target_obj wg komendy. Zwraca (min_dist, end_pos)."""
    cmd = f"fly to the {target_obj['color']} {target_obj['shape']}"
    hover = np.array([target_obj['pos'][0], target_obj['pos'][1], Z_HOVER])
    if teleport_to is not None:                       # carry-over z poprzedniej nogi (poza spawnem)
        did = int(env.env.DRONE_IDS[0])
        p.resetBasePositionAndOrientation(did, [teleport_to[0], teleport_to[1], teleport_to[2]],
                                          [0, 0, 0, 1], physicsClientId=env.env.CLIENT)
        p.resetBaseVelocity(did, [0, 0, 0], [0, 0, 0], physicsClientId=env.env.CLIENT)
    env.hover = hover
    h = model.init_hidden(1, device); tr = Tracker5()
    sh = Shield(arena_half=env.cfg["arena_half"], margin=0.2, near=0.5, theta_age_s=2.0,
                t_acq_s=3.0, t_hold_s=3.0, dt=DT); sh.reset(hover_xy=(hover[0], hover[1]))
    obs = env._obs(env.env._getDroneStateVector(0)); info = env._info(False)
    conf_latest = None; mind = 9.9; end = teleport_to
    for k in range(max_ticks):
        tgt = tr.vector(k)
        action, h = model.act(obs, tgt, h, device)
        st = env.env._getDroneStateVector(0); pos = np.asarray(split_state(st)["pos"], float)
        has_lock = any(ks + K_DEL <= k for (ks, _) in tr.sources)
        age = float(tgt[4]) * AGE_MAX
        dec = sh.step(k, pos, has_lock, age if has_lock else None, conf_latest,
                      float(np.linalg.norm(pos - hover)))
        applied = action
        if dec["decision"] == HOLD:
            applied = np.array([pos[0], pos[1], pos[2], 0, 0, 0], np.float32)
        elif dec["decision"] == REFUSE:
            end = pos; break
        obs, info, done = env.step(applied)
        end = pos
        d = float(np.linalg.norm(pos[:2] - hover[:2])); mind = min(mind, d)
        if k % TICK_EVERY == 0 and info.get("rgb256") is not None:
            box, conf, _ = client.query(info["rgb256"], cmd)
            if conf is not None:
                conf_latest = conf
            if box is not None:
                tr.observe(k, box)
        if done:
            break
    return mind, end, cmd


def main():
    device = get_device(); cfg = load_cfg(); env = make_env(cfg)
    model = PolicyGC5().to(device); model.load_state_dict(torch.load(CKPT, map_location=device)); model.eval()
    client = GrounderClient()
    try:
        env.reset(scene_seed=SEED, level="T0", scene_type="3b")
        K, A = scene_params(SEED)
        objs = [o for o in env.scene["objects"]]
        print(f"scena seed={SEED} K={K}/{A} obiektów={len(objs)}", flush=True)
        for o in objs:
            print(f"  id{o['id']} {o['color']} {o['shape']} pos={[round(x,2) for x in o['pos']]} des={o['designated']}", flush=True)
        # wybierz 3 rozne cele (kolor+ksztalt unikatowe wystarczajaco)
        targets = objs[:3]
        carry = None
        for i, t in enumerate(targets):
            if i > 0:                                  # noga i>0 startuje z pozycji poprzedniego celu
                env.reset(scene_seed=SEED, level="T0", scene_type="3b")   # ta sama scena (deterministyczna)
            mind, carry, cmd = fly_leg(env, client, model, device, t,
                                       teleport_to=(carry if i > 0 else None))
            spawn = "SPAWN" if i == 0 else "carry-over (out-of-spawn)"
            ok = "ARRIVED" if mind <= R_GOAL else ("NEAR" if mind <= 0.5 else "MISS")
            print(f"LEG{i+1} [{spawn}] '{cmd}' -> min_dist={mind:.3f} m  {ok}  end={[round(float(x),2) for x in carry[:2]]}", flush=True)
    finally:
        client.close(); env.close()


if __name__ == "__main__":
    main()
