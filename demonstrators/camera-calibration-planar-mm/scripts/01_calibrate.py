#!/usr/bin/env python3
"""Camera calibration from chessboard images.

Usage: 01_calibrate.py <calib_dir> <out_dir> [--square-mm 25.0]

Acceptance: >= 10 usable views (aim 15-20), RMS reprojection <= 0.5 px.
"""
import argparse
import glob
import json
import sys

import cv2
import numpy as np

PATTERN = (9, 6)  # inner corners of a 10x7-square board


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("calib_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--square-mm", type=float, default=25.0,
                    help="measured square size after printing (mm)")
    args = ap.parse_args()

    objp = np.zeros((PATTERN[0] * PATTERN[1], 3), np.float32)
    objp[:, :2] = (np.mgrid[0:PATTERN[0], 0:PATTERN[1]]
                   .T.reshape(-1, 2) * args.square_mm)

    objpoints, imgpoints, used = [], [], []
    size = None
    files = sorted(glob.glob(f"{args.calib_dir}/*.jpg")
                   + glob.glob(f"{args.calib_dir}/*.png"))
    for f in files:
        img = cv2.imread(f)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        size = gray.shape[::-1]
        ok, corners = cv2.findChessboardCornersSB(gray, PATTERN)
        if not ok:
            print(f"REJECT {f}")
            continue
        objpoints.append(objp)
        imgpoints.append(corners)
        used.append(f)
        print(f"OK     {f}")

    if len(used) < 10:
        sys.exit(f"Only {len(used)} usable views; need >= 10 (aim 15-20).")

    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, size, None, None)

    per_view = {}
    for i, name in enumerate(used):
        proj, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], K, dist)
        d = imgpoints[i].reshape(-1, 2) - proj.reshape(-1, 2)
        per_view[name] = float(np.sqrt(np.mean(np.sum(d * d, axis=1))))

    np.savez(f"{args.out_dir}/camera.npz", K=K, dist=dist, size=size)
    report = {
        "rms_px": float(rms),
        "views": len(used),
        "square_mm": args.square_mm,
        "K": K.tolist(),
        "dist": dist.ravel().tolist(),
        "image_size": list(size),
        "per_view_px": per_view,
    }
    with open(f"{args.out_dir}/calibration_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"RMS reprojection: {rms:.4f} px over {len(used)} views")
    print(f"fx={K[0,0]:.2f} fy={K[1,1]:.2f} cx={K[0,2]:.2f} cy={K[1,2]:.2f}")
    print(f"dist={np.round(dist.ravel(), 5).tolist()}")
    if rms > 0.5:
        print("WARNING: RMS > 0.5 px acceptance threshold - reshoot calibration set.")


if __name__ == "__main__":
    main()
