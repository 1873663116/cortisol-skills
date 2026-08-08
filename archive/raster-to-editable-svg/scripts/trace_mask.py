#!/usr/bin/env python3
"""Fit curvature-aware cubic Bézier segments to a mask and emit local evidence."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import cv2
import numpy as np


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def chord_parameters(points: np.ndarray) -> np.ndarray:
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    total = float(np.sum(lengths))
    if total == 0:
        return np.linspace(0.0, 1.0, len(points))
    return np.concatenate(([0.0], np.cumsum(lengths) / total))


def evaluate(curve: np.ndarray, t: np.ndarray) -> np.ndarray:
    u = 1.0 - t
    return (
        (u**3)[:, None] * curve[0]
        + (3 * u * u * t)[:, None] * curve[1]
        + (3 * u * t * t)[:, None] * curve[2]
        + (t**3)[:, None] * curve[3]
    )


def line_curve(points: np.ndarray) -> np.ndarray:
    p0, p3 = points[0], points[-1]
    delta = (p3 - p0) / 3.0
    return np.vstack((p0, p0 + delta, p0 + (2 * delta), p3))


def fit_once(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit both control points by least squares for local silhouette accuracy."""
    p0, p3 = points[0], points[-1]
    t = chord_parameters(points)
    u = 1.0 - t
    a1 = 3 * u * u * t
    a2 = 3 * u * t * t
    rhs = points - (u**3)[:, None] * p0 - (t**3)[:, None] * p3
    matrix = np.column_stack((a1, a2))
    controls = np.zeros((2, 2), dtype=np.float64)
    for axis in range(2):
        controls[:, axis], *_ = np.linalg.lstsq(matrix, rhs[:, axis], rcond=None)
    curve = np.vstack((p0, controls[0], controls[1], p3))
    errors = np.linalg.norm(evaluate(curve, t) - points, axis=1)
    return curve, errors


