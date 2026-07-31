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
    ax.set_title(f"Noga B (dropout p=0.5): macierz konwersji osłony\n"
                 f"baza sukces {ba['sukces_pct']}% → osłona: SUKCES {sh['SUKCES']} / "
                 f"ODMOWA {sh['ODMOWA']} / PORAŻKA {sh['PORAZKA']} (wrong-action {sh['wrong_action']})")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_konwersja_nogaB.png"), dpi=130); plt.close(fig)


def fig_hold_timeline():
    """Oś czasu przykładowego epizodu HOLD->REFUSE(STALE) z nogi B."""
    d = json.load(open(os.path.join(OUT, "s1_legB.json")))
    # znajdź epizod z HOLD i odmową STALE
    cand = None
    # episodes tu nie mają trace; trace jest w rekordach shield — wczytaj z pełnego dumpu jeśli jest
    full = d.get("shield_traces")  # opcjonalnie
    # trace zapisany w episodes? nie; użyj pola z analizy: potrzebny pełny rekord.
    # Odtwarzamy z pliku episodes: wybierz seed z n_hold_enter>0
    seeds_hold = [e for e in d["episodes"] if e.get("n_hold_enter", 0) > 0 and "ODMOWA" in e["shield"]]
    if not seeds_hold:
        seeds_hold = [e for e in d["episodes"] if e.get("n_hold_enter", 0) > 0]
    if not seeds_hold:
        print("brak epizodu HOLD do figury osi czasu"); return
    target_seed = seeds_hold[0]["seed"]
    # trace pełny nie jest w s1_legB.json episodes; wczytaj z traces jeśli zapisano osobno
    tr = _load_trace(target_seed)
    if tr is None:
        print("trace niedostępny — pomijam oś czasu"); return
    ts = [p["t"] for p in tr]
    age = [p["values"]["age_s"] if p["values"]["age_s"] is not None else np.nan for p in tr]
    dec = [p["decision"] for p in tr]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(ts, age, "-o", color="#1f77b4", ms=3, label="age_s kanału")
    ax.axhline(2.0, color="#d62728", ls=":", label="θ_age=2.0 s")
    for i, dc in enumerate(dec):
        if dc == "HOLD":
            ax.axvspan(ts[i] - 0.04, ts[i] + 0.04, color="#ff7f0e", alpha=0.25)
        if dc == "REFUSE":
            ax.axvline(ts[i], color="k", lw=2, label="REFUSE(STALE_AT_DWELL)")
    ax.set_xlabel("czas epizodu [s]"); ax.set_ylabel("age_s [s]")
    ax.set_title(f"Przykład osi czasu (seed {target_seed}): HOLD (pomarańczowy) → REFUSE gdy kanał nie odświeżył się w T_hold")
    h, l = ax.get_legend_handles_labels()
    seen = dict(zip(l, h))
    ax.legend(seen.values(), seen.keys(), fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_os_czasu_hold.png"), dpi=130); plt.close(fig)


def _load_trace(seed):
    path = os.path.join(OUT, "traces_legB.json")
    if os.path.exists(path):
        traces = json.load(open(path))
        return traces.get(str(seed))
    return None


if __name__ == "__main__":
    fig_conversion_legB()
    fig_hold_timeline()
    print("ZAPIS ->", OUT, [f for f in os.listdir(OUT) if f.endswith(".png")])
