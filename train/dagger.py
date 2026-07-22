"""dagger — DAgger x3 na ramieniu GRU (T4).

Runda = 100 rolloutow POLITYKI na T0 (sceny 44300-44399 / 44400-44499 /
44500-44599), etykieta eksperta na kazdym tiku, AGREGACJA calego zbioru
(BC train + wszystkie rundy DAgger dotad), dotrening 10 epok (te same
hiperparametry co BC: Adam lr 1e-3, grad clip 1.0, batch 16, seq pelne epizody).
Kontynuacja od wag BC (nie od zera). Czas scienny kazdej rundy (rollout + trening).

Start: ckpt/gru/bc.pt -> koniec: ckpt/gru/dagger.pt. Metryki -> results/dagger.json.
"""
import json
import os
import time

import numpy as np
import torch

from models.policy import Policy
from train.common import (EpisodeStore, collect_dagger_episode, get_device,
                          load_cfg, make_env, masked_mse)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BCDIR = os.path.join(_ROOT, "data", "bc")
DGDIR = os.path.join(_ROOT, "data", "dagger")
BC_CKPT = os.path.join(_ROOT, "ckpt", "gru", "bc.pt")
DG_CKPT = os.path.join(_ROOT, "ckpt", "gru", "dagger.pt")
OUT = os.path.join(_ROOT, "results", "dagger.json")

ROUND_SEEDS = [range(44300, 44400), range(44400, 44500), range(44500, 44600)]
LEVEL = "T0"
TRAIN_SEED = 45001
BATCH, LR, CLIP, EPOCHS = 16, 1e-3, 1.0, 10


def retrain(model, store, val_store, device, rng):
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    curve = []
    for epoch in range(EPOCHS):
        order = rng.permutation(len(store))
        tl, nb = 0.0, 0
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH].tolist()
            rgb, kin, dt, sp, mask = store.batch(idx, device)
            loss = masked_mse(model(rgb, kin, dt), sp, mask)
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            opt.step()
            tl += float(loss); nb += 1
        curve.append(round(tl / nb, 6))
    # walidacja monitoringowa
    model.eval()
    vtot, vn = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(val_store), BATCH):
            idx = list(range(i, min(i + BATCH, len(val_store))))
            rgb, kin, dt, sp, mask = val_store.batch(idx, device)
            vtot += float(masked_mse(model(rgb, kin, dt), sp, mask)) * len(idx); vn += len(idx)
    model.train()
    return curve, vtot / max(vn, 1)


def main():
    cfg = load_cfg()
    device = get_device()
    torch.manual_seed(TRAIN_SEED)
    rng = np.random.default_rng(TRAIN_SEED + 100)     # rozlaczny z shuffle BC

    with open(os.path.join(BCDIR, "split.json")) as f:
        split = json.load(f)
    store = EpisodeStore()
    for s in split["train"]:
        store.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))
    val_store = EpisodeStore()
    for s in split["val"]:
        val_store.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))

    model = Policy().to(device)
    model.load_state_dict(torch.load(BC_CKPT, map_location=device))
    print(f"device={device} | start store (BC train): {len(store)} ep")

    env = make_env(cfg)
    rounds = []
    for r, seeds in enumerate(ROUND_SEEDS, 1):
        seeds = list(seeds)
        rdir = os.path.join(DGDIR, f"round{r}")
        os.makedirs(rdir, exist_ok=True)
        # --- rollouty polityki + etykiety eksperta ---
        t_roll = time.perf_counter()
        model.eval()
        n_succ = 0
        for s in seeds:
            ep = collect_dagger_episode(env, model, s, LEVEL, cfg, device)
            n_succ += int(ep["success"])
            np.savez_compressed(os.path.join(rdir, f"ep_{s}.npz"),
                                rgb=ep["rgb"], kin=ep["kin"], dt=ep["dt"],
                                setpoint=ep["setpoint"], length=ep["length"],
                                success=ep["success"])
            store.add_npz(os.path.join(rdir, f"ep_{s}.npz"))
        model.train()
        t_roll = time.perf_counter() - t_roll
        # --- dotrening na zagregowanym zbiorze ---
        t_tr = time.perf_counter()
        curve, vl = retrain(model, store, val_store, device, rng)
        t_tr = time.perf_counter() - t_tr
        rec = {"round": r, "policy_success_rollout": f"{n_succ}/{len(seeds)}",
               "policy_success_pct": round(100 * n_succ / len(seeds), 1),
               "store_size": len(store), "train_curve": curve, "val_mse": round(vl, 6),
               "sec_rollout": round(t_roll, 1), "sec_train": round(t_tr, 1),
               "sec_round": round(t_roll + t_tr, 1)}
        rounds.append(rec)
        print(f"  runda {r}: polityka(rollout) {rec['policy_success_pct']}% | "
              f"store {len(store)} | val_mse {vl:.5f} | "
              f"rollout {t_roll:.0f}s + trening {t_tr:.0f}s = {t_roll+t_tr:.0f}s")
    env.close()

    torch.save(model.state_dict(), DG_CKPT)
    total = sum(x["sec_round"] for x in rounds)
    with open(OUT, "w") as f:
        json.dump({"stage": "dagger", "rounds": rounds,
                   "sec_dagger_total": round(total, 1),
                   "round_seeds": [[s.start, s.stop - 1] for s in ROUND_SEEDS]}, f, indent=2)
    print(f"DAgger x3 gotowe | laczny czas rund {total:.0f}s | ckpt -> {DG_CKPT}")


if __name__ == "__main__":
    main()
