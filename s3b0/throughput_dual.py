"""throughput_dual — S3b0 T4: narzut renderu 256^2 @1 Hz na tik symulacji.

Czysty pybullet (bez groundera), wzorzec s0_throughput.py. 20 s sim @48 Hz
kontroli (960 tikow), scena z scene_gen (K=5, A1). Kamera z pozy hover (port
drone_camera z scene_gen). Trzy konfiguracje:
  baza     : kamera 64^2 @12 Hz (co 4. tik),
  dual     : 64^2 @12 Hz + 256^2 @1 Hz (256^2 co 48. tik),
  dual_224 : 64^2 @12 Hz + 224^2 @0.5 Hz (awaryjna kalibracja D2).
Metryki: tiki/s, x-realtime, narzut dual/baza (mediana 2 przebiegow).

Uruchomienie: python throughput_dual.py
"""
from __future__ import annotations

import json
import os
import statistics
import time

import pybullet as p

import scene_gen as sg

OUT = "../results/s3b0"
TIMESTEP = 1.0 / 240.0
STEPS_PER_TICK = 5
CONTROL_HZ = 240.0 / STEPS_PER_TICK              # 48 Hz
SIM_SECONDS = 20.0
N_TICKS = int(SIM_SECONDS * CONTROL_HZ)          # 960
WARMUP_TICKS = int(2.0 * CONTROL_HZ)             # 96
N_RUNS = 2
SCENE_SEED = 46970
EVERY_12HZ = 4                                   # 48/4 = 12 Hz
EVERY_1HZ = 48                                   # 48/48 = 1 Hz
EVERY_HALFHZ = 96                                # 48/96 = 0.5 Hz


def run_once(cfg: dict) -> dict:
    """cfg: {'lo_res':64,'lo_every':4,'hi_res':int|None,'hi_every':int}."""
    cid = p.connect(p.DIRECT)
    try:
        plan = sg.plan_scene(SCENE_SEED, K=5, a_level="A1")
        sg.build_scene(cid, plan, floor_variant="A", tmpdir="/tmp")
        p.setTimeStep(TIMESTEP, physicsClientId=cid)
        pos, quat = sg.drone_pose(1.4)           # stala poza hover
        for _ in range(WARMUP_TICKS):
            for _ in range(STEPS_PER_TICK):
                p.stepSimulation(physicsClientId=cid)
        lo, hi = 0, 0
        t0 = time.perf_counter()
        for tick in range(N_TICKS):
            for _ in range(STEPS_PER_TICK):
                p.stepSimulation(physicsClientId=cid)
            if tick % cfg["lo_every"] == 0:
                sg.render_frame(cid, pos, quat, cfg["lo_res"], want_seg=False)
                lo += 1
            if cfg["hi_res"] and tick % cfg["hi_every"] == 0:
                sg.render_frame(cid, pos, quat, cfg["hi_res"], want_seg=False)
                hi += 1
        wall = time.perf_counter() - t0
    finally:
        p.disconnect(cid)
    return {"wall_s": wall, "ticks_per_s": N_TICKS / wall,
            "x_realtime": SIM_SECONDS / wall, "lo_frames": lo, "hi_frames": hi}


def measure(label: str, cfg: dict) -> dict:
    runs = [run_once(cfg) for _ in range(N_RUNS)]
    med = {k: statistics.median(r[k] for r in runs)
           for k in ("wall_s", "ticks_per_s", "x_realtime")}
    print(f"[{label}] lo={cfg['lo_res']}^2@{CONTROL_HZ/cfg['lo_every']:.0f}Hz"
          + (f" + hi={cfg['hi_res']}^2@{CONTROL_HZ/cfg['hi_every']:.2f}Hz" if cfg["hi_res"] else "")
          + f"  -> {med['ticks_per_s']:.1f} tik/s, {med['x_realtime']:.2f}x realtime "
            f"(lo {runs[0]['lo_frames']} hi {runs[0]['hi_frames']} klatek)")
    return {"cfg": cfg, "runs": runs, "median": med}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    print(f"throughput_dual: {N_TICKS} tikow = {SIM_SECONDS:.0f}s @ {CONTROL_HZ:.0f}Hz, "
          f"scena seed {SCENE_SEED}")
    base = measure("baza", {"lo_res": 64, "lo_every": EVERY_12HZ, "hi_res": None, "hi_every": 0})
    dual = measure("dual", {"lo_res": 64, "lo_every": EVERY_12HZ,
                            "hi_res": 256, "hi_every": EVERY_1HZ})
    dual224 = measure("dual_224_0.5Hz", {"lo_res": 64, "lo_every": EVERY_12HZ,
                                         "hi_res": 224, "hi_every": EVERY_HALFHZ})

    ovh_dual = dual["median"]["wall_s"] / base["median"]["wall_s"]
    ovh_224 = dual224["median"]["wall_s"] / base["median"]["wall_s"]
    print(f"\nnarzut dual/baza (256^2@1Hz): {ovh_dual:.3f}x")
    print(f"narzut dual_224/baza (224^2@0.5Hz): {ovh_224:.3f}x")
    print(f"x-realtime: baza {base['median']['x_realtime']:.2f}  "
          f"dual {dual['median']['x_realtime']:.2f}  dual_224 {dual224['median']['x_realtime']:.2f}")

    out = {"config": {"n_ticks": N_TICKS, "control_hz": CONTROL_HZ,
                      "sim_seconds": SIM_SECONDS, "scene_seed": SCENE_SEED,
                      "n_runs": N_RUNS, "pybullet_api": p.getAPIVersion()},
           "base": base, "dual_256_1hz": dual, "dual_224_0.5hz": dual224,
           "overhead": {"dual_over_base": ovh_dual, "dual224_over_base": ovh_224}}
    with open(os.path.join(OUT, "throughput.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"-> {OUT}/throughput.json")


if __name__ == "__main__":
    main()
