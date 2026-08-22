#!/usr/bin/env python3
"""Deterministic stratified split + hashed manifest.

Usage: 01_prepare_split.py <dataset_dir> <out_manifest.csv>
Split per class with seed 42: 70% train / 10% val / 20% test.
The manifest (path, label, split, bytes, sha256) is written BEFORE any
training and is the provenance anchor for every later metric.
"""
import csv, hashlib, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import LABELS

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main(root, out):
    rows = []
    for label in LABELS:
        files = sorted(f for f in os.listdir(os.path.join(root, label))
                       if f.lower().endswith((".jpg", ".jpeg", ".png")))
        rng = random.Random(42)
        rng.shuffle(files)
        n = len(files)
        n_train, n_val = int(0.7 * n), int(0.1 * n)
        for i, f in enumerate(files):
            split = "train" if i < n_train else "val" if i < n_train + n_val else "test"
            p = os.path.join(root, label, f)
            rows.append([f"{label}/{f}", label, split, os.path.getsize(p), sha256(p)])
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "label", "split", "bytes", "sha256"])
        w.writerows(rows)
    from collections import Counter
    c = Counter((r[1], r[2]) for r in rows)
    for label in LABELS:
        print(label, {s: c[(label, s)] for s in ("train", "val", "test")})
    print("total", len(rows), Counter(r[2] for r in rows))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
