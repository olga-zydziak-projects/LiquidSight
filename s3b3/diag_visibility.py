"""diag_visibility — DIAG-3B T1+T2: audyt kanału GT + obwiednia widoczności live.

T1 (audyt kanału GT): jak S3b2 liczył gt_bbox_256 gdy wskazany był POZA FOV.
  Kod: env._render_semantic -> bbox_from_mask(seg256, designated_id); poza FOV
  seg ma 0 px -> None -> tracker.observe pomija -> ZOH ostatniego widocznego locka
  (nigdy pozycja poza-FOV). Sonda potwierdza per-tick zawartość kanału GT.

T2 (obwiednia widoczności): 50 ep sweep 46600-46649 (te same sceny co G1) LOTEM
  EKSPERTA (GT), render 256^2 co tick: per komórka K×A frakcja tików z wskazanym
  w FOV (seg-mask >= 3 px), profil widoczności vs czas i vs dystans do celu.
  Zapisuje klatki tików (256^2 PNG) + GT (bbox wskazanego + wszystkich obiektów,
  in_fov, dist, t) dla T3.

Uruchomienie: python -m s3b3.diag_visibility   (główny .venv; po zakończeniu B1)
"""
from __future__ import annotations

import collections
import json
import os
import sys

import numpy as np
from PIL import Image

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from env.liquidsight_env import DT_OBS, POLICY_STEPS  # noqa: E402
from env.scene_attr import bbox_from_mask, scene_params  # noqa: E402
from env.scene_builder import drone_camera  # noqa: E402
from expert.expert import make_expert_for  # noqa: E402
from train.common import load_cfg, make_env  # noqa: E402
from task import split_state  # noqa: E402
from s3b3.live_grounder import K_DEL, TICK_EVERY  # kontrakt D3

OUT = os.path.join(_ROOT, "results", "diag3b")
FRAMES = os.path.join(OUT, "frames")
MIN_PX = 3                    # wskazany "w FOV" <=> seg-mask >= 3 px w 256
SWEEP = list(range(46600, 46650))


def _all_bboxes(seg, objects):
    return {o["id"]: bbox_from_mask(seg, o["id"]) for o in objects}


