"""cand_k3_lfm2vl — S3b0 T3 K3: LFM2-VL (LiquidAI, transformers) grounder.

Prompt groundingowy -> bbox. Spec pisze "LFM2.5-VL-450M"; probujemy literalny id,
fallback do "LiquidAI/LFM2-VL-450M"; inaczej DNF z powodem.

Format bbox modelu jest niepewny -> parser best-effort + skalowanie heurystyczne
do pikseli 256. Tryb --debug drukuje surowe generacje na kilku klatkach dev
(kalibracja promptu/parsera = tuning na dev, dozwolony przed zamrozeniem).

Uruchomienie: python cand_k3_lfm2vl.py [--debug]
"""
from __future__ import annotations

import re
import sys

from PIL import Image

import run_candidate
import eval_grounder as eg

MODEL_IDS = ["LiquidAI/LFM2.5-VL-450M", "LiquidAI/LFM2-VL-450M"]
# Grid promptow (tuning WYLACZNIE na dev; model zwraca bbox znormalizowany [0,1]).
PROMPT_GRID = {
    "where": "Where is the {phrase}? Provide the bounding box.",
    "shikra": ("Please provide the bounding box coordinate of the region this "
               "sentence describes: {phrase}."),
    "locate": ("Locate the {phrase}. Output the bounding box as "
               "[x_min, y_min, x_max, y_max] normalized to 0-1."),
}
DEFAULT_PROMPT = "where"


def _parse_box(text: str, w: int = 256, h: int = 256):
    """Wyciaga 4 liczby jako bbox i skaluje do pikseli 256. None gdy brak/niepoprawny."""
    nums = re.findall(r"-?\d+\.?\d*", text)
    if len(nums) < 4:
        return None
    vals = [float(x) for x in nums[:4]]
    # skalowanie: <=1 -> znormalizowane; <=1000 i >256 -> /1000; inaczej px
    mx = max(abs(v) for v in vals)
    if mx <= 1.0:
        vals = [vals[0] * w, vals[1] * h, vals[2] * w, vals[3] * h]
    elif mx > 256 and mx <= 1000:
        vals = [vals[0] / 1000 * w, vals[1] / 1000 * h,
                vals[2] / 1000 * w, vals[3] / 1000 * h]
    x0, y0, x1, y1 = vals
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    if (x1 - x0) < 1 or (y1 - y0) < 1:
        return None
    return [max(0, x0), max(0, y0), min(w, x1), min(h, y1)]


class K3:
    name = "K3_lfm2vl"
    model_id = "/".join(MODEL_IDS)
    prompt_template = PROMPT_GRID[DEFAULT_PROMPT]

    def __init__(self):
        self.prompt_key = DEFAULT_PROMPT
        self.model = None

    def load(self):
        if self.model is not None:               # idempotent (driver wola ponownie)
            return
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        self.torch = torch
        last = None
        for mid in MODEL_IDS:
            try:
                self.proc = AutoProcessor.from_pretrained(mid, trust_remote_code=True)
                self.model = AutoModelForImageTextToText.from_pretrained(
                    mid, trust_remote_code=True, dtype=torch.bfloat16).to("cuda").eval()
                self.model_id = mid
                break
            except Exception as e:                # sprobuj kolejny id
                last = e
        if self.model is None:
            raise last
        self._select_prompt_on_dev()             # tuning promptu na DEV (przed zamrozeniem)

    def _generate(self, img, command, prompt_key=None) -> str:
        phrase = command.replace("fly to the ", "").strip()
        tmpl = PROMPT_GRID[prompt_key or self.prompt_key]
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": tmpl.format(phrase=phrase)}]}]
        inputs = self.proc.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt").to("cuda")
        with self.torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=64, do_sample=False)
        gen = out[0][inputs["input_ids"].shape[1]:]
        return self.proc.decode(gen, skip_special_tokens=True)

    def _select_prompt_on_dev(self) -> None:
        """Wybor promptu z PROMPT_GRID maksymalizujacy precision@1 na DEV."""
        dev = eg.load_gt("A", "dev")
        best, best_p, trace = DEFAULT_PROMPT, -1.0, []
        for key in PROMPT_GRID:
            preds = {}
            for r in dev:
                img = Image.open(run_candidate._abs(r["frame_path"])).convert("RGB")
                box = _parse_box(self._generate(img, r["command"], prompt_key=key))
                preds[r["frame_path"]] = {"box": box}
            p1 = eg.aggregate(preds, dev)["overall"]["precision@1"] or 0.0
            trace.append({"prompt": key, "dev_precision@1": p1})
            if p1 > best_p:
                best_p, best = p1, key
        self.prompt_key = best
        self.prompt_template = f"[{best}] " + PROMPT_GRID[best]
        self.prompt_dev_trace = trace
        print(f"K3 wybrany prompt (dev): {best} (dev prec@1={best_p}); trace={trace}")

    def predict_raw(self, img, command):
        box = _parse_box(self._generate(img, command))
        return [(box, 1.0)] if box is not None else []


def _debug():
    k = K3()
    k.load()
    print(f"zaladowano {k.model_id}")
    dev = eg.load_gt("A", "dev")
    for r in dev[:4]:
        img = Image.open(run_candidate._abs(r["frame_path"])).convert("RGB")
        txt = k._generate(img, r["command"])
        des = [o for o in r["objects"] if o["designated"]][0]
        print(f"\ncmd={r['command']} d={r['dist']}")
        print(f"  RAW: {txt!r}")
        print(f"  parsed: {_parse_box(txt)}  GT: {des['bbox']}")


if __name__ == "__main__":
    if "--debug" in sys.argv:
        _debug()
    else:
        run_candidate.run(K3())
