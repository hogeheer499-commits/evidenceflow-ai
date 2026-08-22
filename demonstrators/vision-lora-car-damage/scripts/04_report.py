#!/usr/bin/env python3
"""Metrics + comparison report.

Usage: 04_report.py --baseline eval_base.jsonl --finetuned eval_lora.jsonl
                    [--repeat eval_lora_repeat.jsonl] --out report.md --json metrics.json
Reports accuracy, macro-F1, per-class F1, confusion matrix, and selective
accuracy at 90% coverage (abstain on the 10% lowest-confidence images).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import LABELS

def load(p):
    return [json.loads(l) for l in open(p)]

def metrics(recs):
    n = len(recs)
    acc = sum(r["correct"] for r in recs) / n
    f1s, per = [], {}
    for c in LABELS:
        tp = sum(r["pred"] == c and r["label"] == c for r in recs)
        fp = sum(r["pred"] == c and r["label"] != c for r in recs)
        fn = sum(r["pred"] != c and r["label"] == c for r in recs)
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
        f1s.append(f1); per[c] = {"precision": p, "recall": rc, "f1": f1, "support": tp + fn}
    conf = {a: {b: 0 for b in LABELS} for a in LABELS}
    for r in recs:
        conf[r["label"]][r["pred"]] += 1
    srt = sorted(recs, key=lambda r: -r["confidence"])
    k = int(round(0.9 * n))
    sel = sum(r["correct"] for r in srt[:k]) / k
    abst_acc = sum(r["correct"] for r in srt[k:]) / max(1, n - k)
    letter_rate = sum(r["free_top_is_letter"] for r in recs) / n
    return {"n": n, "accuracy": acc, "macro_f1": sum(f1s) / len(f1s),
            "per_class": per, "confusion": conf,
            "selective_accuracy_at_90_coverage": sel,
            "accuracy_of_abstained_10pct": abst_acc,
            "free_answer_is_letter_rate": letter_rate,
            "mean_confidence": sum(r["confidence"] for r in recs) / n}

def table(m):
    s = "| class | precision | recall | F1 | support |\n|---|---|---|---|---|\n"
    for c in LABELS:
        p = m["per_class"][c]
        s += f"| {c} | {p['precision']:.3f} | {p['recall']:.3f} | {p['f1']:.3f} | {p['support']} |\n"
    return s

def confusion(m):
    s = "| true \\ pred | " + " | ".join(LABELS) + " |\n|---|" + "---|" * 6 + "\n"
    for a in LABELS:
        s += f"| {a} | " + " | ".join(str(m["confusion"][a][b]) for b in LABELS) + " |\n"
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--finetuned", required=True)
    ap.add_argument("--repeat")
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()
    b, f = metrics(load(a.baseline)), metrics(load(a.finetuned))
    delta_f1 = 100 * (f["macro_f1"] - b["macro_f1"])
    rep = None
    if a.repeat:
        r1, r2 = load(a.finetuned), load(a.repeat)
        rep = {"identical_predictions": all(x["pred"] == y["pred"] for x, y in zip(r1, r2)),
               "max_abs_conf_delta": max(abs(x["confidence"] - y["confidence"]) for x, y in zip(r1, r2)),
               "byte_identical": open(a.finetuned, "rb").read() == open(a.repeat, "rb").read()}
    verdict = "PASS" if delta_f1 >= 10.0 else "FAIL"
    out = {"baseline": b, "finetuned": f, "delta_macro_f1_points": delta_f1,
           "repeat": rep, "acceptance_delta_f1_ge_10": verdict}
    json.dump(out, open(a.json, "w"), indent=2)
    with open(a.out, "w") as fh:
        fh.write("# Zero-shot baseline vs LoRA fine-tune (held-out test split)\n\n")
        fh.write("| metric | zero-shot baseline | LoRA fine-tuned |\n|---|---|---|\n")
        for k, lab in [("accuracy", "accuracy"), ("macro_f1", "macro-F1"),
                       ("selective_accuracy_at_90_coverage", "selective accuracy @90% coverage"),
                       ("accuracy_of_abstained_10pct", "accuracy on abstained 10%"),
                       ("free_answer_is_letter_rate", "unrestricted answer is a letter"),
                       ("mean_confidence", "mean confidence")]:
            fh.write(f"| {lab} | {b[k]:.4f} | {f[k]:.4f} |\n")
        fh.write(f"| n | {b['n']} | {f['n']} |\n\n")
        fh.write(f"**Delta macro-F1: {delta_f1:+.2f} points** -> pre-registered acceptance "
                 f"(>= +10 points): **{verdict}**\n\n")
        fh.write("## Per-class (baseline)\n\n" + table(b) + "\n## Per-class (fine-tuned)\n\n" + table(f))
        fh.write("\n## Confusion (baseline)\n\n" + confusion(b) + "\n## Confusion (fine-tuned)\n\n" + confusion(f))
        if rep:
            fh.write(f"\n## Repeat evaluation (fresh process)\n\n- identical predictions: {rep['identical_predictions']}\n"
                     f"- max |confidence delta|: {rep['max_abs_conf_delta']:.2e}\n- byte-identical JSONL: {rep['byte_identical']}\n")
    print(json.dumps({k: out[k] for k in ("delta_macro_f1_points", "acceptance_delta_f1_ge_10")}),
          "baseline acc", round(b["accuracy"], 4), "finetuned acc", round(f["accuracy"], 4))

if __name__ == "__main__":
    main()
