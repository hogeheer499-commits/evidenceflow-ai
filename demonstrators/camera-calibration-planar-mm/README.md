# Camera Calibration + Planar mm Measurement Demonstrator

First-party run on the maintainer's Beelink GTR9 Pro, 2026-08-16.

## What this campaign contains

A complete, executable image-to-physical-measurement chain — camera
calibration, distortion correction, chessboard-plane homography, and
pixel-to-millimetre distance measurement with an error report — plus an
**end-to-end synthetic self-test with known ground truth** that validates
the implementation before any physical acquisition.

## Claim boundary (read first)

The synthetic self-test proves that the measurement-chain
**implementation** is correct: a simulated camera with known intrinsics
and lens distortion was recovered by the calibration script, and a known
60.000 mm distance was recovered through the full distorted-image →
undistort → board-homography → mm pipeline within 0.28% worst-case error.

It is **not physical metrology**: no real camera, lens, print, or caliper
was involved. It is also **not** evidence of measurement from
uncontrolled consumer photos, non-planar parts, or per-part-type
tolerances — that is the open question for any real repair or inspection use. The
physical acquisition protocol below is the remaining step to turn this
into a physical demonstrator; its acceptance criteria are pre-registered
here, before any physical measurement has been taken.

## Synthetic self-test results (measured, this campaign)

Ground truth (constructed, `scripts/synth_generate.py`, seed 42):

- Simulated camera: fx = fy = 1100.0, cx = 640.0, cy = 480.0,
  image 1280x960, dist = [k1 -0.12, k2 0.03, p1 0.0005, p2 -0.0004, k3 0].
- Board: 10x7 squares (9x6 inner corners), 25.0 mm squares.
- Reference: two red dots in the board plane, centre distance
  exactly 60.000 mm.
- 16 calibration views (rotations up to ±30-45°, distances 500-700 mm),
  12 measurement scenes (distances 500/700 mm, angles 0/15/30°),
  rendered with lens distortion, blur and sensor noise.

Recovered by the real scripts (`out/calibration_report.json`,
`results.csv`, `report.md`):

- Calibration: 16/16 views detected, RMS reprojection **0.154 px**;
  fx 1098.30 / fy 1098.48 (0.16% from truth), cx 640.80 / cy 479.95
  (< 1 px from truth); k1 -0.132 (truth -0.12). Higher-order
  coefficients (k2, k3) trade off against each other, as expected with
  limited field-of-view coverage — the compound distortion model still
  reproduces the projections at 0.154 px RMS.
- Measurement: 12/12 scenes, all values between 59.977 and 60.167 mm;
  **median relative error 0.078%, p95 0.278%, max absolute error
  +0.167 mm on 60 mm**. Acceptance verdict in `report.md`: PASS
  (pre-set thresholds median <= 2%, p95 <= 4%).
- Determinism: a full rerun of all 12 measurements produced
  byte-identical values (`results-repeat.csv` vs `results.csv`).

## Files

- `scripts/synth_generate.py` — synthetic ground-truth generator
  (documents the exact simulated camera and scene).
- `scripts/01_calibrate.py` — chessboard calibration, per-view RMS,
  JSON report. Acceptance: >= 10 views, RMS <= 0.5 px.
- `scripts/02_measure_plane.py` — planar mm measurement via board
  homography; interactive clicks for physical use, `--auto-red-dots` /
  `--points` for automation.
- `scripts/03_report.py` — error table, median/p95, PASS/FAIL verdict.
- `synth/calib/` (16 images), `synth/meas/` (12 images) — the synthetic
  dataset.
- `out/camera.npz`, `out/calibration_report.json` — recovered camera.
- `results.csv`, `results-repeat.csv`, `ground_truth.csv`, `report.md`.
- `versions.txt` — Python 3.12.3, opencv-python-headless 5.0.0,
  numpy 2.5.2, Linux 7.0.0-28-generic.
- `manifest.sha256` — SHA-256 of every file above.

## Exact commands

```bash
python3 -m venv .venv && .venv/bin/pip install opencv-python-headless numpy
.venv/bin/python scripts/synth_generate.py synth
.venv/bin/python scripts/01_calibrate.py synth/calib out
for f in synth/meas/*.png; do
  .venv/bin/python scripts/02_measure_plane.py out/camera.npz "$f" results.csv --auto-red-dots
done
.venv/bin/python scripts/03_report.py results.csv ground_truth.csv report.md
```

## Pre-registered physical protocol (remaining human step)

1. Print the 10x7 chessboard (25.0 mm squares) on rigid backing;
   **measure the true square size with a caliper over 8 squares / 8**
   and pass it as `--square-mm`.
2. Phase A: 15-20 calibration photos (fixed zoom/focus, no HDR/beautify),
   board filling the frame at varied tilts up to ±40° and positions.
3. Phase B: board flat on a table, reference objects (each caliper-measured
   3x, median as ground truth) **in the same plane**; matrix of
   3 distances x 3 angles x 2 lighting conditions x >= 2 placements.
   File naming `d<cm>_a<deg>_<light>_r<n>_<object>.jpg`.
4. Phase C: run the same three scripts; clicks happen on the undistorted
   image.
5. Pre-registered acceptance (set before any physical measurement):
   calibration RMS <= 0.5 px over >= 15 views; median relative error
   <= 2% and p95 <= 4% within the controlled envelope (30-60 cm,
   <= 30°); all board-not-found and out-of-tolerance shots stay in the
   report as negatives; uncertainty budget table filled in (print scale,
   corner detection, click precision, plane alignment, distortion
   residual, caliper).

This is a functionality and implementation-correctness check of a
calibrated measurement chain on a plane, not a claim of industrial
metrology or of measurement from uncontrolled consumer imagery.
