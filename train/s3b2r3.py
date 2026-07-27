"""s3b2r3 — ANEKS-3B-3: F2 gating dostarczen + F3 (+1 runda DAgger). Reuzywa s3b2r.

F2: nowy box nadpisuje ZOH tylko gdy IoU(nowy, biezacy ZOH) >= 0.2 LUB age_s > 2.0
    (re-akwizycja po dlugiej utracie); odrzucone LOGOWANE (licznik).
F3: +1 runda DAgger (r4, pula 47100-47199). ROUNDS=4. F1 (EMA) NIEAKTYWNA.
Reszta (kanal 5-dim, live-fed, przepis v2, seed 45020) bez zmian.

CLI: python -m train.s3b2r3 {train|precond|g1r}
"""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
import train.s3b2r as s  # noqa: E402
from train.s3b2r import DT, K_DEL  # noqa: E402
from s3b3.live_grounder import iou  # noqa: E402


class GatedTracker(s.Tracker5):
    total_rejected = 0

    def observe(self, k, box):
        if box is None:
            return
        deliv = [(ks, bb) for (ks, bb) in self.sources if ks + K_DEL <= k]
        if deliv:
            cks, cbb = max(deliv, key=lambda x: x[0]); age = (k - cks) * DT
            if not (iou(box, cbb) >= 0.2 or age > 2.0):    # F2: odrzuc kradziez
                GatedTracker.total_rejected += 1
                return
        self.sources.append((int(k), list(box)))


# --- aktywacja dzwigni (przelaczenie globali s3b2r PRZED wywolaniem) ---
s.Tracker5 = GatedTracker                              # F2
s.ROUNDS = 4                                            # F3: +1 runda
s.DAGGER_SEEDS = s.DAGGER_SEEDS + [list(range(47100, 47200))]
s.CKDIR = os.path.join(_ROOT, "ckpt", "s3b2r3")
s.OUT = os.path.join(_ROOT, "results", "s3b2r3")
s.CKPT = os.path.join(s.CKDIR, "policy_gc5.pt")


if __name__ == "__main__":
    os.makedirs(s.OUT, exist_ok=True)
    cmd = sys.argv[1]
    {"train": s.cmd_train, "precond": s.cmd_precond, "g1r": s.cmd_g1r}[cmd]()
    if cmd == "train":
        json.dump({"F2_odrzucone_dostarczenia": GatedTracker.total_rejected},
                  open(os.path.join(s.OUT, "f2_gating.json"), "w"), indent=2)
        print(f"F2 odrzucone dostarczenia (gating): {GatedTracker.total_rejected}", flush=True)
