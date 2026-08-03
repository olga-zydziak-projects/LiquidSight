"""proofs/a4_verify.py — A4/§5: pamięć korekt semantycznych, property-based (DP moduł 5).

Dowodzi (testem):
  (1) przed korektą: komenda z aliasem (crimson) → NO_MATCH; po podpisanej korekcie: ALLOW z
      KANONICZNYM specem (autoryzacja widzi red, nie crimson — F-D5);
  (2) alias rozwiązywany PRZED parserem/frazą (grounder dostaje „red box");
  (3) cel aliasu musi być w klasie gramatyki; nadpisanie słowa gramatyki zakazane;
  (4) łańcuch korekt HMAC-weryfikowalny + odtwarzalny;
  (5) niezmienniki: zero zmian gramatyki/wag/progów (strukturalnie — moduł nie tyka polityki/osłony).
Cert: proofs/certs/A4.json.

CLI: .venv/bin/python -m proofs.a4_verify
"""
from __future__ import annotations
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)
from demo_proof.language import parse, COLORS, SHAPES  # noqa: E402
from demo_proof.authz import Authorizer  # noqa: E402
from demo_proof.memory import SemanticMemory  # noqa: E402

CERT = os.path.join(_HERE, "certs", "A4.json")


def check_correction_flow():
    """(1)+(2): przed korektą NO_MATCH; po korekcie ALLOW z kanonicznym specem; fraza kanoniczna."""
    mem = SemanticMemory(); az = Authorizer()
    raw = "fly to the crimson box"
    # przed korektą
    assert parse(mem.resolve(raw)) is None
    rec0 = az.admit(mem.resolve(raw))
    assert rec0["decision"] == "REFUSE" and rec0["reason"] == "NO_MATCH", rec0
    # korekta podpisana
    lr = mem.learn("crimson", "red")
    assert lr["canonical"] == "red" and lr["klass"] == "color"
    # po korekcie: ta sama komenda → ALLOW, spec KANONICZNY (red), fraza „red box"
    resolved = mem.resolve(raw)
    assert resolved == "fly to the red box"                 # alias PRZED parserem
    rec1 = az.admit(resolved)
    assert rec1["decision"] == "ALLOW", rec1
    assert rec1["spec"] == {"action": "FLY", "color": "red", "shape": "box"}   # autoryzacja widzi red
    assert az.execute_phrase(rec1) == "red box"             # grounder dostaje kanoniczną frazę
    return {"before": "NO_MATCH", "after": "ALLOW", "canonical_spec": "red", "phrase": "red box"}


def check_class_guard():
    """(3): cel aliasu musi być w klasie; nadpisanie słowa gramatyki i zły cel zakazane."""
    mem = SemanticMemory()
    for alias, canon, why in [("scarlet", "vermilion", "cel poza klasami"),
                              ("red", "blue", "nadpisanie słowa gramatyki"),
                              ("crimson red", "red", "alias wielotokenowy")]:
        try:
            mem.learn(alias, canon)
            raise AssertionError(f"powinno odrzucić: {why}")
        except ValueError:
            pass
    # poprawne: alias→shape
    r = mem.learn("cube", "box")
    assert r["klass"] == "shape" and mem.resolve("fly to the red cube") == "fly to the red box"
    return {"rejected_bad_targets": 3, "shape_alias_ok": True}


def check_chain():
    """(4): łańcuch korekt weryfikowalny + odtwarzalny; sabotaż wykryty."""
    seq = [("crimson", "red"), ("cube", "box"), ("azure", "blue")]
    m1 = SemanticMemory(); [m1.learn(a, c) for a, c in seq]
    assert m1.verify_chain()
    m2 = SemanticMemory(); [m2.learn(a, c) for a, c in seq]
    assert [r["sig"] for r in m1.records] == [r["sig"] for r in m2.records], "nieodtwarzalne"
    m1.records[1]["canonical"] = "green"
    assert not m1.verify_chain(), "sabotaż niewykryty"
    return {"verifies": True, "reproducible": True, "tamper_detected": True}


def check_invariants():
    """(5): zero zmian gramatyki/wag/progów — strukturalnie."""
    import demo_proof.memory as M
    src = open(M.__file__).read()
    # moduł pamięci nie importuje polityki ani progów osłony (zero zmian wag/progów)
    assert "policy" not in src.lower() and "shield" not in src.lower() and "torch" not in src.lower()
    # gramatyka niezmieniona: alias to NOWE słowo, klasy COLORS/SHAPES stałe
    mem = SemanticMemory(); mem.learn("crimson", "red")
    assert set(COLORS) == {"red", "green", "blue"} and set(SHAPES) == {"box", "sphere", "cylinder"}
    # alias nie wchodzi do gramatyki — bez korekty „crimson" wciąż poza gramatyką
    assert parse("fly to the crimson box") is None
    return {"no_policy_shield_import": True, "grammar_unchanged": True, "weights_untouched": True}


def main():
    checks = {"correction_flow": check_correction_flow(), "class_guard": check_class_guard(),
              "chain": check_chain(), "invariants": check_invariants()}
    print("=== A4 pamięć korekt (property-based) ===")
    for k, v in checks.items():
        print(f"  {k}: {v}")
    print("WERDYKT A4: PASS")
    cert = {"property": "A4_memory", "verdict": "PASS",
            "method": "property-based: alias→klasa gramatyki, podpisany rekord, rozwiązanie przed parserem",
            "invariants": ["alias→COLORS∪SHAPES (klasa znana)", "zakaz nadpisania słowa gramatyki",
                           "alias rozwiązywany PRZED parserem (F-D5)", "zero zmian wag/progów/gramatyki",
                           "łańcuch HMAC odtwarzalny, sabotaż wykryty"],
            "checks": checks,
            "code_refs": {"memory": "demo_proof/memory.py", "authz": "demo_proof/authz.py",
                          "language": "demo_proof/language.py"},
            "scope_note": "MVP: alias→klasa (§5). Wariant egzemplarz-embedding = przyszły mandat, poza DP.",
            "model_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
    os.makedirs(os.path.dirname(CERT), exist_ok=True)
    json.dump(cert, open(CERT, "w"), indent=2, ensure_ascii=False)
    print(f"zapisano {CERT}  (model_sha256={cert['model_sha256'][:16]}…)")


if __name__ == "__main__":
    main()
