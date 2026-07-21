"""s0_throughput — S0: pomiar przepustowosci sim+render na TEJ maszynie.

NIE jest to bramka: brak PASS/FAIL, brak progow. Czysty pomiar, ktory ma
wykarmic decyzje o n seedow w F3_GATE (decyzja nalezy do czlowieka).

Uzywa DOKLADNIE tej samej sceny i kamery co test krytyczny: importuje
build_scene i camera z s0_render_det (ten sam katalog). Klient DIRECT,
timestep 1/240, tik kontroli = 5x stepSimulation (48 Hz).

Trzy pomiary:
  A (baseline): 20 s symulacji (960 tikow), bez renderu.
  B: 20 s z getCameraImage 64x64 co 4. tik (12 Hz), TinyRenderer, shadow=1,
     lightDirection=[0.4,0.4,1.0] — identycznie jak s0_render_det.
  C: jak B, ale 96x96.
Kazdy pomiar: warmup 2 s, potem 2 przebiegi (raportowane oba + mediana).

Uruchomienie: python s0_throughput.py [--json results/s0_throughput.json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import time

import pybullet as p

from s0_render_det import build_scene, camera

# --- parametry sciezki krytycznej (SPEC S0, nie do strojenia) ---
TIMESTEP = 1.0 / 240.0
STEPS_PER_TICK = 5                 # 5x stepSimulation na tik kontroli
CONTROL_HZ = 240.0 / STEPS_PER_TICK  # = 48 Hz
SIM_SECONDS = 20.0
N_TICKS = int(SIM_SECONDS * CONTROL_HZ)          # 960
WARMUP_SECONDS = 2.0
WARMUP_TICKS = int(WARMUP_SECONDS * CONTROL_HZ)  # 96
SCENE_SEED = 40003
CAM_EVERY = 4                      # render co 4. tik -> 12 Hz
CAM_FPS_NOMINAL = CONTROL_HZ / CAM_EVERY         # 12 Hz
LIGHT_DIR = [0.4, 0.4, 1.0]        # jak s0_render_det
N_RUNS = 2
EPISODE_SECONDS = 10.0
N_EPISODES_PROJ = 300              # przykladowy budzet demonstracji, nie decyzja


def run_once(res: int | None) -> dict:
    """Jeden przebieg: swiezy klient DIRECT, build_scene, warmup, mierzone 20 s.

    res=None -> pomiar A (bez renderu). res=int -> render co CAM_EVERY tik.
    """
    n_render_total = N_TICKS // CAM_EVERY
    cid = p.connect(p.DIRECT)
    try:
        build_scene(SCENE_SEED)                  # ustawia gravity + timestep 1/240
        # warmup (nie mierzony)
        for _ in range(WARMUP_TICKS):
            for _ in range(STEPS_PER_TICK):
                p.stepSimulation()

        cam_frames = 0
        render_idx = 0
        t0 = time.perf_counter()
        for tick in range(N_TICKS):
            for _ in range(STEPS_PER_TICK):
                p.stepSimulation()
            if res is not None and tick % CAM_EVERY == 0:
                t_frac = render_idx / max(n_render_total - 1, 1)
                view, proj = camera(t_frac, res)
                p.getCameraImage(res, res, view, proj,
                                 renderer=p.ER_TINY_RENDERER, shadow=1,
                                 lightDirection=LIGHT_DIR)
                cam_frames += 1
                render_idx += 1
        wall = time.perf_counter() - t0
    finally:
        p.disconnect(cid)

    ticks_per_s = N_TICKS / wall
    x_realtime = SIM_SECONDS / wall
    out = {"wall_s": wall, "ticks_per_s": ticks_per_s, "x_realtime": x_realtime,
           "cam_frames": cam_frames}
    out["cam_fps"] = (cam_frames / wall) if res is not None else None
    return out


def measure(label: str, res: int | None) -> dict:
    runs = [run_once(res) for _ in range(N_RUNS)]
    med = {
        "wall_s": statistics.median(r["wall_s"] for r in runs),
        "ticks_per_s": statistics.median(r["ticks_per_s"] for r in runs),
        "x_realtime": statistics.median(r["x_realtime"] for r in runs),
    }
    if res is not None:
        med["cam_fps"] = statistics.median(r["cam_fps"] for r in runs)
    print(f"[{label}] res={res if res is not None else 'brak'}  "
          f"({N_RUNS} przebiegi + mediana):")
    for i, r in enumerate(runs, 1):
        cam = f", cam {r['cam_fps']:.2f} FPS" if res is not None else ""
        print(f"    przebieg {i}: wall {r['wall_s']:.3f} s, "
              f"{r['ticks_per_s']:.1f} tik/s, {r['x_realtime']:.2f}x realtime{cam}")
    cam = f", cam {med['cam_fps']:.2f} FPS" if res is not None else ""
    print(f"    MEDIANA:    wall {med['wall_s']:.3f} s, "
          f"{med['ticks_per_s']:.1f} tik/s, {med['x_realtime']:.2f}x realtime{cam}")
    return {"res": res, "runs": runs, "median": med}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=str, default="results/s0_throughput.json")
    args = ap.parse_args()

    print(f"s0_throughput: {N_TICKS} tikow = {SIM_SECONDS:.0f} s sim @ "
          f"{CONTROL_HZ:.0f} Hz kontroli (5x step @ {1/TIMESTEP:.0f} Hz), "
          f"kamera {CAM_FPS_NOMINAL:.0f} Hz nominalnie, seed {SCENE_SEED}")
    print(f"pybullet API {p.getAPIVersion()}\n")

    A = measure("A baseline", None)
    B = measure("B render 64", 64)
    C = measure("C render 96", 96)

    # narzut renderu = spowolnienie sciany wzgledem baseline
    ovh_B = B["median"]["wall_s"] / A["median"]["wall_s"]
    ovh_C = C["median"]["wall_s"] / A["median"]["wall_s"]

    # wyprowadzenia: czas sciany 1 epizodu 10 s (z mediany x-realtime)
    ep_B = EPISODE_SECONDS / B["median"]["x_realtime"]
    ep_C = EPISODE_SECONDS / C["median"]["x_realtime"]
    proj_B = N_EPISODES_PROJ * ep_B
    proj_C = N_EPISODES_PROJ * ep_C

    print("\n--- narzut renderu (mediana wall, spowolnienie vs A) ---")
    print(f"    B/A (64x64): {ovh_B:.2f}x     C/A (96x96): {ovh_C:.2f}x")
    print("\n--- wyprowadzenia (etykieta: przykladowy budzet demonstracji, "
          "NIE decyzja) ---")
    print(f"    1 epizod 10 s:  B {ep_B:.2f} s sciany   C {ep_C:.2f} s sciany")
    print(f"    {N_EPISODES_PROJ} epizodow:  "
          f"B {proj_B:.1f} s ({proj_B/60:.1f} min)   "
          f"C {proj_C:.1f} s ({proj_C/60:.1f} min)")

    out = {
        "config": {
            "timestep": TIMESTEP, "steps_per_tick": STEPS_PER_TICK,
            "control_hz": CONTROL_HZ, "sim_seconds": SIM_SECONDS,
            "n_ticks": N_TICKS, "warmup_ticks": WARMUP_TICKS,
            "scene_seed": SCENE_SEED, "cam_every": CAM_EVERY,
            "cam_fps_nominal": CAM_FPS_NOMINAL, "light_dir": LIGHT_DIR,
            "n_runs": N_RUNS, "pybullet_api": p.getAPIVersion(),
        },
        "measurements": {"A": A, "B": B, "C": C},
        "overhead": {"B_over_A": ovh_B, "C_over_A": ovh_C},
        "derivations": {
            "label": "przykladowy budzet demonstracji, nie decyzja",
            "episode_seconds": EPISODE_SECONDS,
            "episode_wall_s": {"B": ep_B, "C": ep_C},
            "n_episodes": N_EPISODES_PROJ,
            "projection_wall_s": {"B": proj_B, "C": proj_C},
            "projection_wall_min": {"B": proj_B / 60, "C": proj_C / 60},
        },
    }
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n-> {args.json}")


if __name__ == "__main__":
    main()
