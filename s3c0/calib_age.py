"""S3c0 T3+T4 — theta_age (R-B) + sucha symulacja replay oslony (OFFLINE, read-only).

Zrodla:
  age + wynik/epizod (wszystkie poziomy G2, w tym baza p0.00 = frozen S3b2-R):
     results/s3b4/measure.json  ['results'][level]['episodes'][*]
       .age_at_dwell_entry (znormalizowane age/AGE_MAX=8.0; None gdy nie wszedl w dwell)
       .success, .fail_type, .seed, .K, .A
  wynik bazy 67% / 100 epizodow (R-A replay): results/s3b2r/diag_lite_episodes.json
  pierwszy lock + conf + etykieta bazy (R-A replay): results/s3b2r/precond_R_audit_tick_audit.jsonl

R-B = brama wieku przy wejsciu w dwell: odrzuc gdy age_at_dwell_entry > theta_age.
R-A = brama conf na pierwszym locku: odrzuc gdy conf < theta_conf.
T4 to ESTYMATA na logach (nie pomiar; pomiar wlasciwy = S3c1). MIERZE = RAPORTUJE.
"""
import json
import os
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "s3c0")
AGE_MAX = 8.0
BINS = [0, 0.1, 0.25, 0.5, 0.75, 1.01]
LEVELS = ["p0.00", "p0.25", "p0.50", "p0.75", "L2", "L5"]


def load_levels():
    d = json.load(open(os.path.join(ROOT, "results", "s3b4", "measure.json")))
    return d["results"]


def hist(vals):
    h = [0] * (len(BINS) - 1)
    for v in vals:
        for i in range(len(BINS) - 1):
            if BINS[i] <= v < BINS[i + 1]:
                h[i] += 1
                break
    return h


# ---------------- T3: age separacja sukces vs porazka ----------------
def t3(res):
    out = {"note": "age_at_dwell_entry znormalizowane (age_s/8.0). Tylko epizody ktore weszly w dwell.",
           "bins_norm": BINS, "bins_sekundy": [round(b * AGE_MAX, 2) for b in BINS], "per_level": {}}
    pooled_succ, pooled_fail = [], []
    base_succ, base_fail = [], []
    for lv in LEVELS:
        eps = res[lv]["episodes"]
        succ = [e["age_at_dwell_entry"] for e in eps if e.get("age_at_dwell_entry") is not None and e["success"]]
        fail = [e["age_at_dwell_entry"] for e in eps if e.get("age_at_dwell_entry") is not None and not e["success"]]
        out["per_level"][lv] = {
            "n_dwell": len(succ) + len(fail),
            "succ_n": len(succ), "fail_n": len(fail),
            "succ_hist": hist(succ), "fail_hist": hist(fail),
            "succ_med": round(float(np.median(succ)), 4) if succ else None,
            "fail_med": round(float(np.median(fail)), 4) if fail else None,
            "succ_max": round(float(max(succ)), 4) if succ else None,
            "fail_min": round(float(min(fail)), 4) if fail else None,
        }
        pooled_succ += succ
        pooled_fail += fail
        if lv == "p0.00":
            base_succ, base_fail = succ, fail

    out["pooled_all_levels"] = {
        "succ_n": len(pooled_succ), "fail_n": len(pooled_fail),
        "succ_hist": hist(pooled_succ), "fail_hist": hist(pooled_fail),
        "succ_med": round(float(np.median(pooled_succ)), 4),
        "fail_med": round(float(np.median(pooled_fail)), 4) if pooled_fail else None,
        "succ_p95": round(float(np.percentile(pooled_succ, 95)), 4),
        "fail_min": round(float(min(pooled_fail)), 4) if pooled_fail else None,
    }
    out["base_p0"] = {
        "succ_n": len(base_succ), "fail_n": len(base_fail),
        "succ_hist": hist(base_succ), "fail_hist": hist(base_fail),
        "succ_med": round(float(np.median(base_succ)), 4) if base_succ else None,
        "succ_max": round(float(max(base_succ)), 4) if base_succ else None,
    }

    # kandydaci theta_age: percentyl 95 sukcesow (utrzymaj prawie wszystkie sukcesy)
    # + punkt separacji miedzy ogonem sukcesow a masa porazek
    cand = {
        "theta_p95_succ": round(float(np.percentile(pooled_succ, 95)), 4),
        "theta_p90_succ": round(float(np.percentile(pooled_succ, 90)), 4),
    }
    thetas = sorted(set(cand.values()))
    props = []
    for th in thetas:
        succ_lost = sum(1 for v in pooled_succ if v > th)
        fail_caught = sum(1 for v in pooled_fail if v > th)
        # ile epizodow bazy (p0) dotknietych regula (age>th) przy wejsciu w dwell
        base_touch = sum(1 for v in (base_succ + base_fail) if v > th)
        props.append({
            "theta_age_norm": round(th, 4), "theta_age_s": round(th * AGE_MAX, 2),
            "succ_lost": succ_lost, "succ_lost_pct_pooled": round(100 * succ_lost / len(pooled_succ), 1),
            "fail_caught": fail_caught,
            "fail_caught_pct_pooled": round(100 * fail_caught / len(pooled_fail), 1) if pooled_fail else None,
            "base_p0_episodes_touched": base_touch,
            "base_p0_dwell_n": len(base_succ) + len(base_fail),
        })
    out["theta_candidates"] = cand
    out["proposals"] = props
    return out


