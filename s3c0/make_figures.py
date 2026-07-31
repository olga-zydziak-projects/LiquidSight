"""Figury S3c0 (odczyt results/s3c0/, zapis results/s3c0/fig_*.png). Zero pomiarow."""
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "s3c0")
AGE_MAX = 8.0


def _first_locks(path):
    ticks = {}
    for l in open(os.path.join(ROOT, path)):
        r = json.loads(l); ticks.setdefault(r["seed"], []).append(r)
    corr, wrong = [], []
    for tl in ticks.values():
        tl.sort(key=lambda r: r["k"])
        f = next((r for r in tl if r["matched"] not in ("no_detection", None)), None)
        if f is None: continue
        (corr if f["matched"] == "designated" else wrong).append(f["conf"])
    return corr, wrong


def _roc(corr, wrong):
    s = np.array(corr + wrong, float); y = np.array([1]*len(corr) + [0]*len(wrong))
    o = np.argsort(-s); y = y[o]
    tpr = np.concatenate([[0], np.cumsum(y)/y.sum()])
    fpr = np.concatenate([[0], np.cumsum(1-y)/(len(y)-y.sum())])
    auc = float(np.sum(np.diff(fpr)*(tpr[1:]+tpr[:-1])/2))
    return fpr, tpr, auc


def fig_roc():
    srcs = [("R (67%)", "results/s3b2r/precond_R_audit_tick_audit.jsonl", "#1f77b4"),
            ("R3 (11%)", "results/s3b2r3/precond_R3_audit_tick_audit.jsonl", "#ff7f0e"),
            ("SWEEP G1", "results/s3b3/tick_audit.jsonl", "#2ca02c")]
    fig, ax = plt.subplots(figsize=(6.2, 6))
    allc, allw = [], []
    for name, path, c in srcs:
        corr, wrong = _first_locks(path)
        fpr, tpr, auc = _roc(corr, wrong)
        ax.plot(fpr, tpr, "-", color=c, lw=1.8, label=f"{name}  AUC={auc:.3f}")
        if name.startswith("R "): allc += corr; allw += wrong
        if name.startswith("R3"): allc += corr; allw += wrong
    fpr, tpr, auc = _roc(allc, allw)
    ax.plot(fpr, tpr, "-", color="#d62728", lw=2.6, label=f"R+R3 zbiorczo  AUC={auc:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=1, label="losowy (AUC=0.5)")
    ax.axhspan(0, 0, color="none")
    ax.set_xlabel("FPR (poprawne locki odrzucone)"); ax.set_ylabel("TPR (poprawne locki zachowane)")
    ax.set_title("R-A: separacja conf pierwszego locka (poprawny vs bledny)\nprog akceptacji 0.65 — zbiorczo AUC=0.650 GRANICZNA")
    ax.legend(loc="lower right", fontsize=8); ax.grid(alpha=0.3)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_roc_conf.png"), dpi=130); plt.close(fig)


def fig_conf_dist():
    corrR, wrongR = _first_locks("results/s3b2r/precond_R_audit_tick_audit.jsonl")
    corr3, wrong3 = _first_locks("results/s3b2r3/precond_R3_audit_tick_audit.jsonl")
    corr = corrR + corr3; wrong = wrongR + wrong3
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bins = np.linspace(0, 0.3, 31)
    ax.hist(np.clip(corr, 0, 0.3), bins=bins, alpha=0.6, color="#2ca02c", label=f"poprawny lock (n={len(corr)})")
    ax.hist(np.clip(wrong, 0, 0.3), bins=bins, alpha=0.7, color="#d62728", label=f"bledny lock (n={len(wrong)})")
    for th, lab in [(0.0023, "θ p5"), (0.0145, "θ p25")]:
        ax.axvline(th, color="k", ls=":", lw=1)
        ax.annotate(lab, (th, ax.get_ylim()[1]*0.9), fontsize=7, rotation=90, va="top")
    ax.set_xlabel("conf pierwszego locka (clip @0.3)"); ax.set_ylabel("liczba epizodow")
    ax.set_title("R+R3: rozklad conf — poprawne i bledne locki nakladaja sie w dolnym zakresie\n(conf na zdegenerowanym wejsciu = slaby sygnal admisyjnosci, F-3b-1)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_conf_dist.png"), dpi=130); plt.close(fig)


def fig_age():
    d = json.load(open(os.path.join(OUT, "age_replay.json")))["T3_age"]
    binlab = ["<0.8s", "0.8-2s", "2-4s", "4-6s", ">6s"]
    x = np.arange(5)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=False)
    for ax, key, ttl in [(axes[0], "pooled_all_levels", "wszystkie poziomy G2 (pooled)"),
                         (axes[1], "base_p0", "baza p0.00 (frozen S3b2-R)")]:
        h = d[key]
        ax.bar(x-0.19, h["succ_hist"], width=0.38, color="#2ca02c", label=f"sukces (n={h['succ_n']})")
        ax.bar(x+0.19, h["fail_hist"], width=0.38, color="#d62728", label=f"porazka (n={h['fail_n']})")
        ax.axvline(1.5, color="k", ls=":", lw=1.2)
        ax.annotate("θ_age=2.0s", (1.55, ax.get_ylim()[1]*0.85), fontsize=8)
        ax.set_xticks(x); ax.set_xticklabels(binlab, fontsize=8)
        ax.set_title(ttl, fontsize=10); ax.set_ylabel("liczba epizodow"); ax.legend(fontsize=8)
        ax.grid(alpha=0.3, axis="y")
    fig.suptitle("R-B: age kanalu przy wejsciu w dwell — porazki maja ogon >6s (kanal zamrozony), sukcesy nie", fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_age_dwell.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    fig_roc(); fig_conf_dist(); fig_age()
    print("ZAPIS ->", OUT, [f for f in os.listdir(OUT) if f.endswith(".png")])
