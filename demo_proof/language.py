"""demo_proof/language.py — gramatyka ZAMKNIĘTA, parser DETERMINISTYCZNY (DP §4, P4).

Zero LLM w torze autoryzacji. Gramatyka (PRE_DP0 §4):
  fly to the {color} {shape} | hold | resume | return home | abort
  {color} ∈ {red, green, blue}   {shape} ∈ {box, sphere, cylinder}   (paleta D4)
Parser → Spec (kanoniczny) albo None (poza gramatyką → NO_MATCH, materiał aktu A4).
Fraza groundera dla FLY = "{color} {shape}" — kontrakt F-D5 (grounder_server: set_classes([phrase]),
`command.replace("fly to the ", "")`). Alias-mapping (crimson→red) NALEŻY do pamięci korekt
(demo_proof/memory.py, moduł 5) i rozwiązuje się PRZED parserem — autoryzacja widzi kanoniczny spec.
"""
from __future__ import annotations
from dataclasses import dataclass

COLORS = ("red", "green", "blue")
SHAPES = ("box", "sphere", "cylinder")
ACTIONS = ("FLY", "HOLD", "RESUME", "RETURN_HOME", "ABORT")


@dataclass(frozen=True)
class Spec:
    action: str
    color: str | None = None
    shape: str | None = None

    def canonical_command(self) -> str:
        if self.action == "FLY":
            return f"fly to the {self.color} {self.shape}"
        return {"HOLD": "hold", "RESUME": "resume",
                "RETURN_HOME": "return home", "ABORT": "abort"}[self.action]

    def grounder_phrase(self) -> str | None:
        """Fraza do YOLO-World (tylko FLY). F-D5: dokładnie '{color} {shape}'."""
        return f"{self.color} {self.shape}" if self.action == "FLY" else None

    def as_dict(self) -> dict:
        return {"action": self.action, "color": self.color, "shape": self.shape}


def normalize(command: str) -> str:
    return " ".join(command.strip().lower().split())


def parse(command: str) -> Spec | None:
    """Deterministyczny parser gramatyki. Zwraca Spec albo None (poza gramatyką)."""
    c = normalize(command)
    if c == "hold":
        return Spec("HOLD")
    if c == "resume":
        return Spec("RESUME")
    if c == "return home":
        return Spec("RETURN_HOME")
    if c == "abort":
        return Spec("ABORT")
    prefix = "fly to the "
    if c.startswith(prefix):
        rest = c[len(prefix):].split()
        if len(rest) == 2 and rest[0] in COLORS and rest[1] in SHAPES:
            return Spec("FLY", rest[0], rest[1])
        return None            # zła liczba/nieznany atrybut → poza gramatyką
    return None                # nierozpoznana komenda → poza gramatyką


def in_grammar(command: str) -> bool:
    return parse(command) is not None
