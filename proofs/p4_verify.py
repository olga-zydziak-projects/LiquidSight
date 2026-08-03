"""proofs/p4_verify.py — P4: autoryzacja (gramatyka + admisja + rekordy) property-based (DP moduł 4).

Dowodzi (testem wyczerpującym + property-based) właściwości P4 z PRE_DP0 §3:
  (a) żadna misja bez admisji (execute odmawia gdy ≠ ALLOW);
  (b) spec wykonany ≡ spec admitowany (fraza z rekordu ALLOW; kontrakt F-D5 z grounderem);
  (c) poza gramatyką ⇒ REFUSE(NO_MATCH);
  (d) rekord HMAC-podpisany, łańcuch weryfikowalny, odtwarzalny (bez zegara), sabotaż wykryty.
Plus: cel poza geofencem ⇒ REFUSE(GEOFENCE) na admisji (A3ii, link do P2).
Cert: proofs/certs/P4.json.

CLI: .venv/bin/python -m proofs.p4_verify
"""
from __future__ import annotations
import hashlib
import json
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)
from demo_proof.language import parse, Spec, COLORS, SHAPES  # noqa: E402
from demo_proof.authz import Authorizer  # noqa: E402

CERT = os.path.join(_HERE, "certs", "P4.json")

IN_GRAMMAR = ([f"fly to the {c} {s}" for c in COLORS for s in SHAPES] +
              ["hold", "resume", "return home", "abort"])          # 9 + 4 = 13
OUT_GRAMMAR = [
    "fly to the crimson box",        # nieznany kolor (alias — materiał A4)
    "fly to the red pyramid",        # nieznany kształt
    "fly to the red",                # brak kształtu
    "fly to the red box now",        # nadmiarowe słowo
    "fly red box",                   # brak 'to the'
    "go to the red box",             # zły czasownik
    "", "   ", "halt", "land",       # puste / nieznane komendy
    "fly to the box red",            # zła kolejność (box nie jest kolorem)
]


def check_c():
    """(c) poza gramatyką ⇒ None(→NO_MATCH); w gramatyce ⇒ Spec."""
    for cmd in IN_GRAMMAR:
        assert parse(cmd) is not None, cmd
    for cmd in OUT_GRAMMAR:
        assert parse(cmd) is None, f"powinno być poza gramatyką: {cmd!r}"
    az = Authorizer()
    for cmd in OUT_GRAMMAR:
        rec = az.admit(cmd)
        assert rec["decision"] == "REFUSE" and rec["reason"] == "NO_MATCH", (cmd, rec)
    return {"in_grammar": len(IN_GRAMMAR), "out_grammar_refused_nomatch": len(OUT_GRAMMAR)}


def check_b():
    """(b) spec wykonany ≡ admitowany + kontrakt F-D5 (fraza = command.replace('fly to the ',''))."""
    az = Authorizer()
    n = 0
    for c in COLORS:
        for s in SHAPES:
            cmd = f"fly to the {c} {s}"
            rec = az.admit(cmd)
            phrase = az.execute_phrase(rec)                 # tylko ALLOW; fraza z rekordu
            assert phrase == f"{c} {s}", (cmd, phrase)
            # kontrakt groundera (s3b3/grounder_server.py:40): replace prefiksu daje TĘ SAMĄ frazę
            assert cmd.replace("fly to the ", "").strip() == phrase
            n += 1
    return {"fly_specs_checked": n, "grounder_contract": "phrase == command.replace('fly to the ','')"}


def check_a():
    """(a) żadna misja bez admisji: execute na ≠ALLOW rzuca."""
    az = Authorizer()
    refused = az.admit("fly to the red pyramid")            # NO_MATCH
    try:
        az.execute_phrase(refused)
        raise AssertionError("execute powinno odmówić dla REFUSE")
    except PermissionError:
        pass
    hold = az.admit("hold")                                 # ALLOW ale nie-FLY → fraza None
    assert az.execute_phrase(hold) is None
    return {"execute_refuses_non_allow": True}


