"""Figury RAPORT_3B (odczyt results/, zapis results/raport3b/*.png). Zero pomiarow."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "results", "raport3b")


def fig_g1_trajektoria():
    # bieg, sukces, wrong-lock, etykieta dzwigni
    runs = [
        ("G1\nlive", 12.0, 20.0),
        ("S3b2-R\nconf-fix+live-fed", 67.0, 10.0),
        ("R3\nF2 gating", 11.0, 7.0),
        ("R4\nF3+zly-val", 8.0, 3.0),
        ("R5\nval-fix", 58.0, 14.0),
        ("R6\nhover-rich", 53.0, 17.0),
        ("R7\nGT+live", 60.0, 12.0),
    ]
    labels = [r[0] for r in runs]; succ = [r[1] for r in runs]; wl = [r[2] for r in runs]
    x = list(range(len(runs)))
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(x, succ, "o-", color="#1f77b4", lw=2, ms=8, label="sukces desygnacji")
    ax.plot(x, wl, "s--", color="#d62728", lw=1.5, ms=6, label="wrong-lock")
    ax.axhline(85, color="#2ca02c", ls=":", lw=1.5, label="prog G1 sukces (85%, nietkniety)")
    ax.axhline(8, color="#ff7f0e", ls=":", lw=1.2, label="prog G1 wrong-lock (8%)")
    for xi, s in zip(x, succ):
        ax.annotate(f"{s:.0f}", (xi, s), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("%"); ax.set_ylim(0, 100)
    ax.set_title("G1 — trajektoria desygnacji live (dzwignie w mandacie; najlepszy = S3b2-R 67%)")
    ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "g1_trajektoria.png"), dpi=130); plt.close(fig)


def fig_g2_krzywa():
    d = json.load(open(os.path.join(ROOT, "results", "s3b4", "measure.json")))["results"]
    ps = [0.0, 0.25, 0.50, 0.75]
    bern = [d[f"p{p:.2f}"]["sukces_pct"] for p in ps]
    bsd = [d[f"p{p:.2f}"]["sd_binom_pp"] for p in ps]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.errorbar(ps, bern, yerr=bsd, fmt="o-", color="#1f77b4", lw=2, ms=8, capsize=4,
                label="Bernoulli (drop losowy/tick)")
    p0 = d["p0.00"]["sukces_pct"]
    # burst jako punkty na wlasnej osi udzialu drop (L/10 tickow)
    for L, xoff, c in [(2, 0.20, "#9467bd"), (5, 0.50, "#8c564b")]:
        lv = d[f"L{L}"]; ax.errorbar([xoff], [lv["sukces_pct"]], yerr=[lv["sd_binom_pp"]],
                                     fmt="D", color=c, ms=10, capsize=4, label=f"burst L={L}s (ciagly)")
        ax.annotate(f"L{L}: {lv['sukces_pct']:.0f}%", (xoff, lv["sukces_pct"]),
                    textcoords="offset points", xytext=(8, 6), fontsize=8, color=c)
    ax.axhline(p0, color="gray", ls=":", lw=1, label=f"kotwica p0={p0:.0f}% (parowana)")
    for p, b in zip(ps, bern):
        ax.annotate(f"{b:.0f}", (p, b), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("udzial utraconych dostarczen (Bernoulli p ; burst = L/10 tickow)")
    ax.set_ylabel("sukces %"); ax.set_ylim(0, 90)
    ax.set_title("G2 — krzywa zrywanego strumienia: burst (ciagly) mostkowany, Bernoulli (rozproszony) stromy")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "g2_krzywa.png"), dpi=130); plt.close(fig)


def fig_g2_age_hist():
    d = json.load(open(os.path.join(ROOT, "results", "s3b4", "measure.json")))["results"]
    levels = ["p0.00", "p0.25", "p0.50", "p0.75", "L2", "L5"]
    bin_lab = ["0-.1\n(<0.8s)", ".1-.25\n(<2s)", ".25-.5\n(<4s)", ".5-.75\n(<6s)", ".75-1\n(>6s)"]
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), sharey=True)
    for ax, lv in zip(axes.flat, levels):
        h = d[lv]["age_at_dwell_entry_hist"]["counts"]
        colors = ["#2ca02c", "#2ca02c", "#ff7f0e", "#ff7f0e", "#d62728"]
        ax.bar(range(5), h, color=colors)
        ax.set_title(f"{lv} (n_dwell={d[lv]['n_entered_dwell']})", fontsize=9)
        ax.set_xticks(range(5)); ax.set_xticklabels(bin_lab, fontsize=6)
        ax.grid(alpha=0.3, axis="y")
    fig.suptitle("G2 — age kanalu przy wejsciu w dwell: Bernoulli przesuwa ogon w gore (stary), burst zostaje swiezy",
                 fontsize=11)
    fig.supylabel("liczba epizodow")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "g2_age_dwell.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_g1_trajektoria(); fig_g2_krzywa(); fig_g2_age_hist()
    print("ZAPIS ->", OUT, os.listdir(OUT))