# ---------------- T4: sucha symulacja replay ----------------
def load_base_ra():
    """Pierwszy lock + conf + etykieta + wynik/epizod bazy S3b2-R (100 seedow)."""
    # pierwszy lock z tick_audit
    ticks = {}
    for l in open(os.path.join(ROOT, "results/s3b2r/precond_R_audit_tick_audit.jsonl")):
        r = json.loads(l)
        ticks.setdefault(r["seed"], []).append(r)
    fl = {}
    for seed, tl in ticks.items():
        tl.sort(key=lambda r: r["k"])
        f = next((r for r in tl if r["matched"] not in ("no_detection", None)), None)
        fl[seed] = {"conf": f["conf"] if f else None,
                    "label": (None if f is None else ("correct" if f["matched"] == "designated" else "wrong"))}
    # wynik/epizod
    outcome = {e["seed"]: e for e in json.load(open(os.path.join(ROOT, "results/s3b2r/diag_lite_episodes.json")))}
    return fl, outcome


def t4_ra(thetas):
    fl, outcome = load_base_ra()
    seeds = sorted(outcome.keys())
    rows = []
    for th in thetas:
        m = {"success_unchanged": 0, "success_to_refuse": 0,
             "wrong_to_refuse": 0, "wrong_unchanged": 0,
             "otherfail_to_refuse": 0, "otherfail_unchanged": 0,
             "no_lock_episode": 0}
        for s in seeds:
            o = outcome[s]
            f = fl.get(s, {"conf": None, "label": None})
            succ = o["success"]
            bucket = o.get("bucket")
            if f["label"] is None:  # brak jakiegokolwiek locka w epizodzie
                m["no_lock_episode"] += 1
                continue
            refuse = (f["conf"] is not None and f["conf"] < th)
            is_wrong = (f["label"] == "wrong") or (bucket == "B3")
            if succ:
                m["success_to_refuse" if refuse else "success_unchanged"] += 1
            elif is_wrong:
                m["wrong_to_refuse" if refuse else "wrong_unchanged"] += 1
            else:
                m["otherfail_to_refuse" if refuse else "otherfail_unchanged"] += 1
        rows.append({"theta_conf": round(float(th), 4), "n_episodes": len(seeds), **m})
    return {"note": "ESTYMATA na logach bazy S3b2-R (100 epizodow, 46500-46599). NIE pomiar.",
            "source_conf": "results/s3b2r/precond_R_audit_tick_audit.jsonl",
            "source_outcome": "results/s3b2r/diag_lite_episodes.json",
            "matrix": rows}


