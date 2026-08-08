#!/usr/bin/env python3
"""Aggregate exact-final SVG evidence into one mechanical completion gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(base: Path, raw: object) -> Path:
    path = Path(str(raw))
    return path if path.is_absolute() else base / path


def read_report(path: Path, label: str, failures: list[str]) -> dict[str, object] | None:
    if not path.is_file():
        failures.append(f"missing {label}: {path}")
        return None
    try:
        report = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"cannot read {label} {path}: {error}")
        return None
    if not isinstance(report, dict):
        failures.append(f"{label} is not a JSON object: {path}")
        return None
    if report.get("decision") != "pass":
        failures.append(f"{label} is not pass: {path}")
    return report


def matches_structural(report: dict[str, object], artifact_hash: str) -> bool:
    records = report.get("artifacts", [])
    return isinstance(records, list) and any(
        isinstance(record, dict)
        and record.get("artifact_sha256") == artifact_hash
        and record.get("decision") == "pass"
        for record in records
    )


def validate_final_review(
    report_path: Path,
    kind: str,
    expected_artifacts: dict[Path, str],
    failures: list[str],
) -> dict[str, object] | None:
    report = read_report(report_path, f"{kind} final review", failures)
    if report is None:
        return None
    if report.get("schema") != "raster-to-editable-svg/final-review/v1" or report.get("kind") != kind:
        failures.append(f"{kind} final review has an invalid schema or kind")
        return report
    reviewed: dict[Path, str] = {}
    for entry in report.get("artifacts", []):
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            failures.append(f"{kind} final review contains an invalid artifact record")
            continue
        artifact = resolve(report_path.parent, entry["path"]).resolve()
        reviewed[artifact] = str(entry["sha256"])
    if reviewed != expected_artifacts:
        failures.append(f"{kind} final review does not match all current artifact paths and hashes")

    evidence = report.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        failures.append(f"{kind} final review lacks evidence files")
    else:
        for index, entry in enumerate(evidence):
            if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
                failures.append(f"{kind} final review evidence {index} is invalid")
                continue
            evidence_path = resolve(report_path.parent, entry["path"])
            if not evidence_path.is_file() or file_sha256(evidence_path) != str(entry["sha256"]):
                failures.append(f"{kind} final review evidence {index} is missing or changed")

    state = report.get("state")
    if not isinstance(state, dict):
        failures.append(f"{kind} final review lacks explicit state")
    elif kind == "visual":
        for field in ("source_scale_inspected", "editing_scale_inspected", "target_sizes_inspected"):
            if state.get(field) is not True:
                failures.append(f"visual final review state {field} is not true")
    else:
        if not str(state.get("editor", "")).strip():
            failures.append("target-editor final review lacks editor identity")
        for field in ("import_succeeded", "vector_objects_editable", "independent_layers"):
            if state.get(field) is not True:
                failures.append(f"target-editor final review state {field} is not true")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("output_json")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_path = Path(args.output_json)
    failures: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text())
        artifact_records = manifest["artifacts"]
        layered = manifest["layered"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"FAIL: cannot read delivery manifest: {error}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(artifact_records, list) or not artifact_records:
        print("FAIL: delivery manifest artifacts must be a nonempty list", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(layered, bool):
        print("FAIL: delivery manifest layered must be boolean", file=sys.stderr)
        raise SystemExit(1)

    base = manifest_path.parent
    results = []
    layer_hashes: dict[str, str] = {}
    current_artifacts: dict[Path, str] = {}
    names: set[str] = set()
    for index, record in enumerate(artifact_records):
        try:
            name = str(record["name"])
            role = str(record["role"])
            artifact = resolve(base, record["artifact"])
            reports = record["reports"]
            expected_path_ids = {str(value) for value in record["path_ids"]}
        except (KeyError, TypeError) as error:
            failures.append(f"artifact record {index} is invalid: {error}")
            continue
        if name in names:
            failures.append(f"duplicate artifact name: {name}")
            continue
        names.add(name)
        if role not in {"layer", "composite"}:
            failures.append(f"{name}: role must be layer or composite")
        if not expected_path_ids:
            failures.append(f"{name}: path_ids must be nonempty")
        if not artifact.is_file():
            failures.append(f"{name}: artifact does not exist: {artifact}")
            continue
        artifact_hash = file_sha256(artifact)
        current_artifacts[artifact.resolve()] = artifact_hash
        if role == "layer":
            layer_hashes[name] = artifact_hash
        required_kinds = ("structural", "curve", "geometry") if role == "layer" else ("structural", "curve")
        if not isinstance(reports, dict):
            failures.append(f"{name}: reports must be an object")
            continue
        loaded: dict[str, dict[str, object]] = {}
        for kind in required_kinds:
            if kind not in reports:
                failures.append(f"{name}: missing required {kind} report")
                continue
            report_path = resolve(base, reports[kind])
            report = read_report(report_path, f"{name} {kind} report", failures)
            if report is not None:
                loaded[kind] = report

        structural = loaded.get("structural")
        if structural is not None and not matches_structural(structural, artifact_hash):
            failures.append(f"{name}: structural report does not match the current artifact hash")

        curve = loaded.get("curve")
        if curve is not None:
            if curve.get("artifact_sha256") != artifact_hash:
                failures.append(f"{name}: curve report does not match the current artifact hash")
            criteria = curve.get("criteria")
            maximum_span = criteria.get("max_bezier_arc_length") if isinstance(criteria, dict) else None
            if (
                isinstance(maximum_span, bool)
                or not isinstance(maximum_span, (int, float))
                or maximum_span <= 0
            ):
                failures.append(f"{name}: curve report lacks max_bezier_arc_length")
            curve_paths = curve.get("paths")
            if not isinstance(curve_paths, list):
                failures.append(f"{name}: curve report lacks path records")
            else:
                reported_ids = {
                    str(path.get("id")) for path in curve_paths if isinstance(path, dict) and path.get("id") is not None
                }
                if reported_ids != expected_path_ids:
                    failures.append(
                        f"{name}: curve path ids {sorted(reported_ids)} do not match {sorted(expected_path_ids)}"
                    )
                for path in curve_paths:
                    if not isinstance(path, dict):
                        continue
                    if not isinstance(path.get("anchor_count"), int) or not isinstance(
                        path.get("segment_arc_length"), list
                    ):
                        failures.append(f"{name}: curve path {path.get('id')} lacks anchor or segment-length evidence")

        geometry = loaded.get("geometry")
        if geometry is not None:
            if geometry.get("artifact_sha256") != artifact_hash:
                failures.append(f"{name}: geometry report does not match the current artifact hash")
            source_evidence = geometry.get("source_evidence")
            if not isinstance(source_evidence, dict) or source_evidence.get("candidate_independent") is not True:
                failures.append(f"{name}: geometry report lacks independent source-evidence provenance")
            else:
                evidence_record = Path(str(source_evidence.get("record", "")))
                if not evidence_record.is_file() or file_sha256(evidence_record) != source_evidence.get(
                    "record_sha256"
                ):
                    failures.append(f"{name}: source-evidence provenance record is missing or changed")

        results.append(
            {
                "name": name,
                "role": role,
                "artifact": str(artifact.resolve()),
                "artifact_sha256": artifact_hash,
                "required_reports": list(required_kinds),
            }
        )

    stack_summary = None
    if layered:
        required_relationship_records = manifest.get("required_relationships")
        if not isinstance(required_relationship_records, list):
            failures.append("layered delivery is missing required_relationships")
            required_relationships: set[tuple[str, str, str]] = set()
        else:
            required_relationships = {
                (str(item.get("kind", "overlap")), str(item.get("upper")), str(item.get("lower")))
                for item in required_relationship_records
                if isinstance(item, dict)
            }
        if "stack_report" not in manifest:
            failures.append("layered delivery is missing stack_report")
        else:
            stack_path = resolve(base, manifest["stack_report"])
            stack = read_report(stack_path, "stack report", failures)
            if stack is not None:
                stack_layers = stack.get("layers", [])
                reported_hashes = {
                    str(item.get("name")): str(item.get("artifact_sha256"))
                    for item in stack_layers
                    if isinstance(item, dict)
                }
                if set(reported_hashes) != set(layer_hashes):
                    failures.append(
                        f"stack layer names {sorted(reported_hashes)} do not match delivery layers {sorted(layer_hashes)}"
                    )
                for name, artifact_hash in layer_hashes.items():
                    if reported_hashes.get(name) != artifact_hash:
                        failures.append(f"stack report does not match current layer {name}")
                for relationship in stack.get("relationships", []):
                    if not isinstance(relationship, dict) or relationship.get("basis") not in {
                        "explicit_request",
                        "independent_evidence",
                    }:
                        failures.append("stack report contains a relationship without an authorized basis")
                reported_relationships = {
                    (
                        str(item.get("kind", "overlap")),
                        str(item.get("upper")),
                        str(item.get("lower")),
                    )
                    for item in stack.get("relationships", [])
                    if isinstance(item, dict)
                }
                if reported_relationships != required_relationships:
                    failures.append(
                        "stack relationships do not exactly match delivery required_relationships"
                    )
                stack_summary = {"report": str(stack_path.resolve()), "layer_count": len(stack_layers)}

    review_summary: dict[str, object] = {}
    final_reviews = manifest.get("final_reviews")
    if not isinstance(final_reviews, dict):
        failures.append("delivery manifest is missing final_reviews")
    else:
        for kind in ("visual", "target_editor"):
            if kind not in final_reviews:
                failures.append(f"delivery manifest is missing {kind} final review")
                continue
            review_path = resolve(base, final_reviews[kind])
            review = validate_final_review(review_path, kind, current_artifacts, failures)
            if review is not None:
                review_summary[kind] = {
                    "report": str(review_path.resolve()),
                    "report_sha256": file_sha256(review_path),
                    "decision": review.get("decision"),
                }

    decision = "pass" if not failures else "fail"
    result = {
        "manifest": str(manifest_path.resolve()),
        "manifest_sha256": file_sha256(manifest_path),
        "artifacts": results,
        "layered": layered,
        "stack": stack_summary,
        "final_reviews": review_summary,
        "decision": decision,
        "failures": failures,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
