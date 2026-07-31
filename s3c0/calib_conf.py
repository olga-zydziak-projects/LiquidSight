"""S3c0 T1+T2 — kalibracja conf dla oslony R-A (OFFLINE, read-only).

Zrodla (kazda liczba stad):
  R   : results/s3b2r/precond_R_audit_tick_audit.jsonl   (model 67%, seedy 46500-46599)
  R3  : results/s3b2r3/precond_R3_audit_tick_audit.jsonl (model 11%, seedy 46500-46599)
  SWEEP(G1): results/s3b3/tick_audit.jsonl               (seedy 46600-46649) — walidacyjnie osobno

Uwaga o R4..R7: results/s3b2r{4,5,6,7}/conf_log.jsonl maja tylko {seed,k,conf,det}
BEZ etykiety GT (designated/other) => NIE DA SIE zbudowac par (conf, poprawny/bledny).
Kalibracja conf opiera sie wylacznie na biegach z tick-auditem: R, R3 (+SWEEP walidacyjnie).

Pierwszy lock epizodu = pierwszy tik (najmniejsze k) z detekcja (matched != no_detection).
Etykieta: correct == 'designated'; wrong == 'other'/'background'.
MIERZE = RAPORTUJE.
"""
import json
import os
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "s3c0")

SOURCES = {
    "R":     "results/s3b2r/precond_R_audit_tick_audit.jsonl",
    "R3":    "results/s3b2r3/precond_R3_audit_tick_audit.jsonl",
    "SWEEP": "results/s3b3/tick_audit.jsonl",
}


def first_locks(path):
    """Per seed -> pierwszy tik z detekcja: (conf, label correct/wrong, k, matched)."""
    ticks = {}
    for l in open(os.path.join(ROOT, path)):
        r = json.loads(l)
        ticks.setdefault(r["seed"], []).append(r)
    out = {}
    n_all_nodet = 0
    for seed, tl in ticks.items():
        tl.sort(key=lambda r: r["k"])
        fl = next((r for r in tl if r["matched"] not in ("no_detection", None)), None)
        if fl is None:
            n_all_nodet += 1
            continue
        label = "correct" if fl["matched"] == "designated" else "wrong"
        out[seed] = {"conf": fl["conf"], "label": label, "k": fl["k"], "matched": fl["matched"]}
    return out, n_all_nodet


def roc_auc(scores, labels):
    """labels: 1=correct(pozytyw), 0=wrong. score=conf. Zwraca (fpr,tpr,thr,auc)."""
    scores = np.asarray(scores, float)
    labels = np.asarray(labels, int)
    P = labels.sum()
    N = len(labels) - P
    if P == 0 or N == 0:
        return None
    order = np.argsort(-scores)
    s = scores[order]
    y = labels[order]
    tps = np.cumsum(y)
    fps = np.cumsum(1 - y)
    # progi na kolejnych unikalnych wartosciach
    tpr = tps / P
    fpr = fps / N
    tpr = np.concatenate([[0], tpr])
    fpr = np.concatenate([[0], fpr])
    thr = np.concatenate([[np.inf], s])
    auc = float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2.0))
    return fpr, tpr, thr, auc


def operating_points(fl_map, thetas):
    """Dla progu theta: lock przyjmowany gdy conf>=theta.
    Zwraca % blednych lockow zlapanych (odrzuconych) i % poprawnych utraconych (odrzuconych)."""
    corr = [v["conf"] for v in fl_map.values() if v["label"] == "correct"]
    wrong = [v["conf"] for v in fl_map.values() if v["label"] == "wrong"]
    rows = []
    for th in thetas:
        wrong_caught = sum(1 for c in wrong if c < th)   # bledny odrzucony = dobrze
        corr_lost = sum(1 for c in corr if c < th)       # poprawny odrzucony = zle
        rows.append({
            "theta": round(th, 4),
            "wrong_caught": wrong_caught, "wrong_total": len(wrong),
            "wrong_caught_pct": round(100 * wrong_caught / len(wrong), 1) if wrong else None,
            "corr_lost": corr_lost, "corr_total": len(corr),
            "corr_lost_pct": round(100 * corr_lost / len(corr), 1) if corr else None,
        })
    return rows


def summarize(fl_map):
    corr = [v["conf"] for v in fl_map.values() if v["label"] == "correct"]
    wrong = [v["conf"] for v in fl_map.values() if v["label"] == "wrong"]
    def st(x):
        if not x: return None
        x = np.array(x)
        return {"n": len(x), "min": round(float(x.min()), 4), "med": round(float(np.median(x)), 4),
                "mean": round(float(x.mean()), 4), "max": round(float(x.max()), 4)}
    return {"n_correct": len(corr), "n_wrong": len(wrong),
            "conf_correct": st(corr), "conf_wrong": st(wrong)}


