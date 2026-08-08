#!/usr/bin/env python3
"""Fit an editable continuous cubic candidate to an accepted contour."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import cv2
import numpy as np
from scipy.interpolate import splprep, splev
from scipy.spatial import cKDTree


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def resample(points: np.ndarray, count: int, closed: bool) -> np.ndarray:
    source = points
    if closed:
        if np.linalg.norm(source[0] - source[-1]) > 1e-9:
            source = np.vstack((source, source[0]))
    lengths = np.linalg.norm(np.diff(source, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    if cumulative[-1] <= 0:
        fail("contour has zero length")
    targets = np.linspace(0.0, cumulative[-1], count, endpoint=not closed)
    x = np.interp(targets, cumulative, source[:, 0])
    y = np.interp(targets, cumulative, source[:, 1])
    return np.column_stack((x, y))


def fit_arc(points: np.ndarray, smoothing: float, segments: int, periodic: bool) -> list[np.ndarray]:
    if len(points) < 4:
        fail("each fitted arc needs at least four samples")
    weights = np.ones(len(points), dtype=np.float64)
    if not periodic:
        weights[0] = weights[-1] = 1000.0
    degree = min(3, len(points) - 1)
    try:
        tck, _ = splprep(
            [points[:, 0], points[:, 1]],
            w=weights,
            s=smoothing,
            per=periodic,
            k=degree,
        )
    except (TypeError, ValueError) as error:
        fail(f"spline fit failed: {error}")

    boundaries = np.linspace(0.0, 1.0, segments + 1)
    curves: list[np.ndarray] = []
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        delta = end - start
        p0 = np.asarray(splev(start, tck, der=0), dtype=np.float64)
        p3 = np.asarray(splev(end, tck, der=0), dtype=np.float64)
        d0 = np.asarray(splev(start, tck, der=1), dtype=np.float64)
        d1 = np.asarray(splev(end, tck, der=1), dtype=np.float64)
        curves.append(np.vstack((p0, p0 + d0 * delta / 3.0, p3 - d1 * delta / 3.0, p3)))
    if not periodic:
        curves[0][0] = points[0]
        curves[-1][3] = points[-1]
    return curves


def split_at_corners(points: np.ndarray, corners: np.ndarray) -> list[np.ndarray]:
    open_points = points[:-1] if np.linalg.norm(points[0] - points[-1]) < 1e-6 else points
    indices = sorted({int(np.argmin(np.linalg.norm(open_points - corner, axis=1))) for corner in corners})
    if len(indices) != len(corners):
        fail("two declared corners resolved to the same contour location")
    arcs = []
    for position, start in enumerate(indices):
        end = indices[(position + 1) % len(indices)]
        if end > start:
            arc = open_points[start : end + 1]
        else:
            arc = np.vstack((open_points[start:], open_points[: end + 1]))
        arc = arc.copy()
        arc[0] = open_points[start]
        arc[-1] = open_points[end]
        arcs.append(arc)
    return arcs


def allocate_segments(arcs: list[np.ndarray], total: int) -> list[int]:
    if total < len(arcs):
        fail("segments must be at least the number of intentional-corner arcs")
    lengths = np.array([float(np.sum(np.linalg.norm(np.diff(arc, axis=0), axis=1))) for arc in arcs])
    allocation = np.ones(len(arcs), dtype=np.int32)
    remaining = total - len(arcs)
    if remaining:
        ideal = remaining * lengths / np.sum(lengths)
        extra = np.floor(ideal).astype(np.int32)
        allocation += extra
        for index in np.argsort(-(ideal - extra))[: remaining - int(np.sum(extra))]:
            allocation[index] += 1
    return allocation.tolist()


def sample_curves(curves: list[np.ndarray], samples_per_curve: int = 64) -> np.ndarray:
    samples = []
    for index, curve in enumerate(curves):
        t = np.linspace(0.0, 1.0, samples_per_curve, endpoint=index == len(curves) - 1)
        u = 1.0 - t
        samples.append(
            (u**3)[:, None] * curve[0]
            + (3 * u * u * t)[:, None] * curve[1]
            + (3 * u * t * t)[:, None] * curve[2]
            + (t**3)[:, None] * curve[3]
        )
    return np.vstack(samples)


def path_data(curves: list[np.ndarray]) -> str:
    commands = [f"M {fmt(curves[0][0, 0])} {fmt(curves[0][0, 1])}"]
    for curve in curves:
        commands.append("C " + " ".join(fmt(value) for point in curve[1:] for value in point))
    commands.append("Z")
    return " ".join(commands)


def join_metrics(curves: list[np.ndarray], intentional: set[int]) -> list[dict[str, object]]:
    records = []
    for index, curve in enumerate(curves):
        following = curves[(index + 1) % len(curves)]
        incoming = curve[3] - curve[2]
        outgoing = following[1] - following[0]
        denominator = float(np.linalg.norm(incoming) * np.linalg.norm(outgoing))
        angle = None
        if denominator > 1e-12:
            cosine = float(np.dot(incoming, outgoing) / denominator)
            angle = round(math.degrees(math.acos(np.clip(cosine, -1.0, 1.0))), 4)
        records.append(
            {
                "anchor": [round(float(value), 3) for value in curve[3]],
                "tangent_angle_deg": angle,
                "intentional_corner": index in intentional,
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("contour_json")
    parser.add_argument("output_dir")
    parser.add_argument("name")
    parser.add_argument("--smoothing", type=float, required=True)
    parser.add_argument("--segments", type=int, required=True)
    parser.add_argument("--fit-samples", type=int, required=True)
    parser.add_argument("--corners", help="optional JSON file containing {'corners': [[x,y], ...]}")
    parser.add_argument("--fill", default="#000000")
    parser.add_argument("--source", help="optional source image for control overlay")
    args = parser.parse_args()

    if args.smoothing < 0:
        fail("smoothing must not be negative")
    if args.segments < 2:
        fail("segments must be at least 2")
    if args.fit_samples < max(16, args.segments * 2):
        fail("fit-samples must provide at least two samples per segment and at least 16 samples")

    try:
        record = json.loads(Path(args.contour_json).read_text())
        points = np.asarray(record["points"], dtype=np.float64)
        width, height = map(int, record["source_size"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        fail(f"cannot read contour record: {error}")
    if not bool(record.get("closed")):
        fail("fit_contour currently requires an accepted closed contour")
    if len(points) < 8:
        fail("contour has too few points")

    sampled_contour = resample(points, args.fit_samples, closed=True)
    corners = np.empty((0, 2), dtype=np.float64)
    if args.corners:
        try:
            corners = np.asarray(json.loads(Path(args.corners).read_text())["corners"], dtype=np.float64)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            fail(f"cannot read corners: {error}")
        if corners.ndim != 2 or corners.shape[1] != 2 or len(corners) < 2:
            fail("corners must contain at least two [x,y] points")

    intentional_join_indices: set[int] = set()
    if len(corners):
        arcs = split_at_corners(sampled_contour, corners)
        allocations = allocate_segments(arcs, args.segments)
        lengths = np.array([float(np.sum(np.linalg.norm(np.diff(arc, axis=0), axis=1))) for arc in arcs])
        curves = []
        for arc, count, length in zip(arcs, allocations, lengths):
            arc_samples = max(8, int(round(args.fit_samples * length / np.sum(lengths))))
            prepared = resample(arc, arc_samples, closed=False)
            curves.extend(fit_arc(prepared, args.smoothing * length / np.sum(lengths), count, periodic=False))
            intentional_join_indices.add(len(curves) - 1)
    else:
        curves = fit_arc(sampled_contour, args.smoothing, args.segments, periodic=True)

    fitted = sample_curves(curves)
    contour_tree, fitted_tree = cKDTree(sampled_contour), cKDTree(fitted)
    contour_to_fit = fitted_tree.query(sampled_contour, k=1)[0]
    fit_to_contour = contour_tree.query(fitted, k=1)[0]
    distances = np.concatenate((contour_to_fit, fit_to_contour))

    joins = join_metrics(curves, intentional_join_indices)
    ordinary_angles = [
        item["tangent_angle_deg"]
        for item in joins
        if not item["intentional_corner"] and item["tangent_angle_deg"] is not None
    ]
    metrics = {
        "name": args.name,
        "source_contour": str(Path(args.contour_json)),
        "source_size": [width, height],
        "fit_method": "parametric-smoothing-spline-to-cubic-hermite",
        "parameters": {
            "smoothing": args.smoothing,
            "segments": args.segments,
            "fit_samples": args.fit_samples,
            "corners": corners.tolist(),
        },
        "curve_segments": len(curves),
        "anchor_count": len(curves),
        "symmetric_contour_distance_px": {
            "mean": round(float(np.mean(distances)), 4),
            "p95": round(float(np.percentile(distances, 95)), 4),
            "maximum": round(float(np.max(distances)), 4),
        },
        "ordinary_join_tangent_angle_deg": {
            "median": round(float(np.median(ordinary_angles)), 4) if ordinary_angles else None,
            "maximum": round(float(np.max(ordinary_angles)), 4) if ordinary_angles else None,
        },
        "joins": joins,
    }

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n  <path d="{path_data(curves)}" fill="{args.fill}"/>\n</svg>\n'''
    (output / f"{args.name}.svg").write_text(svg)
    (output / f"{args.name}.metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

    if args.source:
        overlay = cv2.imread(args.source, cv2.IMREAD_COLOR)
        if overlay is None or overlay.shape[:2] != (height, width):
            fail("--source must be a readable image matching the contour dimensions")
    else:
        overlay = np.full((height, width, 3), 242, dtype=np.uint8)
    original = np.rint(sampled_contour).astype(np.int32)
    rendered = np.rint(fitted).astype(np.int32)
    cv2.polylines(overlay, [original], True, (70, 200, 70), 1, cv2.LINE_AA)
    cv2.polylines(overlay, [rendered], True, (210, 60, 225), 2, cv2.LINE_AA)
    for curve in curves:
        control = np.rint(curve).astype(np.int32)
        cv2.line(overlay, tuple(control[0]), tuple(control[1]), (210, 190, 70), 1, cv2.LINE_AA)
        cv2.line(overlay, tuple(control[3]), tuple(control[2]), (210, 190, 70), 1, cv2.LINE_AA)
        cv2.circle(overlay, tuple(control[0]), 3, (20, 220, 255), -1, cv2.LINE_AA)
    cv2.imwrite(str(output / f"{args.name}.control-overlay.png"), overlay)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
