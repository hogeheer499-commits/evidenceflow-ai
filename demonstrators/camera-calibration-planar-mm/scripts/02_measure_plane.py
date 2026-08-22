#!/usr/bin/env python3
"""Planar mm measurement via chessboard homography.

The reference object must lie in the same plane as the board.

Interactive (physical run):
    02_measure_plane.py out/camera.npz meas/photo.jpg results.csv
    -> click 2 points on the reference object (q aborts)

Non-interactive (automation / synthetic self-test):
    ... --points x1 y1 x2 y2      measure between explicit pixel coords
    ... --auto-red-dots           auto-detect two red dot centroids
Pixel coordinates refer to the UNDISTORTED image.
"""
import argparse
import csv
import os
import sys

import cv2
import numpy as np

PATTERN = (9, 6)


def find_red_dots(und: np.ndarray) -> list[tuple[float, float]]:
    b, g, r = cv2.split(und.astype(np.int16))
    mask = ((r > 150) & (g < 100) & (b < 100)).astype(np.uint8)
    n, _, stats, cents = cv2.connectedComponentsWithStats(mask)
    blobs = sorted(
        ((stats[i, cv2.CC_STAT_AREA], tuple(cents[i])) for i in range(1, n)),
        reverse=True)
    if len(blobs) < 2:
        sys.exit("auto-red-dots: fewer than 2 red blobs found.")
    return [blobs[0][1], blobs[1][1]]


def click_points(und: np.ndarray) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []

    def cb(ev, x, y, flags, param):
        if ev == cv2.EVENT_LBUTTONDOWN:
            pts.append((float(x), float(y)))
            cv2.circle(und, (x, y), 4, (0, 0, 255), -1)
            cv2.imshow("measure", und)

    cv2.imshow("measure", und)
    cv2.setMouseCallback("measure", cb)
    while len(pts) < 2:
        if cv2.waitKey(20) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()
    if len(pts) != 2:
        sys.exit("Need exactly 2 clicked points.")
    return pts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("camera_npz")
    ap.add_argument("image")
    ap.add_argument("out_csv")
    ap.add_argument("--square-mm", type=float, default=25.0)
    ap.add_argument("--points", nargs=4, type=float, metavar=("X1", "Y1", "X2", "Y2"))
    ap.add_argument("--auto-red-dots", action="store_true")
    args = ap.parse_args()

    cal = np.load(args.camera_npz)
    K, dist = cal["K"], cal["dist"]
    img = cv2.imread(args.image)
    und = cv2.undistort(img, K, dist)

    gray = cv2.cvtColor(und, cv2.COLOR_BGR2GRAY)
    ok, corners = cv2.findChessboardCornersSB(gray, PATTERN)
    if not ok:
        sys.exit("Board not found in measurement image - reshoot "
                 "(this is a valid negative: log it in the README).")

    board_mm = (np.mgrid[0:PATTERN[0], 0:PATTERN[1]]
                .T.reshape(-1, 2).astype(np.float32) * args.square_mm)
    H, _ = cv2.findHomography(corners.reshape(-1, 2), board_mm, cv2.RANSAC)

    if args.points:
        pts = [(args.points[0], args.points[1]), (args.points[2], args.points[3])]
    elif args.auto_red_dots:
        pts = find_red_dots(und)
    else:
        pts = click_points(und)

    p = cv2.perspectiveTransform(np.array([pts], np.float32), H)[0]
    mm = float(np.linalg.norm(p[0] - p[1]))

    name = os.path.basename(args.image)
    new = not os.path.exists(args.out_csv)
    with open(args.out_csv, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["image", "px1", "px2", "measured_mm"])
        w.writerow([name, pts[0], pts[1], f"{mm:.3f}"])
    print(f"{name}: {mm:.3f} mm")


if __name__ == "__main__":
    main()