def curvature_split(points: np.ndarray) -> int:
    """Choose a meaningful tangent-change landmark, falling back to arc midpoint."""
    count = len(points)
    margin = max(2, min(12, count // 8))
    if count > (margin * 2) + 2:
        before = points[margin:-margin] - points[:-2 * margin]
        after = points[2 * margin:] - points[margin:-margin]
        before_length = np.linalg.norm(before, axis=1)
        after_length = np.linalg.norm(after, axis=1)
        valid = (before_length > 1e-6) & (after_length > 1e-6)
        cosine = np.ones(len(before), dtype=np.float64)
        cosine[valid] = np.sum(before[valid] * after[valid], axis=1) / (
            before_length[valid] * after_length[valid]
        )
        angles = np.arccos(np.clip(cosine, -1.0, 1.0))
        positions = np.arange(margin, count - margin)
        balance = np.minimum(positions, count - 1 - positions) / max(1, count / 2)
        scores = angles * np.sqrt(np.clip(balance, 0.0, 1.0))
        if float(np.max(scores)) > math.radians(0.75):
            return int(positions[int(np.argmax(scores))])
    parameters = chord_parameters(points)
    return int(np.argmin(np.abs(parameters - 0.5)))


def eligible_splits(points: np.ndarray, minimum_spacing: float) -> np.ndarray:
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    indices = np.arange(2, len(points) - 2)
    if not len(indices):
        return indices
    total = float(cumulative[-1])
    return indices[(cumulative[indices] >= minimum_spacing) & ((total - cumulative[indices]) >= minimum_spacing)]


def allocate(total: int, left_count: int, right_count: int) -> tuple[int, int]:
    if total <= 2:
        return 1, 1
    ratio = left_count / max(1, left_count + right_count)
    left = min(total - 1, max(1, int(round(total * ratio))))
    return left, total - left


def fit_adaptive(
    points: np.ndarray,
    tolerance: float,
    minimum_segments: int,
    maximum_segments: int,
    minimum_anchor_spacing: float,
    depth: int = 0,
) -> list[np.ndarray]:
    if len(points) <= 3:
        return [line_curve(points)]
    curve, errors = fit_once(points)
    worst_index = int(np.argmax(errors))
    exceeds_tolerance = float(errors[worst_index]) > tolerance
    needs_detail = minimum_segments > 1
    if (not exceeds_tolerance and not needs_detail) or maximum_segments <= 1 or depth >= 28:
        return [curve]

    candidates = eligible_splits(points, minimum_anchor_spacing)
    if not len(candidates):
        return [curve]
    if exceeds_tolerance:
        split = int(candidates[int(np.argmax(errors[candidates]))])
    else:
        preferred = curvature_split(points)
        split = int(candidates[int(np.argmin(np.abs(candidates - preferred)))])
    required = max(2, minimum_segments)
    left_required, right_required = allocate(required, split + 1, len(points) - split)
    extra_budget = max(0, maximum_segments - required)
    left_extra, right_extra = (0, 0)
    if extra_budget:
        left_extra, right_extra = allocate(extra_budget + 2, split + 1, len(points) - split)
        left_extra -= 1
        right_extra -= 1
    left_budget = max(left_required, left_required + left_extra)
    right_budget = max(right_required, right_required + right_extra)

    left = fit_adaptive(
        points[: split + 1],
        tolerance,
        left_required,
        left_budget,
        minimum_anchor_spacing,
        depth + 1,
    )
    right = fit_adaptive(
        points[split:],
        tolerance,
        right_required,
        right_budget,
        minimum_anchor_spacing,
        depth + 1,
    )
    return left + right


def fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def path_data(curves: list[np.ndarray]) -> str:
    commands = [f"M {fmt(curves[0][0, 0])} {fmt(curves[0][0, 1])}"]
    for curve in curves:
        commands.append("C " + " ".join(fmt(v) for point in curve[1:] for v in point))
    commands.append("Z")
    return " ".join(commands)


def sample_curves(curves: list[np.ndarray], samples: int = 48) -> np.ndarray:
    result = []
    for index, curve in enumerate(curves):
        t = np.linspace(0.0, 1.0, samples, endpoint=index == len(curves) - 1)
        result.append(evaluate(curve, t))
    return np.vstack(result)


def edge(mask: np.ndarray) -> np.ndarray:
    eroded = cv2.erode(mask, np.ones((3, 3), np.uint8))
    return cv2.subtract(mask, eroded)


def extract_contour(mask: np.ndarray, smoothing_sigma: float, subpixel_scale: int) -> np.ndarray:
    working = mask.astype(np.float32) / 255.0
    if subpixel_scale != 1:
        working = cv2.resize(
            working,
            None,
            fx=subpixel_scale,
            fy=subpixel_scale,
            interpolation=cv2.INTER_CUBIC,
        )
    if smoothing_sigma > 0:
        working = cv2.GaussianBlur(
            working,
            (0, 0),
            sigmaX=smoothing_sigma * subpixel_scale,
            sigmaY=smoothing_sigma * subpixel_scale,
        )
    binary = np.where(working >= 0.5, 255, 0).astype(np.uint8)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        fail("mask has no contour after smoothing")
    contour = max(contours, key=cv2.contourArea).reshape(-1, 2).astype(np.float64)
    return contour / float(subpixel_scale)


def structure_metrics(curves: list[np.ndarray]) -> dict[str, object]:
    chords = np.array([float(np.linalg.norm(curve[3] - curve[0])) for curve in curves])
    joins = []
    for index, curve in enumerate(curves):
        following = curves[(index + 1) % len(curves)]
        incoming = curve[3] - curve[2]
        outgoing = following[1] - following[0]
        incoming_length = float(np.linalg.norm(incoming))
        outgoing_length = float(np.linalg.norm(outgoing))
        angle = None
        if incoming_length > 1e-9 and outgoing_length > 1e-9:
            cosine = float(np.dot(incoming, outgoing) / (incoming_length * outgoing_length))
            angle = round(math.degrees(math.acos(np.clip(cosine, -1.0, 1.0))), 3)
        joins.append(
            {
                "anchor": [round(float(value), 3) for value in curve[3]],
                "tangent_angle_deg": angle,
            }
        )
    valid_angles = [entry["tangent_angle_deg"] for entry in joins if entry["tangent_angle_deg"] is not None]
    return {
        "segment_chord_px": {
            "minimum": round(float(np.min(chords)), 3),
            "median": round(float(np.median(chords)), 3),
            "maximum": round(float(np.max(chords)), 3),
        },
        "join_tangent_angle_deg": {
            "median": round(float(np.median(valid_angles)), 3) if valid_angles else None,
            "maximum": round(float(np.max(valid_angles)), 3) if valid_angles else None,
            "joins": joins,
        },
    }


def local_error(points: np.ndarray, distance_map: np.ndarray, windows: int = 24) -> dict[str, float | int]:
    rounded = np.rint(points).astype(np.int32)
    rounded[:, 0] = np.clip(rounded[:, 0], 0, distance_map.shape[1] - 1)
    rounded[:, 1] = np.clip(rounded[:, 1], 0, distance_map.shape[0] - 1)
    distances = distance_map[rounded[:, 1], rounded[:, 0]]
    groups = np.array_split(distances, min(windows, len(distances)))
    means = np.array([float(np.mean(group)) for group in groups])
    p95s = np.array([float(np.percentile(group, 95)) for group in groups])
    worst = int(np.argmax(means))
    return {
        "window_count": len(groups),
        "worst_window_index": worst,
        "worst_window_mean_px": round(float(means[worst]), 4),
        "worst_window_p95_px": round(float(p95s[worst]), 4),
    }


def write_source_overlay(
    source_path: str, output_path: Path, mask: np.ndarray, curves: list[np.ndarray]
) -> None:
    source = cv2.imread(source_path, cv2.IMREAD_COLOR)
    if source is None or source.shape[:2] != mask.shape:
        fail("--source must be an image with the same dimensions as the mask")
    result = source.copy()
    source_edge = edge(mask) > 0
    result[source_edge] = (70, 210, 70)
    sampled = np.rint(sample_curves(curves, samples=96)).astype(np.int32)
    cv2.polylines(result, [sampled], True, (210, 60, 225), 2, cv2.LINE_AA)
    anchors = np.rint(np.array([curve[0] for curve in curves])).astype(np.int32)
    for x, y in anchors:
        cv2.circle(result, (int(x), int(y)), 4, (30, 220, 255), -1, cv2.LINE_AA)
        cv2.circle(result, (int(x), int(y)), 5, (40, 40, 40), 1, cv2.LINE_AA)
    cv2.imwrite(str(output_path), result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mask")
    parser.add_argument("output_dir")
    parser.add_argument("name")
    parser.add_argument("--tolerance", type=float, required=True)
    parser.add_argument("--min-segments", type=int, required=True)
    parser.add_argument("--max-segments", type=int, required=True)
    parser.add_argument("--min-anchor-spacing", type=float, required=True)
    parser.add_argument("--smoothing-sigma", type=float, required=True)
    parser.add_argument("--subpixel-scale", type=int, required=True)
    parser.add_argument("--fill", default="#000000")
    parser.add_argument("--source", help="optional source image for a contour-and-anchor overlay")
    args = parser.parse_args()
    if args.tolerance <= 0:
        fail("tolerance must be positive")
    if args.min_segments < 2:
        fail("min-segments must be at least 2 for a closed foreground shape")
    if args.max_segments < args.min_segments:
        fail("max-segments must be greater than or equal to min-segments")
    if args.min_anchor_spacing < 0:
        fail("min-anchor-spacing must not be negative")
    if args.smoothing_sigma < 0:
        fail("smoothing-sigma must not be negative")
    if args.subpixel_scale < 1:
        fail("subpixel-scale must be at least 1")

    mask = cv2.imread(args.mask, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        fail(f"cannot read mask: {args.mask}")
    mask = np.where(mask >= 128, 255, 0).astype(np.uint8)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    height, width = mask.shape
    if cv2.countNonZero(mask) == width * height:
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n  <path d="M 0 0 H {width} V {height} H 0 Z" fill="{args.fill}"/>\n</svg>\n'''
        (output / f"{args.name}.svg").write_text(svg)
        metrics = {
            "name": args.name,
            "source_size": [width, height],
            "fit": "exact_full_canvas",
            "curve_segments": 0,
            "anchor_count": 4,
            "line_segments": 4,
            "silhouette_iou": 1.0,
            "edge_mean_px": 0.0,
            "edge_p95_px": 0.0,
            "edge_p99_px": 0.0,
            "edge_max_px": 0.0,
            "fit_parameters": {
                "tolerance_px": args.tolerance,
                "minimum_segments": args.min_segments,
                "maximum_segments": args.max_segments,
                "minimum_anchor_spacing_px": args.min_anchor_spacing,
                "smoothing_sigma_px": args.smoothing_sigma,
                "subpixel_scale": args.subpixel_scale,
            },
        }
        (output / f"{args.name}.metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
        cv2.imwrite(str(output / f"{args.name}.difference.png"), np.full((height, width, 3), 205, dtype=np.uint8))
        cv2.imwrite(str(output / f"{args.name}.rasterized.png"), mask)
        print(json.dumps(metrics, indent=2))
        return
    contour = extract_contour(mask, args.smoothing_sigma, args.subpixel_scale)
    if len(contour) < 8:
        fail("contour has too few points")

    first = int(np.argmax(np.sum((contour - contour[0]) ** 2, axis=1)))
    second = int(np.argmax(np.sum((contour - contour[first]) ** 2, axis=1)))
    a, b = sorted((first, second))
    arc1 = contour[a : b + 1]
    arc2 = np.vstack((contour[b:], contour[: a + 1]))
    arc1_min, arc2_min = allocate(args.min_segments, len(arc1), len(arc2))
    arc1_max, arc2_max = allocate(args.max_segments, len(arc1), len(arc2))
    arc1_max, arc2_max = max(arc1_min, arc1_max), max(arc2_min, arc2_max)
    curves = fit_adaptive(
        arc1,
        args.tolerance,
        arc1_min,
        arc1_max,
        args.min_anchor_spacing,
    ) + fit_adaptive(
        arc2,
        args.tolerance,
        arc2_min,
        arc2_max,
        args.min_anchor_spacing,
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n  <path d="{path_data(curves)}" fill="{args.fill}"/>\n</svg>\n'''
    svg_path = output / f"{args.name}.svg"
    svg_path.write_text(svg)

    sampled_float = sample_curves(curves)
    sampled = np.rint(sampled_float).astype(np.int32)
    traced = np.zeros_like(mask)
    cv2.fillPoly(traced, [sampled], 255)
    intersection = cv2.countNonZero(cv2.bitwise_and(mask, traced))
    union = cv2.countNonZero(cv2.bitwise_or(mask, traced))
    iou = intersection / union if union else 0.0

    source_edge, traced_edge = edge(mask), edge(traced)
    source_distance = cv2.distanceTransform(255 - source_edge, cv2.DIST_L2, 3)
    trace_distance = cv2.distanceTransform(255 - traced_edge, cv2.DIST_L2, 3)
    to_source = source_distance[traced_edge > 0]
    to_trace = trace_distance[source_edge > 0]
    distances = np.concatenate((to_source, to_trace)) if len(to_source) and len(to_trace) else np.array([math.inf])
    source_local = local_error(contour, trace_distance)
    trace_local = local_error(sampled_float, source_distance)
    metrics = {
        "name": args.name,
        "source_size": [width, height],
        "fit_parameters": {
            "tolerance_px": args.tolerance,
            "minimum_segments": args.min_segments,
            "maximum_segments": args.max_segments,
            "minimum_anchor_spacing_px": args.min_anchor_spacing,
            "smoothing_sigma_px": args.smoothing_sigma,
            "subpixel_scale": args.subpixel_scale,
        },
        "curve_segments": len(curves),
        "anchor_count": len(curves),
        "structure": structure_metrics(curves),
        "silhouette_iou": round(float(iou), 6),
        "edge_mean_px": round(float(np.mean(distances)), 4),
        "edge_p95_px": round(float(np.percentile(distances, 95)), 4),
        "edge_p99_px": round(float(np.percentile(distances, 99)), 4),
        "edge_max_px": round(float(np.max(distances)), 4),
        "source_to_trace_local": source_local,
        "trace_to_source_local": trace_local,
    }
    (output / f"{args.name}.metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

    overlay = np.full((height, width, 3), 245, dtype=np.uint8)
    overlap = cv2.bitwise_and(mask, traced) > 0
    source_only = cv2.bitwise_and(mask, cv2.bitwise_not(traced)) > 0
    trace_only = cv2.bitwise_and(traced, cv2.bitwise_not(mask)) > 0
    overlay[overlap] = (205, 205, 205)
    overlay[source_only] = (50, 70, 235)
    overlay[trace_only] = (235, 80, 170)
    cv2.imwrite(str(output / f"{args.name}.difference.png"), overlay)
    cv2.imwrite(str(output / f"{args.name}.rasterized.png"), traced)
    if args.source:
        write_source_overlay(args.source, output / f"{args.name}.source-overlay.png", mask, curves)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
