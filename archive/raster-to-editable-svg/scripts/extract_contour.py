#!/usr/bin/env python3
"""Extract an inspectable subpixel contour from a chosen mask or soft field."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from skimage.measure import find_contours


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def polygon_area(points: np.ndarray) -> float:
    x, y = points[:, 0], points[:, 1]
    return 0.5 * float(np.sum((x * np.roll(y, -1)) - (y * np.roll(x, -1))))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("field", help="grayscale mask, confidence image, or soft field")
    parser.add_argument("output_dir")
    parser.add_argument("name")
    parser.add_argument("--method", choices=("marching-squares", "opencv"), required=True)
    parser.add_argument("--level", type=float, required=True, help="iso-level in the normalized 0..1 field")
    parser.add_argument("--smoothing-sigma", type=float, required=True, help="source-pixel Gaussian sigma")
    parser.add_argument("--subpixel-scale", type=int, required=True)
    parser.add_argument("--source", help="optional same-size source image for overlay")
    args = parser.parse_args()

    if not 0.0 < args.level < 1.0:
        fail("level must be between 0 and 1")
    if args.smoothing_sigma < 0:
        fail("smoothing-sigma must not be negative")
    if args.subpixel_scale < 1:
        fail("subpixel-scale must be at least 1")

    raw = cv2.imread(args.field, cv2.IMREAD_GRAYSCALE)
    if raw is None:
        fail(f"cannot read field: {args.field}")
    height, width = raw.shape
    working = raw.astype(np.float32) / 255.0
    if args.subpixel_scale != 1:
        working = cv2.resize(
            working,
            None,
            fx=args.subpixel_scale,
            fy=args.subpixel_scale,
            interpolation=cv2.INTER_CUBIC,
        )
    if args.smoothing_sigma > 0:
        sigma = args.smoothing_sigma * args.subpixel_scale
        working = cv2.GaussianBlur(working, (0, 0), sigmaX=sigma, sigmaY=sigma)

    if args.method == "marching-squares":
        candidates = [
            np.column_stack((contour[:, 1], contour[:, 0])) / float(args.subpixel_scale)
            for contour in find_contours(working, args.level)
        ]
    else:
        binary = np.where(working >= args.level, 255, 0).astype(np.uint8)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        candidates = [
            contour.reshape(-1, 2).astype(np.float64) / float(args.subpixel_scale)
            for contour in contours
        ]
    candidates = [candidate for candidate in candidates if len(candidate) >= 4]
    if not candidates:
        fail("no contour found at the chosen level")

    contour = max(candidates, key=lambda candidate: abs(polygon_area(candidate)))
    closed_gap = float(np.linalg.norm(contour[0] - contour[-1]))
    closed = closed_gap <= max(1.5 / args.subpixel_scale, 0.25)
    if closed and not np.allclose(contour[0], contour[-1]):
        contour = np.vstack((contour, contour[0]))

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    npy_path = output / f"{args.name}.contour.npy"
    np.save(npy_path, contour)

    record = {
        "name": args.name,
        "source_size": [width, height],
        "field": str(Path(args.field)),
        "method": args.method,
        "parameters": {
            "level": args.level,
            "smoothing_sigma_px": args.smoothing_sigma,
            "subpixel_scale": args.subpixel_scale,
        },
        "point_count": int(len(contour)),
        "closed": closed,
        "closure_gap_px": round(closed_gap, 4),
        "signed_area_px2": round(polygon_area(contour), 3),
        "contour_npy": str(npy_path),
        "points": [[round(float(x), 4), round(float(y), 4)] for x, y in contour],
    }
    json_path = output / f"{args.name}.contour.json"
    json_path.write_text(json.dumps(record, indent=2) + "\n")

    field_view = cv2.resize(working, (width, height), interpolation=cv2.INTER_AREA)
    field_u8 = np.clip(field_view * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(str(output / f"{args.name}.field-heatmap.png"), cv2.applyColorMap(field_u8, cv2.COLORMAP_VIRIDIS))

    if args.source:
        overlay = cv2.imread(args.source, cv2.IMREAD_COLOR)
        if overlay is None or overlay.shape[:2] != (height, width):
            fail("--source must be a readable image matching the field dimensions")
    else:
        overlay = np.full((height, width, 3), 242, dtype=np.uint8)
    drawn = np.rint(contour).astype(np.int32)
    cv2.polylines(overlay, [drawn], closed, (215, 55, 225), 2, cv2.LINE_AA)
    cv2.imwrite(str(output / f"{args.name}.contour-overlay.png"), overlay)

    print(json.dumps({key: value for key, value in record.items() if key != "points"}, indent=2))


if __name__ == "__main__":
    main()
