"""demo_proof/authz.py — admisja + podpisane rekordy decyzji (DP §4/§5, P4).

Każda misja przechodzi przez `Authorizer.admit(command)`:
  parse (gramatyka) → spec kanoniczny → decyzja (ALLOW / REFUSE(NO_MATCH|GEOFENCE)) → rekord PCDL
  podpisany HMAC-SHA256, wpięty w łańcuch (prev_hash) — odtwarzalny per lot.
Właściwości P4 (dowodzone w proofs/p4_verify.py):
  (a) żadna misja bez admisji: `execute` odmawia gdy rekord ≠ ALLOW;
  (b) spec wykonany ≡ spec admitowany: fraza wykonania = fraza z rekordu ALLOW (nie re-parse);
  (c) poza gramatyką ⇒ REFUSE(NO_MATCH);
  (d) rekord podpisany HMAC, łańcuch weryfikowalny i odtwarzalny (bez zegara ściennego).

PCDL lokalny (F-D3): schemat rekordu + HMAC (stdlib), dług integracyjny z ProofGate nazwany w PRE.
Klucz = stały klucz DEMO (nie sekret produkcyjny) — istotny jest MECHANIZM podpisu i odtwarzalność.
"""
from __future__ import annotations
import hashlib
import hmac
import json

from demo_proof.language import parse, Spec

DEMO_KEY = b"liquidsight-demo-proof-key-v1"        # DEMO (nie sekret); łańcuch odtwarzalny
GENESIS = "GENESIS"
GEO_LIM = 1.8                                       # arena_half − margin (shield R-C)


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sign(payload: dict, key: bytes = DEMO_KEY) -> str:
    return hmac.new(key, _canonical(payload).encode("utf-8"), hashlib.sha256).hexdigest()


class Authorizer:
    """Łańcuch podpisanych rekordów decyzji dla JEDNEGO lotu (deterministyczny, bez zegara)."""

    def __init__(self, key: bytes = DEMO_KEY):
        self.key = key
        self.chain: list[dict] = []

    def admit(self, command: str, target_xy=None) -> dict:
        spec = parse(command)
        prev = self.chain[-1]["sig"] if self.chain else GENESIS
        if spec is None:                            # (c) poza gramatyką
            decision, reason, specd, phrase = "REFUSE", "NO_MATCH", None, None
        elif spec.action == "FLY" and target_xy is not None and \
                max(abs(float(target_xy[0])), abs(float(target_xy[1]))) > GEO_LIM:
            decision, reason = "REFUSE", "GEOFENCE"  # cel poza ogrodzeniem (P2/A3ii)
            specd, phrase = spec.as_dict(), spec.grounder_phrase()
        else:
            decision, reason = "ALLOW", None
            specd, phrase = spec.as_dict(), spec.grounder_phrase()
        payload = {"seq": len(self.chain), "prev_hash": prev, "command_raw": command,
                   "decision": decision, "reason": reason, "spec": specd, "grounder_phrase": phrase}
        rec = dict(payload); rec["sig"] = sign(payload, self.key)
        self.chain.append(rec)
        return rec

    def execute_phrase(self, rec: dict) -> str:
        """(a)+(b): tylko admitowany ALLOW jest wykonywany; fraza = z REKORDU (nie re-parse)."""
        if rec["decision"] != "ALLOW":
            raise PermissionError(f"brak admisji: {rec['decision']}({rec['reason']})")
        return rec["grounder_phrase"]               # spec wykonany ≡ spec admitowany

    def verify_chain(self) -> bool:
        """Rekompute HMAC każdego rekordu + spójność łańcucha (prev_hash)."""
        prev = GENESIS
        for rec in self.chain:
            payload = {k: rec[k] for k in
                       ("seq", "prev_hash", "command_raw", "decision", "reason", "spec", "grounder_phrase")}
            if rec["prev_hash"] != prev:
                return False
            if not hmac.compare_digest(rec["sig"], sign(payload, self.key)):
                return False
            prev = rec["sig"]
        return True
