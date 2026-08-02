"""s3d/test_filters.py — testy jednostkowe filtrów 3d (CPU, bez GPU/env).

Sprawdza: parytet param A2↔A3 (≤4000, ±2%), pass-through no-lock, A0 bit-w-bit,
zgodność forward(batched) vs step(online), determinizm, oraz sanity Kalmana
(RMSE < ZOH na syntetycznym torze CV z rzadkimi dostarczeniami).
"""
from __future__ import annotations

import numpy as np
import torch

from s3d.filters import (NoFilter, KalmanCV, MicroGRU, MicroCfC, param_count,
                         IN_DIM, OUT_DIM, AGE_MAX, DT_OBS)

PARAM_CAP = 4000
PARITY_TOL = 0.02


def test_param_parity():
    a2, a3 = MicroGRU(), MicroCfC()
    p2, p3 = param_count(a2), param_count(a3)
    print(f"  A2 MicroGRU params = {p2}")
    print(f"  A3 MicroCfC params = {p3}")
    assert p2 <= PARAM_CAP, f"A2 {p2} > {PARAM_CAP}"
    assert p3 <= PARAM_CAP, f"A3 {p3} > {PARAM_CAP}"
    rel = abs(p2 - p3) / max(p2, p3)
    print(f"  parytet |A2-A3|/max = {rel:.4f} (tol {PARITY_TOL})")
    assert rel <= PARITY_TOL, f"parytet zlamany: {rel:.4f} > {PARITY_TOL}"


def test_a0_bit_exact():
    f = NoFilter()
    box = np.array([0.3, 0.4, 0.1, 0.12], np.float32)
    out = f.step(box, has_lock=True, has_delivery=True, age_n=0.1)
    assert np.array_equal(out, box), "A0 musi zwracac box bit-w-bit"


def test_passthrough_nolock():
    zeros = np.zeros(4, np.float32)
    for f in (KalmanCV(), MicroGRU(), MicroCfC()):
        f.reset()
        out = f.step(zeros, has_lock=False, has_delivery=False, age_n=1.0)
        assert np.allclose(out, zeros), f"{f.name} nie pass-through przy no-lock"


def test_output_dim():
    box = np.array([0.5, 0.5, 0.2, 0.2], np.float32)
    for f in (KalmanCV(), MicroGRU(), MicroCfC()):
        f.reset()
        out = f.step(box, True, True, 0.05)
        assert out.shape == (OUT_DIM,), f"{f.name} zly wymiar {out.shape}"


def test_forward_matches_step():
    """forward(batched, B=1) musi == sekwencyjny step() dla tego samego wejścia."""
    torch.manual_seed(0)
    T = 20
    seq = torch.rand(1, T, IN_DIM)
    seq[0, :, 4] = (seq[0, :, 4] > 0.5).float()   # has_delivery jest binarne (jak w realu)
    for Cls in (MicroGRU, MicroCfC):
        torch.manual_seed(7)
        m = Cls(); m.eval()
        with torch.no_grad():
            fwd = m(seq)[0].numpy()                     # (T,4)
        m.reset()
        onl = []
        for t in range(T):
            x = seq[0, t].numpy()
            # has_lock=True by zawsze uruchomic rdzen (omijamy pass-through)
            o = m.step(x[:4], has_lock=True, has_delivery=bool(x[4] > 0.5), age_n=float(x[5]))
            onl.append(o)
        onl = np.stack(onl)
        err = np.abs(fwd - onl).max()
        print(f"  {m.name}: max|forward-step| = {err:.2e}")
        assert err < 1e-5, f"{m.name} forward!=step ({err})"


def test_determinism():
    torch.manual_seed(3)
    m = MicroCfC(); m.eval()
    box = np.array([0.4, 0.6, 0.15, 0.15], np.float32)
    m.reset(); a = m.step(box, True, True, 0.1)
    m.reset(); b = m.step(box, True, True, 0.1)
    assert np.array_equal(a, b), "step niedeterministyczny"


def test_kalman_beats_zoh_synthetic():
    """Tor CV syntetyczny, dostarczenia co 12 tik (1 Hz) + szum pomiaru; KF < ZOH RMSE."""
    rng = np.random.default_rng(0)
    T = 120
    # prawdziwy tor: liniowy ruch cx,cy; stałe w,h
    t = np.arange(T)
    gt = np.stack([0.3 + 0.002 * t, 0.5 - 0.001 * t,
                   0.12 + 0 * t, 0.12 + 0 * t], axis=1).astype(np.float32)
    kf = KalmanCV(q=1e-3, r=1e-2)
    kf.reset()
    zoh_box = np.zeros(4, np.float32); have = False
    zoh_pred, kf_pred = [], []
    for k in range(T):
        deliver = (k % 12 == 0)
        if deliver:
            meas = gt[k] + rng.normal(0, 0.02, 4).astype(np.float32)
            zoh_box = meas; have = True
        has_lock = have
        kf_out = kf.step(zoh_box if has_lock else np.zeros(4, np.float32),
                         has_lock, deliver and has_lock, min((k % 12) * DT_OBS / AGE_MAX, 1.0))
        zoh_pred.append(zoh_box.copy() if has_lock else gt[k])
        kf_pred.append(kf_out)
    zoh_pred = np.stack(zoh_pred); kf_pred = np.stack(kf_pred)
    rmse_zoh = float(np.sqrt(((zoh_pred - gt) ** 2).mean()))
    rmse_kf = float(np.sqrt(((kf_pred - gt) ** 2).mean()))
    print(f"  RMSE ZOH={rmse_zoh:.4f}  KF={rmse_kf:.4f}")
    assert rmse_kf < rmse_zoh, f"KF ({rmse_kf}) nie bije ZOH ({rmse_zoh}) na torze CV"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    n = 0
    for t in tests:
        print(f"[{t.__name__}]")
        t()
        n += 1
    print(f"\n{n}/{len(tests)} PASS")
