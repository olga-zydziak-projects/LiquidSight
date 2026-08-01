"""Figury RAPORT_3C_MVP (odczyt results/s3c1/, zapis results/s3c1/fig_*.png). Zero pomiarow."""
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "results", "s3c1")


def fig_conversion_legB():
    d = json.load(open(os.path.join(OUT, "s1_legB.json")))
    k = d["konwersje"]
    labels = ["wrong-action\n→odmowa", "porażka\n→odmowa", "sukces\n→odmowa", "bez\nzmian"]
    vals = [k["wrong_action->odmowa"], k["porazka->odmowa"], k["sukces->odmowa"], k["bez_zmian"]]
    colors = ["#2ca02c", "#1f77b4", "#d62728", "#7f7f7f"]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    bars = ax.bar(labels, vals, color=colors)
    for b, v in zip(bars, vals):
        ax.annotate(str(v), (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontweight="bold")
    sh = d["shield"]; ba = d["base"]
    ax.set_ylabel("liczba epizodów (z 50)")
    ax.set_title(f"Noga B (dropout p=0.5): macierz konwersji osłony v2\n"
                 f"baza sukces {ba['sukces_pct']}% → osłona: SUKCES {sh['SUKCES']} / "
                 f"ODMOWA {sh['ODMOWA']} / PORAŻKA {sh['PORAZKA']} (wrong-action {sh['wrong_action']})")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_konwersja_nogaB.png"), dpi=130); plt.close(fig)


def _panel(ax, tr, title):
    ts = [p["t"] for p in tr]
    age = [p["values"]["age_s"] if p["values"]["age_s"] is not None else np.nan for p in tr]
    ax.plot(ts, age, "-o", color="#1f77b4", ms=3, label="age_s kanału")
    ax.axhline(2.0, color="#ff7f0e", ls=":", label="θ_age=2.0 s (admisja)")
    ax.axhline(6.0, color="#d62728", ls="--", label="sufit 6.0 s")
    hold_lab = allow_lab = ref_lab = False
    for i, p in enumerate(tr):
        if p["decision"] == "HOLD":
            ax.axvspan(ts[i] - 0.045, ts[i] + 0.045, color="#ff7f0e", alpha=0.22,
                       label=(None if hold_lab else "HOLD")); hold_lab = True
        elif p["decision"] == "REFUSE":
            ax.axvline(ts[i], color="k", lw=2, label=(None if ref_lab else "REFUSE")); ref_lab = True
        elif p.get("detail", "").startswith("admisja przyznana") and not allow_lab:
            ax.axvline(ts[i], color="#2ca02c", lw=1.6, ls="-",
                       label="admisja (HOLD→ALLOW)"); allow_lab = True
    ax.set_xlabel("czas epizodu [s]"); ax.set_ylabel("age_s [s]")
    ax.set_title(title, fontsize=9)
    h, l = ax.get_legend_handles_labels()
    seen = dict(zip(l, h)); ax.legend(seen.values(), seen.keys(), fontsize=7)
    ax.grid(alpha=0.3)


def fig_hold_timelines():
    path = os.path.join(OUT, "traces_legB.json")
    if not os.path.exists(path):
        print("brak traces_legB.json — pomijam osie czasu"); return
    tr = json.load(open(path)); picks = tr.get("_picks", {})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, kind, ttl in [(axes[0], "hold_refuse", "HOLD → REFUSE (kanał się nie odświeżył)"),
                          (axes[1], "hold_allow", "HOLD → ALLOW (świeży tick → re-admisja)")]:
        seed = picks.get(kind)
        if seed is None or str(seed) not in tr:
            ax.set_title(ttl + " — brak przykładu", fontsize=9); continue
        _panel(ax, tr[str(seed)], f"{ttl}\nseed {seed}")
    fig.suptitle("R-B v2: oś czasu epizodu — admisja na wejściu, sufit 6.0 s", fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_os_czasu_hold.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    fig_conversion_legB()
    fig_hold_timelines()
    print("ZAPIS ->", OUT, [f for f in os.listdir(OUT) if f.endswith(".png")])
