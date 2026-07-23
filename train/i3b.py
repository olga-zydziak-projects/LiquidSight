"""i3b — BIEG WIAZACY F3 (I3b). Precondition par.4 (FAZA A/B) z siatka lr,
wczesnym rozstrzyganiem arytmetycznym i pelna wznawialnoscia.

REGULA STOPU (ANEKS-4): ZERO zmian instrumentu. Jedyna dzwignia: lr z siatki
par.4 {3e-4, 1e-3}, per ramie, z logiem. Seedy: 45010..45019 (sekwencyjnie).
Trening = procedura v2 (train/procedure.run_cycle: 4 etapy od zera, best-val,
120 epok). Eval = 100 scen nominal 43000-43099 per seed.

Wznawialnosc: results/i3b/progress.jsonl (append-only) — wpis po kazdym
ukonczonym (arm, lr, seed). Restart = wczytaj progress i pomin ukonczone.
Checkpointy: results/i3b/ckpt/<arm>_lr<g>_s<seed>.pt.

Wczesne rozstrzygniecie (TYLKO precondition par.4, FAZA A/B): po k seedach
nogi (arm,lr) z suma S p.p.: jesli S + (10-k)*100 < 900 -> noga FAIL (srednia
10 seedow nie moze osiagnac 90%). Arytmetyka na zamrozonym kryterium.

Uzycie:
  python -m train.i3b harvest   # zaimportuj pomiary smoke seed45010 do progress
  python -m train.i3b fazaA      # precondition ramion CfC (fallback lr) + bramka
  python -m train.i3b fazaB      # A_GRU @1e-3 (formalny precondition kontrolny)
  python -m train.i3b status     # podsumowanie progressu
"""
from __future__ import annotations

import collections
import json
import os
import sys
import time

import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.arms import build_arm, core_params  # noqa: E402
from train.common import (EpisodeStore, eval_policy_episode, get_device,  # noqa: E402
                          load_cfg, make_env)
from train.procedure import run_cycle  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BCDIR = os.path.join(_ROOT, "data", "bc")
DGDIR = os.path.join(_ROOT, "data", "i3b_dagger")
I3B = os.path.join(_ROOT, "results", "i3b")
CKDIR = os.path.join(I3B, "ckpt")
PROG = os.path.join(I3B, "progress.jsonl")
NOMINAL = list(range(43000, 43100))
SEEDS = list(range(45010, 45020))
GRID = [3e-4, 1e-3]                      # F3_GATE par.4


def _log(s=""):
    print(s, flush=True)


def _key(arm, lr, seed):
    return f"{arm}|{lr:g}|{seed}"


def load_progress():
    recs = {}
    if os.path.exists(PROG):
        with open(PROG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                recs[_key(r["arm"], r["lr"], r["seed"])] = r
    return recs


def append_progress(rec):
    os.makedirs(I3B, exist_ok=True)
    with open(PROG, "a") as f:
        f.write(json.dumps(rec) + "\n")


def _stores():
    with open(os.path.join(BCDIR, "split.json")) as f:
        split = json.load(f)
    store = EpisodeStore()
    for s in split["train"]:
        store.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))
    val = EpisodeStore()
    for s in split["val"]:
        val.add_npz(os.path.join(BCDIR, f"ep_{s}.npz"))
    return store, val


def run_seed(arm, lr, seed, faza, cfg, device):
    """Pelny cykl v2 + eval nominal + zapis checkpointu. Zwraca rekord progress."""
    store, val = _stores()
    env = make_env(cfg)
    dg = os.path.join(DGDIR, _key(arm, lr, seed))
    t0 = time.perf_counter()
    model, stages = run_cycle(arm, lr, seed, cfg, env, store, val, device, dg, log=_log)
    sec = time.perf_counter() - t0

    model.eval()
    succ = 0
    fails = collections.Counter()
    for s in NOMINAL:
        r = eval_policy_episode(env, model, s, "T0", cfg, device)
        if r["success"]:
            succ += 1
        else:
            fails[r["fail_type"]] += 1
    env.close()

    os.makedirs(CKDIR, exist_ok=True)
    ckpt = os.path.join(CKDIR, f"{_key(arm, lr, seed)}.pt")
    torch.save(model.state_dict(), ckpt)

    return {"faza": faza, "arm": arm, "lr": lr, "seed": seed,
            "nominal_pct": round(100 * succ / len(NOMINAL), 1),
            "nominal_succ": succ, "porazki": dict(fails),
            "dagger_rollout": [s["rollout_succ_pct"] for s in stages if s["round"] > 0],
            "best_val_r": [s["best_val"] for s in stages],
            "best_epoch_r": [s["best_epoch"] for s in stages],
            "sec_cykl": round(sec, 1), "ckpt": ckpt}


