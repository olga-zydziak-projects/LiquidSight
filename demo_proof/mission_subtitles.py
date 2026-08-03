"""demo_proof/mission_subtitles.py — subtitles.vtt GENEROWANY z logu zdarzeń misji (PRE_MC0 §3).

Napisy wyłącznie z `mission.json['events']` (kind+text+timestamp) — szablon per typ zdarzenia,
zero napisów odręcznych poza szablonami. Odtwarzalny skryptem (nie pisany ręcznie). EN.

CLI: .venv/bin/python -m demo_proof.mission_subtitles
"""
from __future__ import annotations
import json
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(_ROOT, "results", "demo_proof", "mission")

# szablon per typ zdarzenia (prefiks); tekst zdarzenia wstawiany
TPL = {
    "MISSION": "▸ {text}",
    "ADMIT": "AUTHORIZATION · {text}",
    "FRAME": "{text}",
    "TRANSIT": "TRANSIT · {text}",
    "DELIVERY": "LINK · {text}",
    "FROZEN": "LINK · {text}",
    "DWELL": "PILOT · {text}",
    "REFUSE": "SHIELD · {text}",
    "NO_MATCH": "AUTHORIZATION · {text}",
    "CORRECTION": "MEMORY · {text}",
    "LANDED": "▸ {text}",
}


def _ts(t):
    mm = int(t // 60); ss = t - mm * 60
    return f"{mm:02d}:{ss:06.3f}"


def build():
    mj = json.load(open(os.path.join(OUT, "mission.json")))
    events = sorted(mj["events"], key=lambda e: e["t"])
    T = mj["n_ticks"] * (1.0 / 12.0)
    lines = ["WEBVTT", ""]
    n = 0
    for i, e in enumerate(events):
        start = e["t"]
        end = events[i + 1]["t"] if i + 1 < len(events) else min(start + 3.0, T)
        if end <= start:
            end = start + 1.2
        text = TPL.get(e["kind"], "{text}").format(text=e["text"])
        lines += [f"{_ts(start)} --> {_ts(end)}", text, ""]
        n += 1
    path = os.path.join(OUT, "subtitles.vtt")
    open(path, "w").write("\n".join(lines))
    print(f"subtitles.vtt: {n} napisów z {len(events)} zdarzeń · {path}")
    # sanity: każdy napis pochodzi ze zdarzenia (żaden odręczny)
    assert n == len(events), "napis bez zdarzenia (zakaz odręcznych)"
    return path


if __name__ == "__main__":
    build()
