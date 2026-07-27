"""s3b2r4 — ANEKS-3B-4: F2 OFF + czysty test F3. Reuzywa s3b2r (S3b2-R = 67%).

JEDNA zmiana vs R3: F2 wylaczone (plain Tracker5 z s3b2r — ZERO gatingu/odrzucen).
F3 zostaje: ROUNDS=4, pula r4 47100-47199. Reszta identyczna z S3b2-R.
Assert: F2 off => tracker nie ma mechanizmu odrzucen (0 odrzuconych z konstrukcji).

CLI: python -m train.s3b2r4 {train|precond|g1r}
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
import train.s3b2r as s  # noqa: E402

# F2 OFF: NIE podmieniamy s.Tracker5 (plain, bez gatingu). F3: +1 runda.
assert not hasattr(s.Tracker5, "total_rejected"), "F2 musi byc OFF (plain Tracker5)"
s.ROUNDS = 4
s.DAGGER_SEEDS = s.DAGGER_SEEDS + [list(range(47100, 47200))]
s.CKDIR = os.path.join(_ROOT, "ckpt", "s3b2r4")
s.OUT = os.path.join(_ROOT, "results", "s3b2r4")
s.CKPT = os.path.join(s.CKDIR, "policy_gc5.pt")


if __name__ == "__main__":
    os.makedirs(s.OUT, exist_ok=True)
    {"train": s.cmd_train, "precond": s.cmd_precond, "g1r": s.cmd_g1r}[sys.argv[1]]()
