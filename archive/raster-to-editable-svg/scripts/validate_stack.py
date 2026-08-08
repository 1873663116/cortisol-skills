#!/usr/bin/env python3
"""Validate complete support coverage and declared overlap in a layered SVG reconstruction."""

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


def read_mask(path: Path, label: str) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        fail(f"cannot read {label}: {path}")
    return image >= 128


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text())
        layer_records = config["layers"]
        required_path = Path(config["required_coverage_mask"])
        maximum_uncovered = float(config["maximum_uncovered_fraction"])
        relationship_records = config.get("relationships", [])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        fail(f"cannot read stack config: {error}")
    if not isinstance(layer_records, list) or not layer_records:
        fail("layers must be a nonempty list in bottom-to-top order")
    if not 0.0 <= maximum_uncovered <= 1.0:
        fail("maximum_uncovered_fraction must be between zero and one")

    layers: dict[str, np.ndarray] = {}
    artifacts = []
    expected_shape = None
    for record in layer_records:
        try:
            name = str(record["name"])
            mask_path = Path(record["mask"])
            artifact_path = Path(record["artifact"])
        except (KeyError, TypeError) as error:
            fail(f"invalid layer record: {error}")
        if name in layers:
            fail(f"duplicate layer name: {name}")
        if not artifact_path.is_file():
            fail(f"artifact does not exist: {artifact_path}")
        mask = read_mask(mask_path, f"mask for {name}")
        if expected_shape is None:
            expected_shape = mask.shape
        if mask.shape != expected_shape:
            fail(f"layer masks have different dimensions: {name}={mask.shape}, expected={expected_shape}")
        layers[name] = mask
        artifacts.append(
            {
                "name": name,
                "artifact": str(artifact_path.resolve()),
                "artifact_sha256": file_sha256(artifact_path),
                "mask": str(mask_path),
                "mask_sha256": file_sha256(mask_path),
            }
        )

    required = read_mask(required_path, "required coverage mask")
    if required.shape != expected_shape:
        fail("required coverage mask dimensions differ from layer masks")
    required_pixels = int(np.count_nonzero(required))
    if required_pixels == 0:
        fail("required coverage mask selects no pixels")

    depth = np.zeros(expected_shape, dtype=np.uint16)
    for mask in layers.values():
        depth += mask.astype(np.uint16)
    uncovered = required & (depth == 0)
    uncovered_fraction = float(np.count_nonzero(uncovered) / required_pixels)
    failures = []
    if uncovered_fraction > maximum_uncovered:
        failures.append(
            f"required coverage uncovered fraction {uncovered_fraction:.6f} exceeds {maximum_uncovered:.6f}"
        )

    relationships = []
    artifact_paths = {Path(item["artifact"]).resolve() for item in artifacts}
    artifact_hashes = {str(item["artifact_sha256"]) for item in artifacts}
    for record in relationship_records:
        try:
            upper = str(record["upper"])
            lower = str(record["lower"])
            kind = str(record.get("kind", "overlap"))
            basis = str(record["basis"])
        except (KeyError, TypeError, ValueError) as error:
            fail(f"invalid relationship record: {error}")
        if kind not in {"overlap", "separation"}:
            fail(f"relationship {upper}, {lower} has unsupported kind: {kind}")
        if basis not in {"explicit_request", "independent_evidence"}:
            fail(f"relationship {upper}, {lower} must declare explicit_request or independent_evidence")
        basis_record: dict[str, object] = {"kind": kind, "basis": basis}
        evidence_record: dict[str, object] | None = None
        evidence_path: Path | None = None
        if basis == "explicit_request":
            request_reference = str(record.get("request_reference", "")).strip()
            if not request_reference:
                fail(f"relationship {upper}, {lower} lacks request_reference")
            basis_record["request_reference"] = request_reference
        else:
            evidence_path = Path(str(record.get("evidence", "")))
            if not evidence_path.is_file():
                fail(f"relationship {upper}, {lower} independent evidence does not exist: {evidence_path}")
            try:
                evidence_record = json.loads(evidence_path.read_text())
                source_record = evidence_record["source"]
                derivation_inputs = evidence_record["derivation_inputs"]
            except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
                fail(f"cannot read relationship evidence {evidence_path}: {error}")
            if evidence_record.get("schema") != "raster-to-editable-svg/relationship-evidence/v1":
                fail(f"relationship {upper}, {lower} has unsupported evidence schema")
            if evidence_record.get("candidate_independent") is not True:
                fail(f"relationship {upper}, {lower} evidence is not candidate-independent")
            relation = evidence_record.get("relationship", {})
            if (
                relation.get("upper") != upper
                or relation.get("lower") != lower
                or relation.get("kind", "overlap") != kind
            ):
                fail(f"relationship evidence does not describe {upper}, {lower}")
            if not isinstance(derivation_inputs, list) or not derivation_inputs:
                fail(f"relationship {upper}, {lower} evidence lacks derivation_inputs")

            def verify_dependency(entry: object, label: str) -> tuple[Path, str]:
                if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
                    fail(f"invalid {label} in relationship evidence")
                dependency = Path(str(entry["path"]))
                if not dependency.is_absolute():
                    dependency = evidence_path.parent / dependency
                if not dependency.is_file():
                    fail(f"{label} does not exist: {dependency}")
                dependency_hash = file_sha256(dependency)
                if dependency_hash != str(entry["sha256"]):
                    fail(f"{label} hash does not match relationship evidence")
                return dependency.resolve(), dependency_hash

            source_path, source_hash = verify_dependency(source_record, "relationship source")
            verified_dependencies = []
            for index, entry in enumerate(derivation_inputs):
                dependency_path, dependency_hash = verify_dependency(entry, f"relationship input {index}")
                if dependency_path in artifact_paths or dependency_hash in artifact_hashes:
                    fail(f"relationship {upper}, {lower} evidence depends on a candidate")
                if dependency_path.suffix.lower() == ".svg":
                    fail(f"relationship {upper}, {lower} evidence contains an SVG candidate")
                verified_dependencies.append(
                    {"path": str(dependency_path), "sha256": dependency_hash}
                )
            if source_hash not in {item["sha256"] for item in verified_dependencies}:
                fail(f"relationship {upper}, {lower} source is absent from derivation_inputs")
            basis_record["evidence"] = str(evidence_path.resolve())
            basis_record["evidence_sha256"] = file_sha256(evidence_path)
            basis_record["source"] = str(source_path)
            basis_record["source_sha256"] = source_hash
            basis_record["derivation_inputs"] = verified_dependencies
        if upper not in layers or lower not in layers:
            fail(f"relationship references an unknown layer: {upper}, {lower}")
        if kind == "overlap":
            try:
                minimum_pixels = int(record["minimum_overlap_pixels"])
            except (KeyError, TypeError, ValueError) as error:
                fail(f"invalid overlap relationship {upper}, {lower}: {error}")
            overlap = layers[upper] & layers[lower]
            overlap_pixels = int(np.count_nonzero(overlap))
            upper_pixels = int(np.count_nonzero(layers[upper]))
            lower_pixels = int(np.count_nonzero(layers[lower]))
            passed = overlap_pixels >= minimum_pixels
            if not passed:
                failures.append(
                    f"{upper} over {lower} overlap {overlap_pixels}px is below {minimum_pixels}px"
                )
            relationships.append(
                {
                    "upper": upper,
                    "lower": lower,
                    "overlap_pixels": overlap_pixels,
                    "fraction_of_upper": round(overlap_pixels / max(1, upper_pixels), 6),
                    "fraction_of_lower": round(overlap_pixels / max(1, lower_pixels), 6),
                    "minimum_overlap_pixels": minimum_pixels,
                    **basis_record,
                    "decision": "pass" if passed else "fail",
                }
            )
            continue

        try:
            maximum_overlap = int(record["maximum_overlap_pixels"])
            minimum_gap = float(record["minimum_gap_px"])
            maximum_gap = float(record["maximum_gap_px"])
        except (KeyError, TypeError, ValueError) as error:
            fail(f"invalid separation relationship {upper}, {lower}: {error}")
        if maximum_overlap < 0 or minimum_gap < 0 or maximum_gap < minimum_gap:
            fail(f"invalid separation criteria for {upper}, {lower}")
        region = np.ones(expected_shape, dtype=bool)
        region_record: dict[str, object] = {"measurement_region": "full_canvas"}
        if "measurement_region" in record:
            region_path = Path(str(record["measurement_region"]))
            region = read_mask(region_path, f"separation measurement region for {upper}, {lower}")
            if region.shape != expected_shape:
                fail(f"separation measurement region dimensions differ for {upper}, {lower}")
            region_hash = file_sha256(region_path)
            region_record = {
                "measurement_region": str(region_path.resolve()),
                "measurement_region_sha256": region_hash,
            }
            if basis == "independent_evidence":
                declared_region = evidence_record.get("measurement_region", {}) if evidence_record else {}
                if (
                    not isinstance(declared_region, dict)
                    or declared_region.get("sha256") != region_hash
                ):
                    fail(f"separation region is not bound to independent evidence for {upper}, {lower}")
        elif basis == "independent_evidence":
            fail(f"independent separation evidence requires measurement_region for {upper}, {lower}")

        upper_eval = layers[upper] & region
        lower_eval = layers[lower] & region
        if not np.any(upper_eval) or not np.any(lower_eval):
            fail(f"separation region does not contain both layers: {upper}, {lower}")
        overlap_pixels = int(np.count_nonzero(upper_eval & lower_eval))
        if overlap_pixels:
            gap = 0.0
        else:
            distance_to_lower = cv2.distanceTransform((~lower_eval).astype(np.uint8), cv2.DIST_L2, 5)
            gap = float(np.min(distance_to_lower[upper_eval]))
        passed = (
            overlap_pixels <= maximum_overlap
            and minimum_gap <= gap <= maximum_gap
        )
        if overlap_pixels > maximum_overlap:
            failures.append(
                f"{upper}, {lower} overlap {overlap_pixels}px exceeds {maximum_overlap}px in separation region"
            )
        if gap < minimum_gap or gap > maximum_gap:
            failures.append(
                f"{upper}, {lower} minimum gap {gap:.4f}px is outside {minimum_gap:.4f}..{maximum_gap:.4f}px"
            )
        relationships.append(
            {
                "upper": upper,
                "lower": lower,
                "overlap_pixels": overlap_pixels,
                "maximum_overlap_pixels": maximum_overlap,
                "minimum_gap_px": round(gap, 4),
                "required_gap_px": [minimum_gap, maximum_gap],
                **region_record,
                **basis_record,
                "decision": "pass" if passed else "fail",
            }
        )

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "config": str(Path(args.config)),
        "config_sha256": file_sha256(Path(args.config)),
        "required_coverage_mask": str(required_path),
        "required_coverage_mask_sha256": file_sha256(required_path),
        "required_coverage_pixels": required_pixels,
        "uncovered_pixels": int(np.count_nonzero(uncovered)),
        "uncovered_fraction": round(uncovered_fraction, 6),
        "maximum_uncovered_fraction": maximum_uncovered,
        "layers": artifacts,
        "relationships": relationships,
        "decision": "pass" if not failures else "fail",
        "failures": failures,
    }
    (output / "stack-metrics.json").write_text(json.dumps(report, indent=2) + "\n")

    depth_image = np.zeros((*expected_shape, 3), dtype=np.uint8)
    palette = np.array(
        [[245, 245, 245], [220, 225, 235], [120, 200, 120], [70, 170, 220], [90, 90, 230], [180, 70, 220]],
        dtype=np.uint8,
    )
    depth_image[:] = palette[0]
    for value in range(1, min(len(palette), int(np.max(depth)) + 1)):
        depth_image[depth == value] = palette[value]
    depth_image[depth >= len(palette)] = palette[-1]
    depth_image[uncovered] = (40, 40, 240)
    cv2.imwrite(str(output / "coverage-depth.png"), depth_image)

    uncovered_image = np.full((*expected_shape, 3), 245, dtype=np.uint8)
    uncovered_image[required] = (220, 220, 220)
    uncovered_image[required & (depth > 0)] = (90, 190, 100)
    uncovered_image[uncovered] = (40, 40, 240)
    cv2.imwrite(str(output / "required-coverage.png"), uncovered_image)
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
