#!/usr/bin/env python3
"""Create inspectable visible-region candidates from explicit Lab decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def kernel(radius: int) -> np.ndarray:
    size = (radius * 2) + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def component_at_seed(mask: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    x, y = seed
    label = int(labels[y, x]) if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1] else 0
    if label == 0 and count > 1:
        label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(labels == label, 255, 0).astype(np.uint8) if label else np.zeros_like(mask)


def required_number(layer: dict[str, object], name: str, field: str) -> float:
    if field not in layer:
        fail(f"{name}: missing explicit decision '{field}'")
    try:
        return float(layer[field])
    except (TypeError, ValueError):
        fail(f"{name}: '{field}' must be numeric")


def polygon_mask(shape: tuple[int, int], polygons: list[object]) -> np.ndarray:
    result = np.zeros(shape, dtype=np.uint8)
    for polygon in polygons:
        cv2.fillPoly(result, [np.asarray(polygon, dtype=np.int32)], 255)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("config")
    parser.add_argument("output_dir")
    args = parser.parse_args()

    source_path = Path(args.source)
    config_path = Path(args.config)
    output = Path(args.output_dir)
    image = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
    if image is None:
        fail(f"cannot read source: {source_path}")
    try:
        config = json.loads(config_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read config: {error}")

    height, width = image.shape[:2]
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    output.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []
    source_record = {"path": str(source_path.resolve()), "sha256": file_sha256(source_path)}
    config_record = {"path": str(config_path.resolve()), "sha256": file_sha256(config_path)}

    layers = config.get("layers")
    if not isinstance(layers, list) or not layers:
        fail("config must contain a nonempty 'layers' array")

    for layer in layers:
        name = str(layer["name"])
        samples = [(int(x), int(y)) for x, y in layer["samples"]]
        if not samples:
            fail(f"{name}: samples is empty")
        if any(not (0 <= x < width and 0 <= y < height) for x, y in samples):
            fail(f"{name}: sample outside image")
        tolerance = required_number(layer, name, "lab_tolerance")
        uncertainty_width = required_number(layer, name, "uncertainty_width")
        open_radius = int(required_number(layer, name, "open_radius"))
        close_radius = int(required_number(layer, name, "close_radius"))
        if tolerance <= 0:
            fail(f"{name}: lab_tolerance must be positive")
        if uncertainty_width < 0:
            fail(f"{name}: uncertainty_width must not be negative")
        if open_radius < 0 or close_radius < 0:
            fail(f"{name}: morphology radii must not be negative")

        colors = np.array([lab[y, x] for x, y in samples])
        distances = np.min(np.linalg.norm(lab[:, :, None, :] - colors[None, None, :, :], axis=3), axis=2)
        mask = np.where(distances <= tolerance, 255, 0).astype(np.uint8)
        allowed = np.ones(mask.shape, dtype=bool)

        if "roi" in layer:
            left, top, right, bottom = map(int, layer["roi"])
            roi_mask = np.zeros_like(mask)
            roi_mask[max(0, top):min(height, bottom), max(0, left):min(width, right)] = 255
            mask = cv2.bitwise_and(mask, roi_mask)
            allowed = roi_mask > 0
        if open_radius:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel(open_radius))
        if close_radius:
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel(close_radius))

        include = polygon_mask(mask.shape, layer.get("include_polygons", []))
        exclude = polygon_mask(mask.shape, layer.get("exclude_polygons", []))
        explicit_unknown = polygon_mask(mask.shape, layer.get("unknown_polygons", []))
        mask[include > 0] = 255
        mask[exclude > 0] = 0
        mask = component_at_seed(mask, samples[0])

        if cv2.countNonZero(mask) == 0:
            fail(f"{name}: segmentation produced an empty mask")
        mask_path = output / f"{name}.mask.png"
        cv2.imwrite(str(mask_path), mask)

        confidence_limit = tolerance + max(uncertainty_width, 1.0)
        confidence = np.clip(1.0 - (distances / confidence_limit), 0.0, 1.0)
        confidence[~allowed] = 0.0
        confidence_path = output / f"{name}.confidence.png"
        cv2.imwrite(str(confidence_path), np.rint(confidence * 255).astype(np.uint8))

        uncertain = allowed & (np.abs(distances - tolerance) <= uncertainty_width)
        uncertain |= explicit_unknown > 0
        evidence = np.zeros_like(mask)
        evidence[(mask > 0) & ~uncertain] = 255
        evidence[uncertain] = 127
        evidence_path = output / f"{name}.evidence.png"
        cv2.imwrite(str(evidence_path), evidence)

        observed = np.where(allowed & ~uncertain, 255, 0).astype(np.uint8)
        observed_path = output / f"{name}.observed-region.png"
        cv2.imwrite(str(observed_path), observed)

        inside = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        outside = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
        signed_distance = inside - outside
        signed_distance_path = output / f"{name}.signed-distance.npy"
        np.save(signed_distance_path, signed_distance)
        extent = max(1.0, float(np.percentile(np.abs(signed_distance), 95)))
        normalized = np.clip((signed_distance / extent + 1.0) * 127.5, 0, 255).astype(np.uint8)
        signed_heatmap_path = output / f"{name}.signed-distance.png"
        cv2.imwrite(str(signed_heatmap_path), cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO))

        edges = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, kernel(1))
        overlay = image.copy()
        if np.any(uncertain):
            overlay[uncertain] = cv2.addWeighted(
                overlay[uncertain],
                0.45,
                np.full_like(overlay[uncertain], (0, 215, 255)),
                0.55,
                0,
            )
        overlay[edges > 0] = (40, 40, 255)
        overlay_path = output / f"{name}.overlay.png"
        cv2.imwrite(str(overlay_path), overlay)
        provenance_path = output / f"{name}.source-evidence.json"
        provenance = {
            "schema": "raster-to-editable-svg/source-evidence/v1",
            "producer": "segment_layers.py",
            "candidate_independent": True,
            "source": source_record,
            "evidence_mask": {
                "path": str(mask_path.resolve()),
                "sha256": file_sha256(mask_path),
            },
            "observed_region": {
                "path": str(observed_path.resolve()),
                "sha256": file_sha256(observed_path),
            },
            "derivation_inputs": [source_record, config_record],
        }
        provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
        x, y, w, h = cv2.boundingRect(mask)
        summary.append(
            {
                "name": name,
                "method": "lab-distance-visible-region-candidate",
                "parameters": {
                    "lab_tolerance": tolerance,
                    "uncertainty_width": uncertainty_width,
                    "open_radius": open_radius,
                    "close_radius": close_radius,
                    "samples": samples,
                    "roi": layer.get("roi"),
                },
                "mask": str(mask_path),
                "confidence": str(confidence_path),
                "evidence": str(evidence_path),
                "observed_region": str(observed_path),
                "source_evidence_provenance": str(provenance_path),
                "signed_distance": str(signed_distance_path),
                "signed_distance_heatmap": str(signed_heatmap_path),
                "overlay": str(overlay_path),
                "legend": {"0": "not selected", "127": "uncertain or declared unknown", "255": "selected visible-region candidate"},
                "manual_corrections": {
                    "included_pixels": int(cv2.countNonZero(include)),
                    "excluded_pixels": int(cv2.countNonZero(exclude)),
                    "declared_unknown_pixels": int(cv2.countNonZero(explicit_unknown)),
                },
                "area": int(cv2.countNonZero(mask)),
                "bbox": [x, y, w, h],
            }
        )

    (output / "segmentation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
