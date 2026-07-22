"""psanity — wykonanie bramki P-SANITY (P1/P2/P3) wg zamrozonego P_SANITY.md.

Werdykty WYLACZNIE wg progow z P_SANITY.md:
  P1 (zdolnosc):   ramie GRU >=90% sukcesu / 100 ep, sceny 43000-43099, T0.
  P2 (rozdzielczosc os): ta sama polityka, 50 ep/poziom, sceny 43100-43149
     identyczne na T0-T3 -> >=2 poziomy w pasmie [30%,85%].
     >85% wszedzie -> wzmocnienie T3 (K:4->8, jitter <=0.05) i powtorka P2.
     Skok >85% -> <30% miedzy sasiednimi -> poziom posredni i powtorka P2.
  P3 (sufit):      ekspert privileged, te same sceny 43100-43149, 50/poziom,
     T0-T3 -> >=95% na KAZDYM poziomie. FAIL -> STOP + diagnoza sceny.

Uzycie: python -m eval.psanity {p1|p2|p3} [--ckpt PATH]
Wyniki -> results/psanity_{p1,p2,p3}.json
"""
import argparse
import collections
import json
import os

import torch

from models.policy import Policy
from train.common import (eval_policy_episode, get_device, load_cfg, make_env)
from expert.expert import run_expert_episode

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DG_CKPT = os.path.join(_ROOT, "ckpt", "gru", "dagger.pt")
RESDIR = os.path.join(_ROOT, "results")

P1_SEEDS = list(range(43000, 43100))          # 100, T0
P2_SEEDS = list(range(43100, 43150))          # 50, identyczne na T0-T3
LEVELS = ["T0", "T1", "T2", "T3"]
BAND = (30.0, 85.0)


def load_policy(ckpt, device):
    model = Policy().to(device)
    model.load_state_dict(torch.load(ckpt, map_location=device))
    model.eval()
    return model


def eval_policy_set(model, env, seeds, level, cfg, device):
    succ = 0
    fails = collections.Counter()
    cat = 0
    for s in seeds:
        r = eval_policy_episode(env, model, s, level, cfg, device)
        if r["success"]:
            succ += 1
        else:
            fails[r["fail_type"]] += 1
            cat += int(r["catastrophe"])
    n = len(seeds)
    return {"n": n, "sukces": succ, "sukces_pct": round(100 * succ / n, 1),
            "katastrofy": cat, "porazki_typy": dict(fails)}


def run_p1(args):
    device = get_device()
    cfg = load_cfg()
    model = load_policy(args.ckpt, device)
    env = make_env(cfg)
    res = eval_policy_set(model, env, P1_SEEDS, "T0", cfg, device)
    env.close()
    res["prog"] = ">=90%"
    res["werdykt"] = "PASS" if res["sukces_pct"] >= 90.0 else "FAIL"
    res["seeds"] = [P1_SEEDS[0], P1_SEEDS[-1]]
    with open(os.path.join(RESDIR, "psanity_p1.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(f"P1 (GRU, T0, 100 ep): {res['sukces_pct']}% -> {res['werdykt']} "
          f"(prog >=90%) | katastrofy={res['katastrofy']} typy={res['porazki_typy']}")


def _band_verdict(per_level):
    pct = {l: per_level[l]["sukces_pct"] for l in LEVELS}
    in_band = [l for l in LEVELS if BAND[0] <= pct[l] <= BAND[1]]
    all_above = all(pct[l] > BAND[1] for l in LEVELS)
    cliff = any(pct[LEVELS[i]] > BAND[1] and pct[LEVELS[i + 1]] < BAND[0]
                for i in range(len(LEVELS) - 1))
    if all_above:
        verdict = "WSZYSTKO>85 -> procedura wzmocnienia T3 (K4->8, jitter<=0.05) i powtorka P2"
    elif cliff:
        verdict = "KLIF (>85 -> <30 sasiednie) -> dodac poziom posredni i powtorka P2"
    elif len(in_band) >= 2:
        verdict = "PASS"
    else:
        verdict = "FAIL (mniej niz 2 poziomy w pasmie [30,85])"
    return pct, in_band, verdict


def run_p2(args):
    device = get_device()
    cfg = load_cfg()
    model = load_policy(args.ckpt, device)
    env = make_env(cfg)
    per_level = {}
    for l in LEVELS:
        per_level[l] = eval_policy_set(model, env, P2_SEEDS, l, cfg, device)
        print(f"  P2 {l}: {per_level[l]['sukces_pct']}% "
              f"(katastrofy={per_level[l]['katastrofy']})")
    env.close()
    pct, in_band, verdict = _band_verdict(per_level)
    out = {"per_level": per_level, "sukces_pct": pct, "pasmo": list(BAND),
           "poziomy_w_pasmie": in_band, "werdykt": verdict,
           "seeds": [P2_SEEDS[0], P2_SEEDS[-1]]}
    with open(os.path.join(RESDIR, "psanity_p2.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"P2 pasmo[30,85]: w pasmie={in_band} -> {verdict}")


def run_p3(args):
    cfg = load_cfg()
    env = make_env(cfg)
    per_level = {}
    for l in LEVELS:
        succ = 0
        fails = collections.Counter()
        cat = 0
        for s in P2_SEEDS:
            r = run_expert_episode(env, s, l, cfg)
            if r["success"]:
                succ += 1
            else:
                fails[r["fail_type"]] += 1
                cat += int(r["catastrophe"])
        n = len(P2_SEEDS)
        per_level[l] = {"n": n, "sukces": succ, "sukces_pct": round(100 * succ / n, 1),
                        "katastrofy": cat, "porazki_typy": dict(fails)}
        print(f"  P3 {l} (ekspert): {per_level[l]['sukces_pct']}%")
    env.close()
    allpass = all(per_level[l]["sukces_pct"] >= 95.0 for l in LEVELS)
    out = {"per_level": per_level, "prog": ">=95% na kazdym poziomie",
           "werdykt": "PASS" if allpass else "FAIL -> STOP, diagnoza sceny",
           "seeds": [P2_SEEDS[0], P2_SEEDS[-1]]}
    with open(os.path.join(RESDIR, "psanity_p3.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"P3 (ekspert, >=95%/poziom): {'PASS' if allpass else 'FAIL -> STOP'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["p1", "p2", "p3"])
    ap.add_argument("--ckpt", default=DG_CKPT)
    args = ap.parse_args()
    {"p1": run_p1, "p2": run_p2, "p3": run_p3}[args.phase](args)


if __name__ == "__main__":
    main()
