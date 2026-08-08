from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import cv2
import numpy as np


SCRIPTS = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_script(name: str, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
    )


class ValidationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.artifact = self.root / "shape.svg"
        self.artifact.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
            '<path id="shape" fill="#000" d="M 8 8 C 16 6 24 6 24 8 C 26 16 26 24 24 24 '
            'C 16 26 8 26 8 24 C 6 16 6 8 8 8 Z"/></svg>\n'
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_curve_report_has_real_anchors_and_rejects_long_beziers(self) -> None:
        passing = self.root / "curve-pass.json"
        result = run_script(
            "inspect_svg_curves.py",
            self.artifact,
            passing,
            "--tangent-angle-max",
            180,
            "--min-anchor-spacing",
            1,
            "--max-bezier-arc-length",
            100,
            "--require-closed",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(passing.read_text())
        self.assertEqual(report["paths"][0]["anchor_count"], 4)
        self.assertEqual(report["paths"][0]["cubic_segment_count"], 4)
        self.assertEqual(len(report["paths"][0]["segment_arc_length"]), 4)

        failing = self.root / "curve-fail.json"
        result = run_script(
            "inspect_svg_curves.py",
            self.artifact,
            failing,
            "--tangent-angle-max",
            180,
            "--min-anchor-spacing",
            1,
            "--max-bezier-arc-length",
            10,
            "--require-closed",
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(failing.read_text())["decision"], "fail")

    def source_geometry_reports(self) -> tuple[Path, Path]:
        source = np.full((32, 32, 3), 245, dtype=np.uint8)
        source[8:24, 8:24] = (220, 80, 60)
        source_path = self.root / "source.png"
        cv2.imwrite(str(source_path), source)
        config_path = self.root / "segments.json"
        config_path.write_text(
            json.dumps(
                {
                    "layers": [
                        {
                            "name": "shape",
                            "samples": [[12, 12]],
                            "lab_tolerance": 5,
                            "uncertainty_width": 0,
                            "open_radius": 0,
                            "close_radius": 0,
                            "roi": [0, 0, 32, 32],
                        }
                    ]
                }
            )
        )
        evidence_dir = self.root / "evidence"
        segmented = run_script("segment_layers.py", source_path, config_path, evidence_dir)
        self.assertEqual(segmented.returncode, 0, segmented.stderr)

        candidate = np.zeros((32, 32), dtype=np.uint8)
        candidate[8:24, 9:25] = 255
        candidate_path = self.root / "candidate.png"
        cv2.imwrite(str(candidate_path), candidate)
        geometry_dir = self.root / "geometry"
        geometry = run_script(
            "validate_geometry.py",
            evidence_dir / "shape.mask.png",
            candidate_path,
            evidence_dir / "shape.observed-region.png",
            geometry_dir,
            "--artifact",
            self.artifact,
            "--evidence-provenance",
            evidence_dir / "shape.source-evidence.json",
            "--iou-min",
            0,
            "--edge-mean-max",
            100,
            "--edge-p95-max",
            100,
            "--local-window-points",
            8,
            "--local-mean-max",
            100,
            "--local-p95-max",
            100,
        )
        self.assertEqual(geometry.returncode, 0, geometry.stderr)
        return geometry_dir / "geometry-metrics.json", candidate_path

    def test_geometry_requires_candidate_independent_source_evidence(self) -> None:
        geometry_report, candidate_path = self.source_geometry_reports()
        report = json.loads(geometry_report.read_text())
        self.assertTrue(report["source_evidence"]["candidate_independent"])

        provenance_path = self.root / "evidence" / "shape.source-evidence.json"
        provenance = json.loads(provenance_path.read_text())
        provenance["derivation_inputs"].append(
            {"path": str(candidate_path.resolve()), "sha256": sha256(candidate_path)}
        )
        provenance_path.write_text(json.dumps(provenance))
        result = run_script(
            "validate_geometry.py",
            self.root / "evidence" / "shape.mask.png",
            candidate_path,
            self.root / "evidence" / "shape.observed-region.png",
            self.root / "self-reference",
            "--artifact",
            self.artifact,
            "--evidence-provenance",
            provenance_path,
            "--iou-min",
            0,
            "--edge-mean-max",
            100,
            "--edge-p95-max",
            100,
            "--local-window-points",
            8,
            "--local-mean-max",
            100,
            "--local-p95-max",
            100,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("depends on the candidate", result.stderr)

    def test_delivery_gate_rejects_stale_current_artifact(self) -> None:
        geometry_report, _ = self.source_geometry_reports()
        structural_report = self.root / "structural.json"
        structural = run_script(
            "validate_svg.py", self.artifact, "--output-json", structural_report
        )
        self.assertEqual(structural.returncode, 0, structural.stderr)
        curve_report = self.root / "curve.json"
        curve = run_script(
            "inspect_svg_curves.py",
            self.artifact,
            curve_report,
            "--tangent-angle-max",
            180,
            "--min-anchor-spacing",
            1,
            "--max-bezier-arc-length",
            100,
            "--require-closed",
        )
        self.assertEqual(curve.returncode, 0, curve.stderr)
        manifest = self.root / "delivery.json"
        review_artifacts = [{"path": str(self.artifact), "sha256": sha256(self.artifact)}]
        review_evidence = [{"path": str(self.root / "source.png"), "sha256": sha256(self.root / "source.png")}]
        visual_review = self.root / "visual-review.json"
        visual_review.write_text(
            json.dumps(
                {
                    "schema": "raster-to-editable-svg/final-review/v1",
                    "kind": "visual",
                    "decision": "pass",
                    "artifacts": review_artifacts,
                    "evidence": review_evidence,
                    "state": {
                        "source_scale_inspected": True,
                        "editing_scale_inspected": True,
                        "target_sizes_inspected": True,
                    },
                }
            )
        )
        editor_review = self.root / "editor-review.json"
        editor_review.write_text(
            json.dumps(
                {
                    "schema": "raster-to-editable-svg/final-review/v1",
                    "kind": "target_editor",
                    "decision": "pass",
                    "artifacts": review_artifacts,
                    "evidence": review_evidence,
                    "state": {
                        "editor": "test editor",
                        "import_succeeded": True,
                        "vector_objects_editable": True,
                        "independent_layers": True,
                    },
                }
            )
        )
        manifest.write_text(
            json.dumps(
                {
                    "layered": False,
                    "artifacts": [
                        {
                            "name": "shape",
                            "role": "layer",
                            "artifact": str(self.artifact),
                            "path_ids": ["shape"],
                            "reports": {
                                "structural": str(structural_report),
                                "curve": str(curve_report),
                                "geometry": str(geometry_report),
                            },
                        }
                    ],
                    "final_reviews": {
                        "visual": str(visual_review),
                        "target_editor": str(editor_review),
                    },
                }
            )
        )
        result_path = self.root / "delivery-result.json"
        accepted = run_script("validate_delivery.py", manifest, result_path)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

        manifest_record = json.loads(manifest.read_text())
        del manifest_record["final_reviews"]["target_editor"]
        manifest.write_text(json.dumps(manifest_record))
        missing_review = run_script("validate_delivery.py", manifest, result_path)
        self.assertEqual(missing_review.returncode, 2)
        self.assertIn("missing target_editor final review", result_path.read_text())

        manifest_record["final_reviews"]["target_editor"] = str(editor_review)
        manifest.write_text(json.dumps(manifest_record))

        self.artifact.write_text(self.artifact.read_text().replace("#000", "#111"))
        rejected = run_script("validate_delivery.py", manifest, result_path)
        self.assertEqual(rejected.returncode, 2)
        failures = json.loads(result_path.read_text())["failures"]
        self.assertTrue(any("current artifact hash" in failure for failure in failures))

    def test_stack_relationship_requires_an_authorized_basis(self) -> None:
        mask = np.zeros((32, 32), dtype=np.uint8)
        mask[8:24, 8:24] = 255
        mask_path = self.root / "mask.png"
        cv2.imwrite(str(mask_path), mask)
        config_path = self.root / "stack.json"
        config = {
            "required_coverage_mask": str(mask_path),
            "maximum_uncovered_fraction": 0,
            "layers": [
                {"name": "lower", "mask": str(mask_path), "artifact": str(self.artifact)},
                {"name": "upper", "mask": str(mask_path), "artifact": str(self.artifact)},
            ],
            "relationships": [
                {
                    "upper": "upper",
                    "lower": "lower",
                    "minimum_overlap_pixels": 1,
                    "basis": "explicit_request",
                    "request_reference": "user requested shared support",
                }
            ],
        }
        config_path.write_text(json.dumps(config))
        accepted = run_script("validate_stack.py", config_path, self.root / "stack-pass")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

        del config["relationships"][0]["basis"]
        config_path.write_text(json.dumps(config))
        rejected = run_script("validate_stack.py", config_path, self.root / "stack-fail")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("invalid relationship record", rejected.stderr)

    def test_separation_relationship_rejects_intersection_and_wrong_gap(self) -> None:
        upper = np.zeros((32, 32), dtype=np.uint8)
        lower = np.zeros((32, 32), dtype=np.uint8)
        upper[8:24, 4:10] = 255
        lower[8:24, 14:20] = 255
        upper_path = self.root / "upper.png"
        lower_path = self.root / "lower.png"
        region_path = self.root / "negative-space.png"
        source_path = self.root / "relationship-source.png"
        cv2.imwrite(str(upper_path), upper)
        cv2.imwrite(str(lower_path), lower)
        cv2.imwrite(str(region_path), np.full((32, 32), 255, dtype=np.uint8))
        cv2.imwrite(str(source_path), np.full((32, 32, 3), 240, dtype=np.uint8))
        evidence_path = self.root / "separation-evidence.json"
        evidence_path.write_text(
            json.dumps(
                {
                    "schema": "raster-to-editable-svg/relationship-evidence/v1",
                    "candidate_independent": True,
                    "relationship": {"kind": "separation", "upper": "upper", "lower": "lower"},
                    "source": {"path": str(source_path), "sha256": sha256(source_path)},
                    "measurement_region": {"path": str(region_path), "sha256": sha256(region_path)},
                    "derivation_inputs": [
                        {"path": str(source_path), "sha256": sha256(source_path)}
                    ],
                }
            )
        )
        config_path = self.root / "separation-stack.json"
        config = {
            "required_coverage_mask": str(lower_path),
            "maximum_uncovered_fraction": 0,
            "layers": [
                {"name": "lower", "mask": str(lower_path), "artifact": str(self.artifact)},
                {"name": "upper", "mask": str(upper_path), "artifact": str(self.artifact)},
            ],
            "relationships": [
                {
                    "kind": "separation",
                    "upper": "upper",
                    "lower": "lower",
                    "maximum_overlap_pixels": 0,
                    "minimum_gap_px": 4,
                    "maximum_gap_px": 6,
                    "measurement_region": str(region_path),
                    "basis": "independent_evidence",
                    "evidence": str(evidence_path),
                }
            ],
        }
        config_path.write_text(json.dumps(config))
        accepted = run_script("validate_stack.py", config_path, self.root / "separation-pass")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

        config["relationships"][0]["minimum_gap_px"] = 6
        config["relationships"][0]["maximum_gap_px"] = 8
        config_path.write_text(json.dumps(config))
        wrong_gap = run_script("validate_stack.py", config_path, self.root / "separation-gap-fail")
        self.assertEqual(wrong_gap.returncode, 2)
        self.assertIn("minimum gap", wrong_gap.stdout)

        intersecting = upper.copy()
        intersecting[8:24, 14:16] = 255
        cv2.imwrite(str(upper_path), intersecting)
        config["relationships"][0]["minimum_gap_px"] = 0
        config["relationships"][0]["maximum_gap_px"] = 8
        config_path.write_text(json.dumps(config))
        intersection = run_script("validate_stack.py", config_path, self.root / "separation-overlap-fail")
        self.assertEqual(intersection.returncode, 2)
        self.assertIn("overlap", intersection.stdout)


if __name__ == "__main__":
    unittest.main()
