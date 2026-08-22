#!/usr/bin/env python3
"""Error table + acceptance verdict.

Usage: 03_report.py results.csv ground_truth.csv report.md

ground_truth.csv columns: object,true_mm (median of 3 caliper readings,
or the exact constructed value for synthetic scenes).
Image names must contain the object key and condition metadata, e.g.
d450_a15_synth_r1_synthdots.png
"""
import csv
import re
import statistics as st
import sys


def main(results: str, truth: str, out_md: str) -> None:
    gt = {r["object"]: float(r["true_mm"]) for r in csv.DictReader(open(truth))}
    rows = []
    for r in csv.DictReader(open(results)):
        obj = next((o for o in gt if o in r["image"]), None)
        if obj is None:
            continue
        m = re.search(r"d(\d+)_a(\d+)_(\w+?)_r(\d+)", r["image"])
        if not m:
            continue
        meas = float(r["measured_mm"])
        err = meas - gt[obj]
        rows.append({
            "image": r["image"], "object": obj,
            "dist": m.group(1), "angle": m.group(2), "light": m.group(3),
            "meas": meas, "true": gt[obj], "err_mm": err,
            "rel_pct": 100 * abs(err) / gt[obj],
        })
    if not rows:
        sys.exit("No rows matched ground truth objects.")

    rels = sorted(x["rel_pct"] for x in rows)
    med = st.median(rels)
    p95 = rels[min(len(rels) - 1, int(0.95 * len(rels)))]

    with open(out_md, "w") as f:
        f.write("# Planar measurement error report\n\n")
        f.write("| image | object | dist | angle | light | measured mm |"
                " true mm | err mm | rel % |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for x in rows:
            f.write(f"| {x['image']} | {x['object']} | {x['dist']} |"
                    f" {x['angle']} | {x['light']} | {x['meas']:.3f} |"
                    f" {x['true']:.3f} | {x['err_mm']:+.3f} |"
                    f" {x['rel_pct']:.3f} |\n")
        f.write(f"\nn={len(rows)}  median rel err={med:.3f}%  p95={p95:.3f}%\n\n")
        verdict = "PASS" if med <= 2.0 and p95 <= 4.0 else "FAIL"
        f.write("Acceptance (median<=2%, p95<=4% within the controlled"
                f" envelope): **{verdict}**\n")
    print(f"median {med:.3f}%  p95 {p95:.3f}%  -> {out_md}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
