"""demo_proof/extract_states.py — A′: geometria sceny per akt (PREZENTACJA, deterministyczna).

Dla każdego aktu: `env.reset(seed)` (BEZ lotu/groundera) → zrzut statycznej geometrii sceny
(obiekty: kolor/kształt/pozycja/rozmiar + hover + arena + geofence z certyfikatu P2) do
`results/demo_proof/<act>/scene.json`. Ten sam seed → ta sama scena, którą widziało nagranie.
A3a: replikacja `relocate_designated_beyond_geofence`. Nie dotyka nagrań/certyfikatów/64² —
tylko DODAJE plik geometrii. sha256 sceny → manifest. SANITY per akt (kolor/kształt celu vs komenda).

Rider (2): geofence rysowany ze STAŁYCH certyfikatu P2 (arena=2, geo_lim=9/5=1.8, margin=1/5).
Rider (1): scene.json z seedem + sha256 w manifeście (prowieniencja jak każdy artefakt).

CLI: .venv/bin/python -m demo_proof.extract_states
"""
from __future__ import annotations
import hashlib
import json
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)
from train.common import load_cfg, make_env  # noqa: E402
from env.scene_attr import COLORS, SHAPE_GEOM  # noqa: E402
from s3c1.traps import relocate_designated_beyond_geofence  # noqa: E402

OUT = os.path.join(_ROOT, "results", "demo_proof")
ACTS = [("A1", 46513, False), ("A2", 46502, False), ("A3a", 47425, True),
        ("A3b", 46503, False), ("A4", 46505, False)]

# geofence ze stałych certyfikatu P2 (rider 2) — spięte z dowodem, nie rysowane z ręki
_p2 = json.load(open(os.path.join(_ROOT, "proofs", "certs", "P2.json")))["constants_rational"]
ARENA = round(eval(_p2["arena_half"]), 4)  # 2
GEO_LIM = round(eval(_p2["geo_lim"]), 4)   # 9/5 = 1.8
MARGIN = round(ARENA - GEO_LIM, 4)         # 1/5 = 0.2
RENDER = {"colors": {k: list(v) for k, v in COLORS.items()}, "shapes": SHAPE_GEOM}


def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sanity(command, objects, did):
    """Eyeball: kolor/kształt celu w scene.json zgodne z komendą."""
    des = next((o for o in objects if o["id"] == did), None)
    parts = command.replace("fly to the ", "").split()
    ok = bool(des) and len(parts) == 2 and des["color"] == parts[0] and des["shape"] == parts[1]
    return {"designated_color_shape_match_command": ok,
            "command": command, "designated": (des["color"] + " " + des["shape"]) if des else None,
            "designated_pos": (des["pos"] if des else None)}


def extract(act, seed, geofence):
    cfg = load_cfg(); env = make_env(cfg)
    try:
        obs, info = env.reset(scene_seed=seed, level="T0", scene_type="3b")
        if geofence:
            relocate_designated_beyond_geofence(env, coord=2.2)   # A3a: cel poza areną (jak w nagraniu)
        objs = [{"id": o["id"], "color": o["color"], "shape": o["shape"],
                 "pos": [round(float(x), 4) for x in o["pos"]], "designated": bool(o["designated"])}
                for o in env.scene["objects"]]
        scene = {"act": act, "seed": seed, "command": info["command"],
                 "designated_id": info["designated_id"],
                 "hover": [round(float(x), 4) for x in env.hover],
                 "arena_half": ARENA, "geo_lim": GEO_LIM, "margin": MARGIN,
                 "objects": objs, "render": RENDER,
                 "sanity": sanity(info["command"], objs, info["designated_id"])}
    finally:
        env.close()
    return scene


def main():
    manifest_path = os.path.join(OUT, "manifest.json")
    man = {m["act"]: m for m in json.load(open(manifest_path))["episodes"]}
    notes = []
    for act, seed, geo in ACTS:
        scene = extract(act, seed, geo)
        body = json.dumps(scene, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        h = sha256_str(body)
        path = os.path.join(OUT, act, "scene.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(json.dumps(scene, indent=2, ensure_ascii=False))
        man[act]["scene_seed"] = seed
        man[act]["scene_sha256"] = h
        san = scene["sanity"]
        notes.append(f"[{act}] seed={seed} obj={len(scene['objects'])} SANITY={'OK' if san['designated_color_shape_match_command'] else 'FAIL'} "
                     f"(cmd='{san['command']}' des='{san['designated']}' pos={san['designated_pos']}) sha={h[:12]}")
        print(notes[-1], flush=True)
    order = ["A1", "A2", "A3a", "A3b", "A4"]
    json.dump({"episodes": [man[a] for a in order if a in man]}, open(manifest_path, "w"), indent=2, ensure_ascii=False)
    allok = all("SANITY=OK" in n for n in notes)
    print(f"\nSANITY per akt: {'WSZYSTKIE OK' if allok else 'UWAGA — sprawdź FAIL'}")
    print(f"geofence viz ze stałych P2: arena={ARENA} geo_lim={GEO_LIM} margin={MARGIN}")


if __name__ == "__main__":
    main()
