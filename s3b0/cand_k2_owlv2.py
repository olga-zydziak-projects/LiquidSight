"""cand_k2_owlv2 — S3b0 T3 K2: OWLv2 (transformers) grounder.

Query = fraza komendy ("{color} {shape}"); top-1 po score.
Model: google/owlv2-base-patch16-ensemble. Uruchomienie: python cand_k2_owlv2.py
"""
from __future__ import annotations

import run_candidate


class K2:
    name = "K2_owlv2"
    model_id = "google/owlv2-base-patch16-ensemble"
    prompt_template = 'text query = "{color} {shape}"; top-1 po score'

    def load(self):
        import torch
        from transformers import Owlv2ForObjectDetection, Owlv2Processor
        self.torch = torch
        self.proc = Owlv2Processor.from_pretrained(self.model_id)
        self.model = Owlv2ForObjectDetection.from_pretrained(self.model_id).to("cuda").eval()

    def predict_raw(self, img, command):
        phrase = command.replace("fly to the ", "").strip()
        with self.torch.no_grad():
            inputs = self.proc(text=[[phrase]], images=img, return_tensors="pt").to("cuda")
            outputs = self.model(**inputs)
            target_sizes = self.torch.tensor([(img.height, img.width)]).to("cuda")
            res = self.proc.post_process_grounded_object_detection(
                outputs, threshold=0.0, target_sizes=target_sizes)[0]
        dets = []
        for box, score in zip(res["boxes"], res["scores"]):
            dets.append((box.tolist(), float(score)))
        return dets


if __name__ == "__main__":
    run_candidate.run(K2())
