#!/usr/bin/env python3
"""Abstention (selective prediction) analysis on the committed per-image JSONL.

Usage: 05_abstention_analysis.py --baseline eval_baseline_test.jsonl
                                 --finetuned eval_lora_test.jsonl
                                 --out abstention.md --json abstention.json

For each model: risk-coverage table (accuracy on the most-confident
fraction of images at several coverage levels), accuracy of the abstained
remainder, expected calibration error (10 equal-width bins), Brier score of
the max-probability confidence, and the confidence threshold that yields
each coverage. Confidence = softmax over the six answer-letter logits; it
is a proxy, not a calibrated probability - the ECE column says how far off.
"""
import argparse, json

COVERAGES = [1.0, 0.95, 0.9, 0.8, 0.7, 0.5]

def load(p):
    return [json.loads(l) for l in open(p)]

def analyse(recs):
    srt = sorted(recs, key=lambda r: -r["confidence"])
    n = len(srt)
    rows = []
    for c in COVERAGES:
        k = max(1, int(round(c * n)))
        kept, dropped = srt[:k], srt[k:]
        rows.append({"coverage": c, "kept": k,
                     "threshold": kept[-1]["confidence"],
                     "selective_accuracy": sum(r["correct"] for r in kept) / k,
                     "abstained_accuracy": (sum(r["correct"] for r in dropped) / len(dropped)) if dropped else None})
    bins = [[] for _ in range(10)]
    for r in recs:
        bins[min(9, int(r["confidence"] * 10))].append(r)
    ece = sum(len(b) / n * abs(sum(r["correct"] for r in b) / len(b) - sum(r["confidence"] for r in b) / len(b))
              for b in bins if b)
    brier = sum((r["confidence"] - (1.0 if r["correct"] else 0.0)) ** 2 for r in recs) / n
    return {"n": n, "risk_coverage": rows, "ece_10bin": ece, "brier_maxprob": brier,
            "overall_accuracy": sum(r["correct"] for r in recs) / n}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True); ap.add_argument("--finetuned", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--json", required=True)
    a = ap.parse_args()
    b, f = analyse(load(a.baseline)), analyse(load(a.finetuned))
    json.dump({"baseline": b, "finetuned": f}, open(a.json, "w"), indent=2)
    with open(a.out, "w") as fh:
        fh.write("# Abstention analysis (selective prediction on the held-out test split)\n\n")
        fh.write("Confidence = softmax over the six answer-letter logits (a proxy). "
                 "Coverage = fraction of images on which the model answers; the rest is abstained / escalated.\n\n")
        fh.write("| coverage | zero-shot: acc on answered | zero-shot: acc on abstained | zero-shot: threshold | fine-tuned: acc on answered | fine-tuned: acc on abstained | fine-tuned: threshold |\n|---|---|---|---|---|---|---|\n")
        for rb, rf in zip(b["risk_coverage"], f["risk_coverage"]):
            fa = lambda v: "-" if v is None else f"{v:.3f}"
            fh.write(f"| {int(rb['coverage']*100)}% | {rb['selective_accuracy']:.3f} | {fa(rb['abstained_accuracy'])} | {rb['threshold']:.3f} | "
                     f"{rf['selective_accuracy']:.3f} | {fa(rf['abstained_accuracy'])} | {rf['threshold']:.3f} |\n")
        fh.write(f"\n| calibration metric | zero-shot | fine-tuned |\n|---|---|---|\n")
        fh.write(f"| expected calibration error (10 bins) | {b['ece_10bin']:.3f} | {f['ece_10bin']:.3f} |\n")
        fh.write(f"| Brier score (max-prob vs correct) | {b['brier_maxprob']:.3f} | {f['brier_maxprob']:.3f} |\n")
        fh.write(f"| overall accuracy (100% coverage) | {b['overall_accuracy']:.3f} | {f['overall_accuracy']:.3f} |\n")
    print(json.dumps({"baseline_ece": round(b["ece_10bin"], 3), "finetuned_ece": round(f["ece_10bin"], 3)}))
    for r in f["risk_coverage"]:
        print(f"finetuned coverage {int(r['coverage']*100):3d}%  acc {r['selective_accuracy']:.3f}  abstained acc {r['abstained_accuracy']}")

if __name__ == "__main__":
    main()