def main():
    result = {"note": "OFFLINE kalibracja conf. R4-R7 bez etykiet GT -> nie w zbiorze.", "runs": {}}
    per_run_fl = {}
    for tag, path in SOURCES.items():
        fl, n_nodet = first_locks(path)
        per_run_fl[tag] = fl
        seeds = sorted(fl.keys())
        summ = summarize(fl)
        auc_run = roc_auc([v["conf"] for v in fl.values()],
                          [1 if v["label"] == "correct" else 0 for v in fl.values()])
        result["runs"][tag] = {
            "source": path,
            "seed_min": min(seeds), "seed_max": max(seeds),
            "n_episodes_with_lock": len(fl),
            "n_episodes_all_no_detection": n_nodet,
            **summ,
            "auc": round(float(auc_run[3]), 4) if auc_run else None,
        }

    # Zbiorczy zbior kalibracyjny = R + R3 (biegi precondition z tick-auditem)
    calib = {}
    for tag in ("R", "R3"):
        for seed, v in per_run_fl[tag].items():
            calib[(tag, seed)] = v
    scores = [v["conf"] for v in calib.values()]
    labels = [1 if v["label"] == "correct" else 0 for v in calib.values()]
    roc = roc_auc(scores, labels)
    auc = float(roc[3])

    # Punkty pracy: percentyle conf poprawnych (chcemy utrzymac poprawne, ciac bledne)
    corr = sorted(v["conf"] for v in calib.values() if v["label"] == "correct")
    # kandydaci theta: nisko/srednio/wysoko wg rozkladu
    thetas = [np.percentile(corr, 5), np.percentile(corr, 10), np.percentile(corr, 25)]
    ops = operating_points(calib, thetas)

    result["calib_zbiorczy_R_R3"] = {
        "n_total": len(calib),
        "n_correct": sum(labels),
        "n_wrong": len(labels) - sum(labels),
        "auc": round(auc, 4),
        "auc_flat_threshold": 0.65,
        "auc_verdict": "PLASKA (<0.65) -> R-A tylko NO_MATCH/timeout" if auc < 0.65
                       else "SEPARUJE (>=0.65) -> theta_conf sensowny",
        "operating_points": ops,
        "roc_curve": {"fpr": [round(float(x), 4) for x in roc[0]],
                      "tpr": [round(float(x), 4) for x in roc[1]]},
    }
    # rozklad zrodel w zbiorze zbiorczym
    result["calib_zbiorczy_R_R3"]["zrodla"] = {
        "R":  sum(1 for (t, _) in calib if t == "R"),
        "R3": sum(1 for (t, _) in calib if t == "R3"),
    }

    os.makedirs(OUT, exist_ok=True)
    json.dump(result, open(os.path.join(OUT, "conf_calib.json"), "w"), indent=1)

    # konsola
    print("=== T1 zbior kalibracyjny (pierwszy lock / epizod) ===")
    for tag in SOURCES:
        r = result["runs"][tag]
        print(f"{tag} [{r['source']}] seedy {r['seed_min']}-{r['seed_max']}: "
              f"locki={r['n_episodes_with_lock']} (correct {r['n_correct']}/wrong {r['n_wrong']}), "
              f"all-no-det={r['n_episodes_all_no_detection']}, AUC={r['auc']}")
        print(f"    conf correct: {r['conf_correct']}")
        print(f"    conf wrong  : {r['conf_wrong']}")
    print("\n=== T2 zbiorczy R+R3 ===")
    z = result["calib_zbiorczy_R_R3"]
    print(f"n={z['n_total']} (correct {z['n_correct']}/wrong {z['n_wrong']}) zrodla={z['zrodla']}")
    print(f"AUC={z['auc']}  -> {z['auc_verdict']}")
    print("punkty pracy (przyjmij lock gdy conf>=theta):")
    for op in z["operating_points"]:
        print(f"  theta={op['theta']:.4f}: bledne zlapane {op['wrong_caught']}/{op['wrong_total']} "
              f"({op['wrong_caught_pct']}%) | poprawne utracone {op['corr_lost']}/{op['corr_total']} "
              f"({op['corr_lost_pct']}%)")
    print("\nZAPIS ->", os.path.join(OUT, "conf_calib.json"))


if __name__ == "__main__":
    main()