def check_d():
    """(d) HMAC + łańcuch: weryfikacja, odtwarzalność, wykrycie sabotażu."""
    cmds = ["fly to the red box", "hold", "resume", "fly to the blue sphere", "abort"]
    az1 = Authorizer(); [az1.admit(c) for c in cmds]
    assert az1.verify_chain(), "łańcuch powinien być poprawny"
    # odtwarzalność: ten sam klucz + komendy → identyczne podpisy (bez zegara)
    az2 = Authorizer(); [az2.admit(c) for c in cmds]
    assert [r["sig"] for r in az1.chain] == [r["sig"] for r in az2.chain], "łańcuch nieodtwarzalny"
    # sabotaż: podmiana decyzji w środku łańcucha wykryta
    az1.chain[1]["decision"] = "REFUSE"
    assert not az1.verify_chain(), "sabotaż powinien być wykryty"
    # sabotaż prev_hash
    az3 = Authorizer(); [az3.admit(c) for c in cmds]
    az3.chain[2]["prev_hash"] = "0" * 64
    assert not az3.verify_chain(), "zerwanie łańcucha powinno być wykryte"
    return {"chain_verifies": True, "reproducible": True, "tamper_detected": True}


def check_geofence_admission():
    """A3ii: FLY z celem poza ogrodzeniem ⇒ REFUSE(GEOFENCE) na admisji."""
    az = Authorizer()
    rec = az.admit("fly to the red box", target_xy=(1.95, 0.1))   # 1.95 > 1.8
    assert rec["decision"] == "REFUSE" and rec["reason"] == "GEOFENCE", rec
    rec2 = az.admit("fly to the red box", target_xy=(1.2, 0.3))   # w arenie
    assert rec2["decision"] == "ALLOW", rec2
    return {"target_beyond_arena_refused": True}


def check_property_based(n=2000):
    """Property-based: losowe komendy — w gramatyce ⇔ (ALLOW lub GEOFENCE), inaczej NO_MATCH."""
    rng = random.Random(0)
    words = list(COLORS) + list(SHAPES) + ["fly", "to", "the", "hold", "abort", "crimson",
                                           "pyramid", "cube", "go", "now", "home", "return"]
    az = Authorizer()
    for _ in range(n):
        k = rng.randint(0, 6)
        cmd = " ".join(rng.choice(words) for _ in range(k))
        spec = parse(cmd)
        rec = az.admit(cmd)
        if spec is None:
            assert rec["decision"] == "REFUSE" and rec["reason"] == "NO_MATCH", (cmd, rec)
        else:
            assert rec["decision"] == "ALLOW" and rec["spec"] == spec.as_dict(), (cmd, rec)
    assert az.verify_chain()
    return {"random_commands": n, "invariant": "in_grammar ⇔ ALLOW; else NO_MATCH"}


def main():
    checks = {"P4c_out_of_grammar": check_c(), "P4b_exec_eq_admitted": check_b(),
              "P4a_no_mission_without_admission": check_a(), "P4d_hmac_chain": check_d(),
              "geofence_admission": check_geofence_admission(),
              "property_based": check_property_based()}
    print("=== P4 autoryzacja (property-based) ===")
    for k, v in checks.items():
        print(f"  {k}: {v}")
    print("WERDYKT P4: PASS")
    cert = {"property": "P4", "verdict": "PASS",
            "method": "exhaustive grammar + property-based admission/records; HMAC-SHA256 chain",
            "grammar": {"fly": "fly to the {color} {shape}", "colors": list(COLORS),
                        "shapes": list(SHAPES), "commands": ["hold", "resume", "return home", "abort"]},
            "properties": {
                "P4a": "execute odmawia gdy rekord ≠ ALLOW",
                "P4b": "fraza wykonania = fraza z rekordu ALLOW = command.replace('fly to the ','') (F-D5)",
                "P4c": "poza gramatyką ⇒ REFUSE(NO_MATCH)",
                "P4d": "rekord HMAC-SHA256, łańcuch weryfikowalny+odtwarzalny (bez zegara), sabotaż wykryty",
                "geofence": "cel poza 1.8 ⇒ REFUSE(GEOFENCE) na admisji (A3ii)"},
            "checks": checks,
            "pcdl": "lokalny PCDL: rekord {seq,prev_hash,command_raw,decision,reason,spec,phrase,sig} + HMAC; "
                    "dług integracyjny z ProofGate nazwany (PRE_DP0 §9)",
            "code_refs": {"parser": "demo_proof/language.py", "authz": "demo_proof/authz.py",
                          "grounder_contract": "s3b3/grounder_server.py:40"},
            "model_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
    os.makedirs(os.path.dirname(CERT), exist_ok=True)
    json.dump(cert, open(CERT, "w"), indent=2, ensure_ascii=False)
    print(f"zapisano {CERT}  (model_sha256={cert['model_sha256'][:16]}…)")


if __name__ == "__main__":
    main()
