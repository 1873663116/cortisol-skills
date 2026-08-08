#!/usr/bin/env python3
"""Inspect anchor spacing and join continuity in exact delivered SVG paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from svgpathtools import CubicBezier, QuadraticBezier, svg2paths2


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def angle_degrees(incoming: complex, outgoing: complex) -> float | None:
    denominator = abs(incoming) * abs(outgoing)
    if denominator <= 1e-12:
        return None
    cosine = (incoming.real * outgoing.real + incoming.imag * outgoing.imag) / denominator
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def load_corners(path: str | None) -> dict[str, set[int]]:
    if path is None:
        return {}
    try:
        raw = json.loads(Path(path).read_text())
        declared = raw.get("intentional_corners", {})
        return {str(name): {int(index) for index in indices} for name, indices in declared.items()}
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        fail(f"cannot read intentional corners: {error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("svg")
    parser.add_argument("output_json")
    parser.add_argument("--corners", help="JSON with {'intentional_corners': {'path-id': [join-index, ...]}}")
    parser.add_argument("--tangent-angle-max", type=float, required=True)
    parser.add_argument("--min-anchor-spacing", type=float, required=True)
    parser.add_argument(
        "--max-bezier-arc-length",
        type=float,
        required=True,
        help="task-scale upper bound for one editable Bezier segment, in SVG user units",
    )
    parser.add_argument("--require-closed", action="store_true")
    args = parser.parse_args()
    if args.tangent_angle_max < 0 or args.min_anchor_spacing < 0 or args.max_bezier_arc_length <= 0:
        fail("angle and minimum spacing must be nonnegative; maximum Bezier arc length must be positive")
    if args.max_bezier_arc_length < args.min_anchor_spacing:
        fail("max-bezier-arc-length must be at least min-anchor-spacing")

    artifact = Path(args.svg)
    if not artifact.is_file():
        fail(f"artifact does not exist: {artifact}")
    try:
        paths, attributes, _ = svg2paths2(str(artifact))
    except Exception as error:
        fail(f"cannot parse SVG paths: {error}")
    if not paths:
        fail("SVG contains no path geometry")
    corners = load_corners(args.corners)
    reports = []
    failures = []

    for path_index, (curve, attrs) in enumerate(zip(paths, attributes)):
        name = attrs.get("id") or f"path-{path_index}"
        segments = list(curve)
        if not segments:
            failures.append(f"{name}: empty path")
            continue
        closed = abs(segments[-1].end - segments[0].start) <= 1e-6
        if args.require_closed and not closed:
            failures.append(f"{name}: path is open")
        declared = corners.get(name, set())
        chord_lengths = [float(abs(segment.end - segment.start)) for segment in segments]
        segment_arc_lengths = [float(segment.length(error=1e-8)) for segment in segments]
        bezier_indices = [
            index
            for index, segment in enumerate(segments)
            if isinstance(segment, (CubicBezier, QuadraticBezier))
        ]
        joins = []
        join_count = len(segments) if closed else len(segments) - 1
        for join_index in range(join_count):
            current = segments[join_index]
            following = segments[(join_index + 1) % len(segments)]
            gap = float(abs(current.end - following.start))
            angle = angle_degrees(current.derivative(1.0), following.derivative(0.0))
            intentional = join_index in declared
            record = {
                "join_index": join_index,
                "anchor": [round(float(current.end.real), 4), round(float(current.end.imag), 4)],
                "gap_px": round(gap, 6),
                "tangent_angle_deg": None if angle is None else round(angle, 4),
                "intentional_corner": intentional,
            }
            joins.append(record)
            if gap > 1e-6:
                failures.append(f"{name}: join {join_index} has a {gap:.4f}px gap")
            if not intentional and angle is not None and angle > args.tangent_angle_max:
                failures.append(f"{name}: join {join_index} tangent angle {angle:.4f} exceeds criterion")
        short = [index for index, length in enumerate(chord_lengths) if length < args.min_anchor_spacing]
        if short:
            failures.append(f"{name}: segment chords below spacing criterion at {short}")
        long_beziers = [
            index
            for index in bezier_indices
            if segment_arc_lengths[index] > args.max_bezier_arc_length
        ]
        if long_beziers:
            failures.append(
                f"{name}: Bezier arc lengths exceed the task-scale criterion at {long_beziers}"
            )
        anchor_count = len(segments) if closed else len(segments) + 1
        reports.append(
            {
                "id": name,
                "closed": closed,
                "anchor_count": anchor_count,
                "segment_count": len(segments),
                "bezier_segment_count": len(bezier_indices),
                "cubic_segment_count": sum(isinstance(segment, CubicBezier) for segment in segments),
                "quadratic_segment_count": sum(isinstance(segment, QuadraticBezier) for segment in segments),
                "segment_types": [type(segment).__name__ for segment in segments],
                "segment_arc_length": [round(length, 4) for length in segment_arc_lengths],
                "chord_length_px": {
                    "minimum": round(min(chord_lengths), 4),
                    "median": round(sorted(chord_lengths)[len(chord_lengths) // 2], 4),
                    "maximum": round(max(chord_lengths), 4),
                },
                "joins": joins,
            }
        )

    report = {
        "artifact": str(artifact.resolve()),
        "artifact_sha256": file_sha256(artifact),
        "criteria": {
            "tangent_angle_max": args.tangent_angle_max,
            "min_anchor_spacing": args.min_anchor_spacing,
            "max_bezier_arc_length": args.max_bezier_arc_length,
            "require_closed": args.require_closed,
        },
        "paths": reports,
        "decision": "pass" if not failures else "fail",
        "failures": failures,
    }
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