def run_leg(arm, lr, faza, cfg, device, prog, early=True):
    """Jedna noga (arm,lr) nad 10 seedami z wczesnym rozstrzyganiem (early=True
    tylko precondition). Zwraca werdykt nogi."""
    _log(f"\n===== NOGA {arm} @ lr={lr:g} (faza {faza}) =====")
    S = 0.0
    done = []
    for k, seed in enumerate(SEEDS, 1):
        key = _key(arm, lr, seed)
        rec = prog.get(key)
        if rec is None:
            _log(f"  -> trening {arm} lr={lr:g} seed={seed} (k={k}/10) ...")
            rec = run_seed(arm, lr, seed, faza, cfg, device)
            append_progress(rec)
            prog[key] = rec
            _log(f"  [{arm} lr={lr:g} s{seed}] nominal={rec['nominal_pct']}% "
                 f"porazki={rec['porazki']} ({rec['sec_cykl']:.0f}s)")
        else:
            _log(f"  [{arm} lr={lr:g} s{seed}] WCZYTANY nominal={rec['nominal_pct']}% "
                 f"porazki={rec.get('porazki')}")
        pct = rec["nominal_pct"]
        S += pct
        done.append((seed, pct))
        if early and (S + (10 - k) * 100 < 900):
            _log(f"  WCZESNE ROZSTRZYGNIECIE: k={k}, S={S:.0f} p.p.; "
                 f"S+(10-k)*100={S + (10 - k) * 100:.0f} < 900 -> NOGA FAIL")
            return {"arm": arm, "lr": lr, "verdict": "FAIL_EARLY", "k": k,
                    "S": round(S, 1), "mean_partial": round(S / k, 1), "seeds": done}
    mean = S / 10
    verdict = "PASS" if mean >= 90 else "FAIL_FULL"
    _log(f"  NOGA {arm} @ lr={lr:g}: srednia 10 seedow = {mean:.1f}% -> {verdict}")
    return {"arm": arm, "lr": lr, "verdict": verdict, "mean": round(mean, 1), "seeds": done}


def harvest():
    """Zaimportuj pomiary smoke seed45010 (identyczna procedura v2) do progress
    jako punkty FAZY A. ckpt=null (mierzone poza i3b; nie wymagane dla nogi FAIL)."""
    prog = load_progress()
    srcs = [("A_NCP", 0.0003, "smoke_A_NCP_proc2_lr3e-4.json"),
            ("A_CFC", 0.0003, "smoke_A_CFC_proc2_lr3e-4.json"),
            ("A_NCP", 0.001, "smoke_A_NCP.json"),
            ("A_CFC", 0.001, "smoke_A_CFC.json")]
    n = 0
    for arm, lr, fname in srcs:
        p = os.path.join(_ROOT, "results", fname)
        if not os.path.exists(p):
            _log(f"  POMIN {fname} (brak)")
            continue
        d = json.load(open(p))
        if d["arm"] != arm or abs(d["lr"] - lr) > 1e-9 or d["seed"] != 45010:
            _log(f"  POMIN {fname}: niezgodne arm/lr/seed ({d['arm']},{d['lr']},{d['seed']})")
            continue
        key = _key(arm, lr, 45010)
        if key in prog:
            _log(f"  {key} juz w progress — pomin")
            continue
        rec = {"faza": "A", "arm": arm, "lr": lr, "seed": 45010,
               "nominal_pct": d["nominal_pct"], "nominal_succ": d["nominal_sukces"],
               "porazki": d["nominal_porazki"],
               "dagger_rollout": [r["rollout_succ_pct"] for r in d["dagger"]],
               "best_val_r": [d["bc"]["best_val"]] + [r["best_val"] for r in d["dagger"]],
               "best_epoch_r": [d["bc"]["best_epoch"]] + [r["best_epoch"] for r in d["dagger"]],
               "sec_cykl": d["sec_cykl_treningu"], "ckpt": None,
               "zrodlo": f"smoke({fname})"}
        append_progress(rec)
        n += 1
        _log(f"  + {key} nominal={rec['nominal_pct']}% (z {fname})")
    _log(f"harvest: dodano {n} rekordow seed45010")


