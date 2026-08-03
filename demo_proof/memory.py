"""demo_proof/memory.py — pamięć korekt semantycznych (DP §5, akt A4).

Korekta człowieka = mapowanie ALIASU na klasę ZNANĄ gramatyce (np. crimson→red), zapisywane jako
podpisany rekord (HMAC, jak authz) i aktywne od następnej komendy. Alias rozwiązywany PRZED parserem
(F-D5) — autoryzacja zawsze widzi kanoniczny spec; grounder dostaje kanoniczną frazę „red box",
nigdy „crimson box".

ZAKAZY (niezmienniki §5): zero zmian wag polityki, zero zmian progów osłony, zero zmian gramatyki
(alias nie może nadpisać istniejącego słowa gramatyki; cel aliasu MUSI należeć do COLORS∪SHAPES).
Ten moduł nie importuje polityki ani progów osłony — korekta żyje wyłącznie w słowniku aliasów.
"""
from __future__ import annotations

from demo_proof.language import COLORS, SHAPES, normalize
from demo_proof.authz import sign, DEMO_KEY, GENESIS

GRAMMAR_WORDS = set(COLORS) | set(SHAPES) | {"fly", "to", "the", "hold", "resume", "return",
                                            "home", "abort"}


class SemanticMemory:
    """Słownik aliasów + łańcuch podpisanych rekordów korekt (deterministyczny, bez zegara)."""

    def __init__(self, key: bytes = DEMO_KEY):
        self.key = key
        self.aliases: dict[str, str] = {}
        self.records: list[dict] = []

    def learn(self, alias: str, canonical: str) -> dict:
        alias = normalize(alias); canonical = normalize(canonical)
        klass = "color" if canonical in COLORS else "shape" if canonical in SHAPES else None
        if klass is None:
            raise ValueError(f"cel aliasu '{canonical}' poza klasami gramatyki (COLORS∪SHAPES)")
        if alias in GRAMMAR_WORDS:
            raise ValueError(f"alias '{alias}' jest słowem gramatyki — zakaz nadpisania (§5)")
        if " " in alias:
            raise ValueError("alias musi być pojedynczym tokenem")
        prev = self.records[-1]["sig"] if self.records else GENESIS
        payload = {"seq": len(self.records), "prev_hash": prev,
                   "kind": "alias", "alias": alias, "canonical": canonical, "klass": klass}
        rec = dict(payload); rec["sig"] = sign(payload, self.key)
        self.records.append(rec)
        self.aliases[alias] = canonical           # aktywne od następnej komendy
        return rec

    def resolve(self, command: str) -> str:
        """Rozwija aliasy token-po-tokenie PRZED parserem (F-D5)."""
        return " ".join(self.aliases.get(t, t) for t in normalize(command).split())

    def verify_chain(self) -> bool:
        import hmac
        prev = GENESIS
        for rec in self.records:
            payload = {k: rec[k] for k in ("seq", "prev_hash", "kind", "alias", "canonical", "klass")}
            if rec["prev_hash"] != prev or not hmac.compare_digest(rec["sig"], sign(payload, self.key)):
                return False
            prev = rec["sig"]
        return True