def t4_rb(res, thetas):
    eps = res["p0.00"]["episodes"]
    dwell = [e for e in eps if e.get("age_at_dwell_entry") is not None]
    rows = []
    for th in thetas:
        m = {"success_unchanged": 0, "success_to_refuse": 0,
             "fail_unchanged": 0, "fail_to_refuse": 0,
             "no_dwell_entry": len(eps) - len(dwell)}
        for e in dwell:
            refuse = e["age_at_dwell_entry"] > th
            if e["success"]:
                m["success_to_refuse" if refuse else "success_unchanged"] += 1
            else:
                m["fail_to_refuse" if refuse else "fail_unchanged"] += 1
        rows.append({"theta_age_norm": round(float(th), 4), "theta_age_s": round(float(th) * AGE_MAX, 2),
                     "n_episodes": len(eps), **m})
    return {"note": "ESTYMATA na logach bazy p0.00 (50 epizodow 46500-46549, frozen S3b2-R; offset +13pp vs pop 67%). NIE pomiar.",
            "source": "results/s3b4/measure.json [p0.00]",
            "matrix": rows}


def main():
    res = load_levels()
    conf = json.load(open(os.path.join(OUT, "conf_calib.json")))
    thetas_conf = [op["theta"] for op in conf["calib_zbiorczy_R_R3"]["operating_points"]]

    t3res = t3(res)
    thetas_age = [p["theta_age_norm"] for p in t3res["proposals"]]

    out = {"T3_age": t3res,
           "T4_replay": {"R_A": t4_ra(thetas_conf), "R_B": t4_rb(res, thetas_age)}}
    json.dump(out, open(os.path.join(OUT, "age_replay.json"), "w"), indent=1)

    # konsola
    print("=== T3 age-at-dwell-entry (sukces vs porazka) ===")
    p = t3res["pooled_all_levels"]
    print(f"pooled: sukces n={p['succ_n']} med={p['succ_med']} p95={p['succ_p95']} | "
          f"porazka n={p['fail_n']} med={p['fail_med']} min={p['fail_min']}")
    print(f"  succ_hist {p['succ_hist']}  fail_hist {p['fail_hist']}  (biny s={t3res['bins_sekundy']})")
    b = t3res["base_p0"]
    print(f"baza p0: sukces n={b['succ_n']} med={b['succ_med']} max={b['succ_max']} | porazka n={b['fail_n']}")
    print("propozycje theta_age:")
    for pr in t3res["proposals"]:
        print(f"  theta={pr['theta_age_norm']} ({pr['theta_age_s']}s): sukces utracony {pr['succ_lost']} "
              f"({pr['succ_lost_pct_pooled']}%) | porazka zlapana {pr['fail_caught']} "
              f"({pr['fail_caught_pct_pooled']}%) | baza dotknieta {pr['base_p0_episodes_touched']}/{pr['base_p0_dwell_n']}")

    print("\n=== T4 R-A replay (baza 100 ep) ESTYMATA ===")
    for r in out["T4_replay"]["R_A"]["matrix"]:
        print(f"  theta_conf={r['theta_conf']}: wrong->odmowa {r['wrong_to_refuse']} (wrong pozostalo {r['wrong_unchanged']}) "
              f"| sukces->odmowa {r['success_to_refuse']} (sukces {r['success_unchanged']}) "
              f"| inne-fail->odmowa {r['otherfail_to_refuse']} | brak-locka {r['no_lock_episode']}")
    print("\n=== T4 R-B replay (baza p0 50 ep) ESTYMATA ===")
    for r in out["T4_replay"]["R_B"]["matrix"]:
        print(f"  theta_age={r['theta_age_norm']} ({r['theta_age_s']}s): fail->odmowa {r['fail_to_refuse']} "
              f"(fail {r['fail_unchanged']}) | sukces->odmowa {r['success_to_refuse']} (sukces {r['success_unchanged']}) "
              f"| nie-wszedl-w-dwell {r['no_dwell_entry']}")
    print("\nZAPIS ->", os.path.join(OUT, "age_replay.json"))


if __name__ == "__main__":
    main()
