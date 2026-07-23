"""procedure — ujednolicona procedura treningu C1 (ANEKS-4). JEDEN kod dla
wszystkich ramion (A_GRU / A_NCP / A_CFC). Realizuje Z1-Z3:

  Z1 rundy DAgger = retrening OD ZERA na pelnym agregacie kazda runde
     [frozen c1_train.py:181-196 (petla rnd0..3 ta sama funkcja, agregacja
      dataset=dataset+new); c1_train.py:127-131 (swiezy model + swiezy Adam)];
  Z2 selekcja = best-val na kazdym etapie; split val = data/bc/split.json['val']
     (staly, ekspertowy, ten sam dla wszystkich ramion/seedow)
     [frozen c1_train.py:135,151-156 (deepcopy best_state gdy vl<best; load na
      koncu); analog frozen walidacji-eksperta c1_train.py:85-95 / c1_common.py:67];
  Z3 epoki = 120 per etap (BC=runda0 i rundy 1..3) [frozen c1_train.py:37,39].

Lr per ramie (F3_GATE par.4) BEZ ZMIAN — przekazywane z zewnatrz. Batch 16 ep,
grad clip 1.0 [frozen c1_train.py:40,149]. Konstrukcja rdzeni (ANEKS-3) i
normalizacja wejsc: BEZ ZMIAN (aneks dotyka wylacznie procedury).
"""
from __future__ import annotations

import copy
import os
import time

import numpy as np
import torch

from train.common import (EpisodeStore, collect_dagger_episode,  # noqa: F401
                          masked_mse)
from models.arms import build_arm  # noqa: E402

BATCH = 16                 # frozen c1_train.py:40 (BATCH_EP)
CLIP = 1.0                 # frozen c1_train.py:149
EPOCHS = 120               # frozen c1_train.py:37 (BC=runda0 i kazda runda)
ROUNDS = 3                 # frozen c1_train.py:39
ROUND_SEEDS = [range(44300, 44400), range(44400, 44500), range(44500, 44600)]


def _val_mse(model, val_store, device):
    model.eval()
    tot, n = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(val_store), BATCH):
            idx = list(range(i, min(i + BATCH, len(val_store))))
            rgb, kin, dt, sp, mask = val_store.batch(idx, device)
            tot += float(masked_mse(model(rgb, kin, dt), sp, mask)) * len(idx)
            n += len(idx)
    model.train()
    return tot / max(n, 1)


def train_from_scratch(arm, lr, seed, store, val_store, device):
    """Z1+Z2+Z3: swiezy model + swiezy Adam, EPOCHS epok, wybor best-val.
    Init deterministyczny (seed) co wywolanie [frozen c1_train.py:128];
    kolejnosc shuffle deterministyczna z seeda. Zwraca (model, metryki)."""
    torch.manual_seed(seed)
    model = build_arm(arm).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    rng = np.random.default_rng(seed)
    tcurve, vcurve = [], []
    best, best_state, best_ep = float("inf"), None, -1
    for ep in range(EPOCHS):
        model.train()
        order = rng.permutation(len(store))
        tl, nb = 0.0, 0
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH].tolist()
            rgb, kin, dt, sp, mask = store.batch(idx, device)
            loss = masked_mse(model(rgb, kin, dt), sp, mask)
            if torch.isnan(loss):
                raise RuntimeError("NaN w stracie -> STOP (patologia)")
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            opt.step()
            tl += loss.item()
            nb += 1
        vl = _val_mse(model, val_store, device)
        tcurve.append(round(tl / nb, 6))
        vcurve.append(round(vl, 6))
        if vl < best:
            best, best_state, best_ep = vl, copy.deepcopy(model.state_dict()), ep
    model.load_state_dict(best_state)
    return model, {"train_curve": tcurve, "val_curve": vcurve,
                   "best_val": round(best, 6), "best_epoch": best_ep}


def run_cycle(arm, lr, seed, cfg, env, store, val_store, device, dg_dir, log=print):
    """Pelny cykl C1 (ANEKS-4): 4 etapy OD ZERA (BC=runda0 + DAgger 1..3),
    agregacja miedzy etapami. Rollout rundy r steruje model z etapu r-1
    [frozen collect_round(model=poprzedni)]. Zwraca (model, stages)."""
    stages = []
    model = None
    for rnd in range(ROUNDS + 1):
        n_succ, t_roll = None, 0.0
        if rnd > 0:
            seeds = list(ROUND_SEEDS[rnd - 1])
            rdir = os.path.join(dg_dir, arm, f"round{rnd}")
            os.makedirs(rdir, exist_ok=True)
            t0 = time.perf_counter()
            model.eval()
            n_succ = 0
            for s in seeds:
                ep = collect_dagger_episode(env, model, s, "T0", cfg, device)
                n_succ += int(ep["success"])
                np.savez_compressed(os.path.join(rdir, f"ep_{s}.npz"),
                                    rgb=ep["rgb"], kin=ep["kin"], dt=ep["dt"],
                                    setpoint=ep["setpoint"], length=ep["length"],
                                    success=ep["success"])
                store.add_npz(os.path.join(rdir, f"ep_{s}.npz"))
            t_roll = time.perf_counter() - t0
        t1 = time.perf_counter()
        model, m = train_from_scratch(arm, lr, seed, store, val_store, device)
        t_tr = time.perf_counter() - t1
        pct = round(100 * n_succ / len(ROUND_SEEDS[rnd - 1]), 1) if rnd > 0 else None
        rec = {"round": rnd, "n_episodes": len(store), "rollout_succ": n_succ,
               "rollout_succ_pct": pct, "best_val": m["best_val"],
               "best_epoch": m["best_epoch"],
               "train_mse_start_end": [m["train_curve"][0], m["train_curve"][-1]],
               "sec_rollout": round(t_roll, 1), "sec_train": round(t_tr, 1)}
        stages.append(rec)
        log(f"  [{arm} r{rnd}] store={len(store)} best_val={m['best_val']:.5f}"
            f"@{m['best_epoch']} rollout={pct} ({t_roll:.0f}+{t_tr:.0f}s)")
        model.train()
    return model, stages
