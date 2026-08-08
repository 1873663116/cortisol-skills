#!/usr/bin/env python3
"""Validate editable geometry-delivery SVG structure."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


FORBIDDEN = {
    "image",
    "script",
    "foreignObject",
    "defs",
    "filter",
    "mask",
    "style",
    "linearGradient",
    "radialGradient",
    "pattern",
    "clipPath",
    "symbol",
    "use",
}
EDITABLE_GEOMETRY = {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line"}


def local(tag: object) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("svg", nargs="+")
    parser.add_argument("--matching-canvas", action="store_true")
    parser.add_argument("--output-json", help="write a hash-bound structural report")
    args = parser.parse_args()
    canvases = []
    reports = []
    for raw in args.svg:
        path = Path(raw)
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as error:
            fail(f"{path}: {error}")
        values = root.get("viewBox", "").replace(",", " ").split()
        if len(values) != 4:
            fail(f"{path}: viewBox must contain four numbers")
        try:
            box = tuple(float(value) for value in values)
        except ValueError:
            fail(f"{path}: nonnumeric viewBox")
        if not all(math.isfinite(value) for value in box) or box[2] <= 0 or box[3] <= 0:
            fail(f"{path}: invalid viewBox")
        if not root.get("width") or not root.get("height"):
            fail(f"{path}: missing width or height")
        geometry = [node for node in root.iter() if local(node.tag) in EDITABLE_GEOMETRY]
        forbidden = sorted({local(node.tag) for node in root.iter() if local(node.tag) in FORBIDDEN})
        if forbidden:
            fail(f"{path}: geometry delivery contains unsupported elements: {forbidden}")
        if not geometry:
            fail(f"{path}: no editable vector geometry")
        indirect_paint = [
            local(node.tag)
            for node in geometry
            if "url(" in node.get("fill", "") or "url(" in node.get("stroke", "")
        ]
        if indirect_paint:
            fail(f"{path}: geometry delivery uses indirect paint: {indirect_paint}")
        visible_strokes = [
            local(node.tag)
            for node in geometry
            if node.get("stroke", "none").strip().lower() != "none"
        ]
        if visible_strokes:
            fail(f"{path}: authoritative silhouettes use filled boundaries: {visible_strokes}")
        empty_paths = [node for node in geometry if local(node.tag) == "path" and not node.get("d", "").strip()]
        if empty_paths:
            fail(f"{path}: empty path in geometry candidate")
        canvases.append(box)
        reports.append(
            {
                "artifact": str(path.resolve()),
                "artifact_sha256": file_sha256(path),
                "viewBox": box,
                "editable_geometry": len(geometry),
                "decision": "pass",
            }
        )
        print(f"PASS: {path} viewBox={box} editable_geometry={len(geometry)}")
    if args.matching_canvas and any(canvas != canvases[0] for canvas in canvases[1:]):
        fail("SVG canvases do not match")
    if args.output_json:
        output = Path(args.output_json)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps({"artifacts": reports, "decision": "pass", "failures": []}, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
