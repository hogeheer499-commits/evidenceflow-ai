#!/usr/bin/env python3
"""Synthetic ground-truth generator for the calibration/measurement self-test.

Renders a 10x7-square chessboard (9x6 inner corners, 25.0 mm squares) as
seen by a SIMULATED camera with KNOWN intrinsics and lens distortion:

    fx = fy = 1100 px, cx = 640, cy = 480, image 1280x960
    dist = [k1=-0.12, k2=0.03, p1=0.0005, p2=-0.0004, k3=0.0]

Pipeline per view: board plane (mm) -> H = K [r1 r2 t] -> undistorted
render (warpPerspective from an 8 px/mm canvas) -> lens distortion applied
by remap (dst distorted pixel samples src at its undistorted position via
cv2.undistortPoints) -> mild blur + sensor noise.

Measurement scenes additionally contain two red dots in the board plane
with an exact centre distance of 60.000 mm ("synthdots" ground truth).

This validates the measurement-chain IMPLEMENTATION. It is not physical
metrology: no real camera, lens, print, or caliper is involved.
"""
import math
import os
import sys

import cv2
import numpy as np

SQUARE_MM = 25.0
SQUARES = (10, 7)              # full squares (x, y)
IMG_SIZE = (1280, 960)
K_TRUE = np.array([[1100.0, 0, 640.0],
                   [0, 1100.0, 480.0],
                   [0, 0, 1.0]])
DIST_TRUE = np.array([-0.12, 0.03, 0.0005, -0.0004, 0.0])
S = 8                          # canvas px per mm
MARGIN_MM = 40.0
DOT_GAP_MM = 60.0              # exact ground truth distance
RNG_SEED = 42


def make_canvas(with_dots: bool) -> tuple[np.ndarray, float]:
    """Return (canvas BGR, canvas width mm). Origin of mm frame = canvas (0,0)."""
    obj_zone = 100.0 if with_dots else 0.0
    w_mm = MARGIN_MM * 2 + SQUARES[0] * SQUARE_MM + obj_zone
    h_mm = MARGIN_MM * 2 + SQUARES[1] * SQUARE_MM
    canvas = np.full((int(h_mm * S), int(w_mm * S), 3), 255, np.uint8)
    for iy in range(SQUARES[1]):
        for ix in range(SQUARES[0]):
            if (ix + iy) % 2 == 0:
                x0 = int((MARGIN_MM + ix * SQUARE_MM) * S)
                y0 = int((MARGIN_MM + iy * SQUARE_MM) * S)
                x1 = int((MARGIN_MM + (ix + 1) * SQUARE_MM) * S)
                y1 = int((MARGIN_MM + (iy + 1) * SQUARE_MM) * S)
                canvas[y0:y1, x0:x1] = 0
    if with_dots:
        dot_x = MARGIN_MM + SQUARES[0] * SQUARE_MM + 50.0
        y_mid = h_mm / 2
        for dy in (-DOT_GAP_MM / 2, DOT_GAP_MM / 2):
            c = (int(dot_x * S), int((y_mid + dy) * S))
            cv2.circle(canvas, c, int(2.0 * S), (0, 0, 255), -1, cv2.LINE_AA)
    return canvas, w_mm


def distortion_maps() -> tuple[np.ndarray, np.ndarray]:
    """For each distorted output pixel, the undistorted source coordinate."""
    w, h = IMG_SIZE
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32),
                         np.arange(h, dtype=np.float32))
    pts = np.stack([xs.ravel(), ys.ravel()], axis=1).reshape(-1, 1, 2)
    und = cv2.undistortPoints(pts, K_TRUE, DIST_TRUE, P=K_TRUE).reshape(h, w, 2)
    return und[..., 0], und[..., 1]


def render(canvas: np.ndarray, w_mm: float, rx: float, ry: float, rz: float,
           dist_mm: float, map_x: np.ndarray, map_y: np.ndarray,
           rng: np.random.Generator) -> np.ndarray:
    h_mm = canvas.shape[0] / S
    R, _ = cv2.Rodrigues(np.array([math.radians(rx), math.radians(ry),
                                   math.radians(rz)]))
    centre = np.array([w_mm / 2, h_mm / 2, 0.0])
    t = np.array([0.0, 0.0, dist_mm]) - R @ centre
    H_mm = K_TRUE @ np.column_stack([R[:, 0], R[:, 1], t])
    H_canvas = H_mm @ np.diag([1.0 / S, 1.0 / S, 1.0])
    und = cv2.warpPerspective(canvas, H_canvas, IMG_SIZE,
                              flags=cv2.INTER_AREA,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(128, 128, 128))
    distorted = cv2.remap(und, map_x, map_y, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT,
                          borderValue=(128, 128, 128))
    distorted = cv2.GaussianBlur(distorted, (0, 0), 0.8)
    noise = rng.normal(0, 2.0, distorted.shape)
    return np.clip(distorted.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def main(out_root: str) -> None:
    rng = np.random.default_rng(RNG_SEED)
    map_x, map_y = distortion_maps()
    map_x = map_x.astype(np.float32)
    map_y = map_y.astype(np.float32)

    calib_canvas, w1 = make_canvas(with_dots=False)
    poses = [(0, 0, 0), (20, 0, 0), (-20, 0, 0), (0, 20, 0), (0, -20, 0),
             (20, 20, 5), (-20, 20, -5), (20, -20, 10), (-20, -20, -10),
             (30, 0, 15), (0, 30, -15), (-30, 10, 0), (10, -30, 0),
             (25, 15, 30), (-15, 25, -30), (0, 0, 45)]
    dists = [500, 600, 700]
    for i, (rx, ry, rz) in enumerate(poses):
        img = render(calib_canvas, w1, rx, ry, rz, dists[i % 3],
                     map_x, map_y, rng)
        cv2.imwrite(f"{out_root}/calib/calib_{i:02d}.png", img)
    print(f"calibration views: {len(poses)}")

    meas_canvas, w2 = make_canvas(with_dots=True)
    meas_poses = [(0, 0, 0), (15, 0, 0), (0, 15, 0),
                  (30, 0, 0), (0, 30, 0), (15, 15, 0)]
    n = 0
    for d in (500, 700):
        for r, (rx, ry, rz) in enumerate(meas_poses, start=1):
            a = max(abs(rx), abs(ry))
            img = render(meas_canvas, w2, rx, ry, rz, d, map_x, map_y, rng)
            name = f"d{d}_a{a:02d}_synth_r{r}_synthdots.png"
            cv2.imwrite(f"{out_root}/meas/{name}", img)
            n += 1
    print(f"measurement views: {n}")
    print("TRUE fx=fy=1100.0 cx=640.0 cy=480.0 dist="
          + str(DIST_TRUE.tolist()))
    print(f"TRUE dot distance: {DOT_GAP_MM:.3f} mm")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__) + "/../synth")