def faza_a(cfg, device):
    prog = load_progress()
    matrix = {}
    oper_lr = {}
    for arm in ["A_NCP", "A_CFC"]:
        leg = run_leg(arm, 3e-4, "A", cfg, device, prog, early=True)
        matrix[_key(arm, 3e-4, 0)] = leg
        if leg["verdict"] == "PASS":
            oper_lr[arm] = 3e-4
            continue
        leg2 = run_leg(arm, 1e-3, "A", cfg, device, prog, early=True)
        matrix[_key(arm, 1e-3, 0)] = leg2
        if leg2["verdict"] == "PASS":
            oper_lr[arm] = 1e-3
    any_pass = len(oper_lr) > 0
    out = {"faza": "A", "matrix": matrix, "oper_lr": oper_lr,
           "any_cfc_pass": any_pass,
           "bramka": "POJEDYNEK/HYBRYDA (idz do B/C)" if any_pass
                     else "GRANICA (pomin B,C; FAZA D wariant GRANICA; STOP par.4)"}
    with open(os.path.join(I3B, "fazaA_wynik.json"), "w") as f:
        json.dump(out, f, indent=2)
    _log("\n" + "=" * 60)
    _log("FAZA A — MACIERZ PRECONDITION:")
    for k, leg in matrix.items():
        _log(f"  {k}: {leg['verdict']} "
             + (f"mean={leg.get('mean')}%" if 'mean' in leg
                else f"k={leg['k']} S={leg['S']} mean_part={leg['mean_partial']}%"))
    _log(f"oper_lr={oper_lr} | any_cfc_pass={any_pass}")
    _log(f"BRAMKA: {out['bramka']}")
    return out


def faza_b(cfg, device):
    prog = load_progress()
    leg = run_leg("A_GRU", 1e-3, "B", cfg, device, prog, early=False)
    with open(os.path.join(I3B, "fazaB_wynik.json"), "w") as f:
        json.dump({"faza": "B", "leg": leg}, f, indent=2)
    _log(f"\nFAZA B A_GRU@1e-3: {leg['verdict']} mean={leg.get('mean')}%")
    return leg


def status():
    prog = load_progress()
    by = collections.defaultdict(list)
    for k, r in prog.items():
        by[(r["arm"], r["lr"])].append((r["seed"], r["nominal_pct"]))
    _log(f"progress.jsonl: {len(prog)} rekordow")
    for (arm, lr), lst in sorted(by.items()):
        lst.sort()
        s = sum(p for _, p in lst)
        _log(f"  {arm} @ lr={lr:g}: {len(lst)} seedow, suma {s:.0f} p.p. "
             f"-> {[(sd, p) for sd, p in lst]}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    os.makedirs(I3B, exist_ok=True)
    if cmd == "harvest":
        harvest()
    elif cmd == "status":
        status()
    elif cmd == "runseed":
        # runseed <arm> <lr> <seed> [faza] — pojedynczy seed (idempotentny wzgl. progress)
        arm, lr, seed = sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
        faza = sys.argv[5] if len(sys.argv) > 5 else "A"
        prog = load_progress()
        key = _key(arm, lr, seed)
        if key in prog:
            _log(f"{key} juz w progress ({prog[key]['nominal_pct']}%) — pomin")
            return
        cfg = load_cfg()
        device = get_device()
        _log(f"I3b runseed {key} | device={device}")
        rec = run_seed(arm, lr, seed, faza, cfg, device)
        append_progress(rec)
        _log(f"[{key}] nominal={rec['nominal_pct']}% porazki={rec['porazki']} "
             f"({rec['sec_cykl']:.0f}s) ckpt={rec['ckpt']}")
    else:
        cfg = load_cfg()
        device = get_device()
        _log(f"I3b {cmd} | device={device} | rdzenie: "
             + ", ".join(f"{a}={core_params(build_arm(a))}" for a in ['A_GRU', 'A_NCP', 'A_CFC']))
        if cmd == "fazaA":
            faza_a(cfg, device)
        elif cmd == "fazaB":
            faza_b(cfg, device)
        else:
            _log(f"nieznana komenda: {cmd}")
            sys.exit(2)


if __name__ == "__main__":
    main()
