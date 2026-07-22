"""train_bc — trening BC ramienia GRU (T3).

Sekwencyjnie pelnymi epizodami (120 tikow), batch 16 epizodow, Adam lr 1e-3,
grad clip 1.0, 15 epok. Seed treningu 45001 (pula REZERWOWA 45xxx — odnotowane
w raporcie; pula dropout niewykorzystana w F3, wiec 45001 wolny). Bit-determinizm
CUDA nie wymagany (regula 4).

Krzywa straty -> results/bc_loss.json ; checkpoint -> ckpt/gru/bc.pt.
"""
import json
import os
import time

import numpy as np
import torch

from models.policy import Policy, param_report
from train.common import EpisodeStore, get_device, masked_mse

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BCDIR = os.path.join(_ROOT, "data", "bc")
CKPT = os.path.join(_ROOT, "ckpt", "gru", "bc.pt")
LOSS = os.path.join(_ROOT, "results", "bc_loss.json")

TRAIN_SEED = 45001
BATCH = 16
LR = 1e-3
CLIP = 1.0
EPOCHS = 15


def load_store(ids):
    st = EpisodeStore()
    for s in ids:
        st.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))
    return st


def val_loss(model, store, device):
    model.eval()
    tot, n = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(store), BATCH):
            idx = list(range(i, min(i + BATCH, len(store))))
            rgb, kin, dt, sp, mask = store.batch(idx, device)
            tot += float(masked_mse(model(rgb, kin, dt), sp, mask)) * len(idx)
            n += len(idx)
    model.train()
    return tot / max(n, 1)


def main():
    with open(os.path.join(BCDIR, "split.json")) as f:
        split = json.load(f)
    device = get_device()
    torch.manual_seed(TRAIN_SEED)
    rng = np.random.default_rng(TRAIN_SEED)

    train_store = load_store(split["train"])
    val_store = load_store(split["val"])
    print(f"device={device} | train {len(train_store)} ep / val {len(val_store)} ep")

    model = Policy().to(device)
    print("parametry:", param_report(model))
    opt = torch.optim.Adam(model.parameters(), lr=LR)

    curve = []
    t0 = time.perf_counter()
    for epoch in range(EPOCHS):
        order = rng.permutation(len(train_store))
        tl, nb = 0.0, 0
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH].tolist()
            rgb, kin, dt, sp, mask = train_store.batch(idx, device)
            pred = model(rgb, kin, dt)
            loss = masked_mse(pred, sp, mask)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP)
            opt.step()
            tl += float(loss); nb += 1
        vl = val_loss(model, val_store, device)
        curve.append({"epoch": epoch, "train_mse": tl / nb, "val_mse": vl})
        print(f"  epoch {epoch:2d} | train_mse {tl/nb:.5f} | val_mse {vl:.5f}")
    dt = time.perf_counter() - t0

    os.makedirs(os.path.dirname(CKPT), exist_ok=True)
    torch.save(model.state_dict(), CKPT)
    with open(LOSS, "w") as f:
        json.dump({"stage": "bc", "train_seed": TRAIN_SEED, "epochs": EPOCHS,
                   "batch": BATCH, "lr": LR, "clip": CLIP, "seconds": round(dt, 1),
                   "curve": curve, "params": param_report(model)}, f, indent=2)
    print(f"BC trening: {EPOCHS} epok | {dt:.1f}s | ckpt -> {CKPT}")


if __name__ == "__main__":
    main()