def main():
    os.makedirs(FRAMES, exist_ok=True)
    cfg = load_cfg()
    env = make_env(cfg)
    ticks = []                          # rekordy per tick (T2 + zapis dla T3)
    gt_audit = []                       # zawartość kanału GT per tick (T1)
    per_cell = collections.defaultdict(lambda: [0, 0])   # [n_tick, n_in_fov]

    for seed in SWEEP:
        K, A = scene_params(seed)
        obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
        did = info["designated_id"]; objects = info["objects"]; command = info["command"]
        expert = make_expert_for(env, obs, info, cfg)
        # GT tracker (replika S3b2): źródło = gt_bbox_256 gdy w FOV, ZOH
        sources = []                     # (k_src, bbox)
        for k in range(POLICY_STEPS):
            a = expert.setpoint(k * DT_OBS)
            obs, info, done = env.step(a)
            if k % TICK_EVERY == 0:
                st = env.env._getDroneStateVector(0)
                s = split_state(st); pos, quat = s["pos"], s["quat"]
                rgb, seg = drone_camera(env.env.CLIENT, pos, quat, 256, want_seg=True)
                dpx = int((seg == did).sum())
                in_fov = dpx >= MIN_PX
                dbox = bbox_from_mask(seg, did)
                allb = _all_bboxes(seg, objects)
                dist = float(np.linalg.norm(pos - env.hover))
                fname = f"s{seed}_k{k:03d}.png"
                Image.fromarray(rgb).save(os.path.join(FRAMES, fname))
                ticks.append({"seed": seed, "K": K, "A": A, "k": k, "t": round(k * DT_OBS, 3),
                              "frame": fname, "command": command, "designated_id": did,
                              "in_fov": in_fov, "designated_px": dpx, "dist": round(dist, 3),
                              "designated_bbox": dbox,
                              "objects": [{"id": o["id"], "designated": o["designated"],
                                           "bbox": allb[o["id"]]} for o in objects]})
                per_cell[(K, A)][0] += 1
                per_cell[(K, A)][1] += int(in_fov)
                # kanał GT: co niósł w tym momencie
                if dbox is not None and in_fov:
                    sources.append((k, dbox))
                delivered = [(ks, bb) for (ks, bb) in sources if ks + K_DEL <= k]
                if delivered:
                    ks, bb = max(delivered, key=lambda x: x[0])
                    carried = "ZOH_last_infov" if ks != k - 0 else "fresh_infov"
                    age = round((k - ks) * DT_OBS, 3)
                    gt_audit.append({"seed": seed, "k": k, "in_fov": in_fov,
                                     "channel": "lock", "lock_src_k": ks, "age_s": age,
                                     "src_was_infov": True})
                else:
                    gt_audit.append({"seed": seed, "k": k, "in_fov": in_fov,
                                     "channel": "no_lock", "age_s": None})
            if done:
                break
    env.close()

    # zapis surowych rekordów (GT dla T3) + audytu
    with open(os.path.join(OUT, "ticks.jsonl"), "w") as f:
        for r in ticks:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(OUT, "gt_channel_audit.jsonl"), "w") as f:
        for r in gt_audit:
            f.write(json.dumps(r) + "\n")

    # --- T2 podsumowanie: frakcja widoczności per komórka ---
    vis_cell = {f"K{K}_{A}": round(v[1] / v[0], 3) for (K, A), v in sorted(per_cell.items())}
    fr = [v[1] / v[0] for v in per_cell.values()]
    # profil vs dystans (biny) i vs czas (tik index)
    by_dist = collections.defaultdict(lambda: [0, 0])
    by_t = collections.defaultdict(lambda: [0, 0])
    for r in ticks:
        db = min(int(r["dist"] / 0.5) * 0.5, 3.0)      # biny co 0.5 m
        by_dist[db][0] += 1; by_dist[db][1] += int(r["in_fov"])
        by_t[r["k"]][0] += 1; by_t[r["k"]][1] += int(r["in_fov"])
    vis_dist = {f"{d:.1f}m": round(v[1] / v[0], 3) for d, v in sorted(by_dist.items())}
    vis_time = {f"t{round(k*DT_OBS,2)}s": round(v[1] / v[0], 3) for k, v in sorted(by_t.items())}

    # --- T1 audyt: kanał GT poza FOV ---
    out_fov = [a for a in gt_audit if not a["in_fov"]]
    out_fov_lock = [a for a in out_fov if a["channel"] == "lock"]
    n_infov_total = sum(1 for a in gt_audit if a["in_fov"])
    verdict_gt = ("FIZYCZNY (poza FOV kanał niesie ZOH ostatniego widocznego locka "
                  "lub no-lock; NIGDY pozycji poza-FOV)")

    summary = {
        "n_ticks": len(ticks), "n_frames_saved": len(ticks),
        "T2_widocznosc_per_cell": vis_cell,
        "T2_widocznosc_min": round(min(fr), 3), "T2_widocznosc_max": round(max(fr), 3),
        "T2_widocznosc_srednia": round(float(np.mean(fr)), 3),
        "T2_profil_vs_dystans": vis_dist, "T2_profil_vs_czas": vis_time,
        "T1_frac_tickow_wskazany_w_FOV": round(n_infov_total / len(gt_audit), 3),
        "T1_tickow_poza_FOV": len(out_fov),
        "T1_poza_FOV_z_lockiem_ZOH": len(out_fov_lock),
        "T1_poza_FOV_no_lock": len(out_fov) - len(out_fov_lock),
        "T1_werdykt_kanal_GT": verdict_gt,
    }
    json.dump(summary, open(os.path.join(OUT, "visibility.json"), "w"), indent=2)
    print(f"T1/T2: {len(ticks)} tików/klatek | widocznosc srednia "
          f"{summary['T2_widocznosc_srednia']} (min {summary['T2_widocznosc_min']} "
          f"max {summary['T2_widocznosc_max']})")
    print(f"  per-cell: {vis_cell}")
    print(f"  vs dystans: {vis_dist}")
    print(f"  T1 frac in-FOV: {summary['T1_frac_tickow_wskazany_w_FOV']} | "
          f"poza-FOV: {len(out_fov)} (ZOH-lock {len(out_fov_lock)}, no-lock "
          f"{len(out_fov)-len(out_fov_lock)}) -> kanal GT: {verdict_gt}")


if __name__ == "__main__":
    main()
