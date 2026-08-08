#!/usr/bin/env python3
"""Compare an exact SVG candidate's rendered silhouette with visible geometry evidence."""

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


def recorded_path(record_path: Path, value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else record_path.parent / path


def validate_source_evidence_provenance(
    provenance_path: Path,
    evidence_path: Path,
    observed_path: Path,
    candidate_path: Path,
    artifact_path: Path,
) -> dict[str, object]:
    try:
        record = json.loads(provenance_path.read_text())
        source_record = record["source"]
        evidence_record = record["evidence_mask"]
        observed_record = record["observed_region"]
        derivation_inputs = record["derivation_inputs"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        fail(f"cannot read source-evidence provenance: {error}")
    if record.get("schema") != "raster-to-editable-svg/source-evidence/v1":
        fail("unsupported source-evidence provenance schema")
    if record.get("candidate_independent") is not True:
        fail("source-evidence provenance must declare candidate_independent=true")
    if not isinstance(derivation_inputs, list) or not derivation_inputs:
        fail("source-evidence provenance must contain derivation_inputs")

    def verify_file(entry: object, label: str) -> tuple[Path, str]:
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            fail(f"invalid {label} record in source-evidence provenance")
        path = recorded_path(provenance_path, entry["path"])
        if not path.is_file():
            fail(f"{label} does not exist: {path}")
        actual = file_sha256(path)
        if actual != str(entry["sha256"]):
            fail(f"{label} hash does not match source-evidence provenance")
        return path.resolve(), actual

    source_path, source_hash = verify_file(source_record, "source image")
    recorded_evidence, evidence_hash = verify_file(evidence_record, "evidence mask")
    recorded_observed, observed_hash = verify_file(observed_record, "observed region")
    if recorded_evidence != evidence_path.resolve() or evidence_hash != file_sha256(evidence_path):
        fail("evidence mask does not match source-evidence provenance")
    if recorded_observed != observed_path.resolve() or observed_hash != file_sha256(observed_path):
        fail("observed region does not match source-evidence provenance")

    candidate_hash = file_sha256(candidate_path)
    artifact_hash = file_sha256(artifact_path)
    forbidden_paths = {candidate_path.resolve(), artifact_path.resolve()}
    forbidden_hashes = {candidate_hash, artifact_hash}
    verified_inputs = []
    for index, entry in enumerate(derivation_inputs):
        dependency_path, dependency_hash = verify_file(entry, f"derivation input {index}")
        if dependency_path in forbidden_paths or dependency_hash in forbidden_hashes:
            fail("source evidence depends on the candidate artifact or its render")
        if dependency_path.suffix.lower() == ".svg":
            fail("source-evidence derivation inputs must not contain SVG candidates")
        verified_inputs.append({"path": str(dependency_path), "sha256": dependency_hash})
    if source_hash not in {entry["sha256"] for entry in verified_inputs}:
        fail("source image is absent from source-evidence derivation inputs")
    if evidence_hash == candidate_hash or observed_hash == candidate_hash:
        fail("source evidence is self-referential to the candidate render")

    source = cv2.imread(str(source_path), cv2.IMREAD_UNCHANGED)
    if source is None:
        fail(f"cannot read source image from provenance: {source_path}")
    return {
        "record": str(provenance_path.resolve()),
        "record_sha256": file_sha256(provenance_path),
        "source": str(source_path),
        "source_sha256": source_hash,
        "source_shape": list(source.shape[:2]),
        "producer": record.get("producer"),
        "candidate_independent": True,
        "derivation_inputs": verified_inputs,
    }


def read_binary(path: Path, label: str) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        fail(f"cannot read {label}: {path}")
    return image >= 128


def interior_edge(mask: np.ndarray, observed: np.ndarray) -> np.ndarray:
    kernel = np.ones((3, 3), np.uint8)
    gradient = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_GRADIENT, kernel) > 0
    interior = cv2.erode(observed.astype(np.uint8), kernel, iterations=1) > 0
    return gradient & interior


def directed_distances(source_edge: np.ndarray, target_edge: np.ndarray) -> np.ndarray:
    if not np.any(source_edge) or not np.any(target_edge):
        fail("observed region must contain source and candidate edge samples")
    distance = cv2.distanceTransform((~target_edge).astype(np.uint8), cv2.DIST_L2, 5)
    return distance[source_edge]


def contour_windows(
    mask: np.ndarray,
    observed: np.ndarray,
    target_edge: np.ndarray,
    window_points: int,
    direction: str,
) -> list[dict[str, object]]:
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    interior = cv2.erode(observed.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1) > 0
    distance = cv2.distanceTransform((~target_edge).astype(np.uint8), cv2.DIST_L2, 5)
    records: list[dict[str, object]] = []
    minimum_run = max(8, window_points // 4)
    for contour_index, contour in enumerate(contours):
        points = contour.reshape(-1, 2)
        if len(points) < minimum_run:
            continue
        valid = interior[points[:, 1], points[:, 0]]
        indices = np.flatnonzero(valid)
        if not len(indices):
            continue
        runs = np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1)
        for run_index, run in enumerate(runs):
            if len(run) < minimum_run:
                continue
            for start in range(0, len(run), window_points):
                selected = run[start : start + window_points]
                if len(selected) < minimum_run:
                    continue
                samples = points[selected]
                values = distance[samples[:, 1], samples[:, 0]]
                center = np.mean(samples, axis=0)
                records.append(
                    {
                        "direction": direction,
                        "contour_index": contour_index,
                        "run_index": run_index,
                        "sample_count": len(selected),
                        "center": [round(float(center[0]), 2), round(float(center[1]), 2)],
                        "mean_px": round(float(np.mean(values)), 4),
                        "p95_px": round(float(np.percentile(values, 95)), 4),
                        "maximum_px": round(float(np.max(values)), 4),
                    }
                )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_mask", help="binary visible-geometry evidence from the source")
    parser.add_argument("candidate_mask", help="plain silhouette rendered from the exact SVG candidate")
    parser.add_argument("observed_region", help="binary region where the source supports comparison")
    parser.add_argument("output_dir")
    parser.add_argument("--artifact", required=True, help="exact SVG represented by candidate_mask")
    parser.add_argument(
        "--evidence-provenance",
        required=True,
        help="source-derived evidence record whose dependency chain excludes the candidate",
    )
    parser.add_argument("--iou-min", type=float, required=True)
    parser.add_argument("--edge-mean-max", type=float, required=True)
    parser.add_argument("--edge-p95-max", type=float, required=True)
    parser.add_argument("--local-window-points", type=int, required=True)
    parser.add_argument("--local-mean-max", type=float, required=True)
    parser.add_argument("--local-p95-max", type=float, required=True)
    args = parser.parse_args()
    if args.local_window_points < 8:
        fail("local-window-points must be at least 8")

    evidence_path = Path(args.evidence_mask)
    candidate_path = Path(args.candidate_mask)
    observed_path = Path(args.observed_region)
    artifact_path = Path(args.artifact)
    provenance_path = Path(args.evidence_provenance)
    if not artifact_path.is_file():
        fail(f"artifact does not exist: {artifact_path}")
    if not provenance_path.is_file():
        fail(f"source-evidence provenance does not exist: {provenance_path}")

    provenance = validate_source_evidence_provenance(
        provenance_path,
        evidence_path,
        observed_path,
        candidate_path,
        artifact_path,
    )

    evidence = read_binary(evidence_path, "evidence mask")
    candidate = read_binary(candidate_path, "candidate mask")
    observed = read_binary(observed_path, "observed region")
    if evidence.shape != candidate.shape or evidence.shape != observed.shape:
        fail(f"mask dimensions differ: evidence={evidence.shape}, candidate={candidate.shape}, observed={observed.shape}")
    if tuple(provenance["source_shape"]) != evidence.shape:
        fail(f"source dimensions differ from evidence masks: source={provenance['source_shape']}, masks={evidence.shape}")
    if not np.any(observed):
        fail("observed region selects no pixels")

    evidence_eval = evidence & observed
    candidate_eval = candidate & observed
    union = evidence_eval | candidate_eval
    intersection = evidence_eval & candidate_eval
    iou = 1.0 if not np.any(union) else float(np.count_nonzero(intersection) / np.count_nonzero(union))

    evidence_edge = interior_edge(evidence, observed)
    candidate_edge = interior_edge(candidate, observed)
    evidence_to_candidate = directed_distances(evidence_edge, candidate_edge)
    candidate_to_evidence = directed_distances(candidate_edge, evidence_edge)
    symmetric = np.concatenate((evidence_to_candidate, candidate_to_evidence))
    edge_mean = float(np.mean(symmetric))
    edge_p95 = float(np.percentile(symmetric, 95))
    local_windows = contour_windows(
        evidence, observed, candidate_edge, args.local_window_points, "evidence_to_candidate"
    ) + contour_windows(
        candidate, observed, evidence_edge, args.local_window_points, "candidate_to_evidence"
    )
    if not local_windows:
        fail("observed region yields no local contour windows")
    worst_local_mean = max(float(record["mean_px"]) for record in local_windows)
    worst_local_p95 = max(float(record["p95_px"]) for record in local_windows)
    passed = (
        iou >= args.iou_min
        and edge_mean <= args.edge_mean_max
        and edge_p95 <= args.edge_p95_max
        and worst_local_mean <= args.local_mean_max
        and worst_local_p95 <= args.local_p95_max
    )

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    metrics = {
        "artifact": str(artifact_path.resolve()),
        "artifact_sha256": file_sha256(artifact_path),
        "source_evidence": provenance,
        "evidence_mask": str(evidence_path),
        "evidence_mask_sha256": file_sha256(evidence_path),
        "candidate_mask": str(candidate_path),
        "candidate_mask_sha256": file_sha256(candidate_path),
        "observed_region": str(observed_path),
        "observed_region_sha256": file_sha256(observed_path),
        "observed_pixels": int(np.count_nonzero(observed)),
        "metrics": {
            "silhouette_iou": round(iou, 6),
            "symmetric_edge_mean_px": round(edge_mean, 4),
            "symmetric_edge_p95_px": round(edge_p95, 4),
            "evidence_to_candidate_mean_px": round(float(np.mean(evidence_to_candidate)), 4),
            "candidate_to_evidence_mean_px": round(float(np.mean(candidate_to_evidence)), 4),
            "worst_local_mean_px": round(worst_local_mean, 4),
            "worst_local_p95_px": round(worst_local_p95, 4),
        },
        "local_windows": sorted(local_windows, key=lambda record: float(record["mean_px"]), reverse=True),
        "thresholds": {
            "iou_min": args.iou_min,
            "edge_mean_max": args.edge_mean_max,
            "edge_p95_max": args.edge_p95_max,
            "local_window_points": args.local_window_points,
            "local_mean_max": args.local_mean_max,
            "local_p95_max": args.local_p95_max,
        },
        "decision": "pass" if passed else "fail",
    }
    (output / "geometry-metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

    overlap = np.full((*evidence.shape, 3), 238, dtype=np.uint8)
    overlap[observed] = (225, 225, 225)
    overlap[evidence_eval & ~candidate_eval] = (70, 70, 235)
    overlap[candidate_eval & ~evidence_eval] = (220, 80, 220)
    overlap[intersection] = (80, 180, 90)
    cv2.imwrite(str(output / "silhouette-overlap.png"), overlap)

    edges = np.full((*evidence.shape, 3), 245, dtype=np.uint8)
    edges[evidence_edge] = (70, 210, 70)
    edges[candidate_edge] = (210, 60, 225)
    edges[evidence_edge & candidate_edge] = (40, 40, 40)
    cv2.imwrite(str(output / "edge-overlay.png"), edges)

    local_map = edges.copy()
    for record in local_windows:
        x, y = (int(round(value)) for value in record["center"])
        severity = min(1.0, float(record["mean_px"]) / max(args.local_mean_max, 1e-9))
        color = (40, int(round(210 * (1.0 - severity))), int(round(80 + 175 * severity)))
        cv2.circle(local_map, (x, y), 5, color, -1, cv2.LINE_AA)
    cv2.imwrite(str(output / "local-residuals.png"), local_map)

    print(json.dumps(metrics, indent=2))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
