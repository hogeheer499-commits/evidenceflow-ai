#!/usr/bin/env python3
"""Constrained 6-way classification eval for a (base or LoRA-adapted) Qwen2.5-VL.

Usage: 02_eval.py --model <base_or_adapter_dir> --manifest manifest.csv
                  --data-root <dir> --split test --out eval.jsonl

One forward pass per image; prediction = argmax over the logits of the six
answer letters at the first generated position; confidence = softmax over
those six logits. Also records the unrestricted top token for transparency.
Fully deterministic (no sampling).
"""
import argparse, csv, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import torch
from PIL import Image
from unsloth import FastVisionModel
from common import LABELS, LETTERS, PROMPT, LETTER_TO_LABEL

MAX_PIXELS = 512 * 512
MIN_PIXELS = 128 * 128

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    model, tokenizer = FastVisionModel.from_pretrained(
        args.model, load_in_4bit=False, dtype=torch.bfloat16)
    FastVisionModel.for_inference(model)
    tokenizer.image_processor.max_pixels = MAX_PIXELS
    tokenizer.image_processor.min_pixels = MIN_PIXELS
    tok = tokenizer.tokenizer

    letter_ids = []
    for L in LETTERS:
        variants = {tok.encode(L, add_special_tokens=False)[0],
                    tok.encode(" " + L, add_special_tokens=False)[0]}
        letter_ids.append(sorted(variants))

    rows = [r for r in csv.DictReader(open(args.manifest)) if r["split"] == args.split]
    if args.limit:
        rows = rows[:args.limit]
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PROMPT}]}]
    text = tokenizer.apply_chat_template(messages, add_generation_prompt=True)

    n_ok = 0
    t0 = time.time()
    with open(args.out, "w") as fh:
        for i, r in enumerate(rows):
            img = Image.open(os.path.join(args.data_root, r["path"])).convert("RGB")
            inputs = tokenizer(img, text, add_special_tokens=False, return_tensors="pt").to("cuda")
            with torch.no_grad():
                logits = model(**inputs).logits[0, -1].float()
            six = torch.stack([logits[ids].max() for ids in letter_ids])
            probs = torch.softmax(six, dim=0)
            k = int(probs.argmax())
            pred = LETTER_TO_LABEL[LETTERS[k]]
            top_id = int(logits.argmax())
            rec = {"path": r["path"], "label": r["label"], "pred": pred,
                   "confidence": float(probs[k]),
                   "probs": {LABELS[j]: float(probs[j]) for j in range(6)},
                   "free_top_token": tok.decode([top_id]),
                   "free_top_is_letter": any(top_id in ids for ids in letter_ids),
                   "correct": pred == r["label"],
                   "image_tokens": int(inputs["input_ids"].shape[1])}
            n_ok += rec["correct"]
            fh.write(json.dumps(rec) + "\n")
            if (i + 1) % 25 == 0:
                print(f"{i+1}/{len(rows)} acc={n_ok/(i+1):.3f} {(time.time()-t0)/(i+1):.2f}s/img", flush=True)
    print(f"DONE {args.split}: n={len(rows)} accuracy={n_ok/len(rows):.4f} "
          f"elapsed={time.time()-t0:.1f}s")

if __name__ == "__main__":
    main()
