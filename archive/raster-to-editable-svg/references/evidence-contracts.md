# Mechanical evidence contracts

Use these records to bind source evidence and validation reports to the files they support. Paths may be absolute or relative to the record containing them; every recorded hash is SHA-256.

## Source geometry evidence

`segment_layers.py` writes one `<name>.source-evidence.json` record per layer. Another source-only instrument may emit the same schema:

```json
{
  "schema": "raster-to-editable-svg/source-evidence/v1",
  "producer": "source-only instrument name",
  "candidate_independent": true,
  "source": {"path": "source.png", "sha256": "..."},
  "evidence_mask": {"path": "shape.mask.png", "sha256": "..."},
  "observed_region": {"path": "shape.observed-region.png", "sha256": "..."},
  "derivation_inputs": [
    {"path": "source.png", "sha256": "..."},
    {"path": "segmentation-config.json", "sha256": "..."}
  ]
}
```

`validate_geometry.py` verifies every dependency and rejects the candidate SVG, its render, SVG inputs, mismatched masks, and missing source provenance.

## Relationship evidence

Do not create this record merely because independently accepted shapes look similar. Use it only when source evidence establishes a relationship that the user did not already request.

```json
{
  "schema": "raster-to-editable-svg/relationship-evidence/v1",
  "candidate_independent": true,
  "relationship": {"kind": "separation", "upper": "upper-name", "lower": "lower-name"},
  "source": {"path": "source.png", "sha256": "..."},
  "measurement_region": {"path": "negative-space-region.png", "sha256": "..."},
  "derivation_inputs": [
    {"path": "source.png", "sha256": "..."},
    {"path": "measured-landmarks.json", "sha256": "..."}
  ]
}
```

A stack relationship declares either `"basis": "explicit_request"` with a nonempty `request_reference`, or `"basis": "independent_evidence"` with an `evidence` path to this record.

An overlap relationship declares `"kind": "overlap"` and `minimum_overlap_pixels`. A negative-space relationship declares `"kind": "separation"`, `maximum_overlap_pixels`, `minimum_gap_px`, `maximum_gap_px`, and a source-derived `measurement_region`. The measured minimum distance is the nearest foreground-pixel distance in that region; an intersection reports zero. Independent separation evidence must bind the exact measurement-region hash.

## Delivery manifest

Generate hash-bound JSON reports with `validate_svg.py --output-json`, `inspect_svg_curves.py`, `validate_geometry.py`, and, for layered work, `validate_stack.py`. Then run `validate_delivery.py` with a manifest:

```json
{
  "layered": true,
  "artifacts": [
    {
      "name": "shape-name",
      "role": "layer",
      "artifact": "outputs/layers/shape.svg",
      "path_ids": ["shape-name"],
      "reports": {
        "structural": "evidence/structural.json",
        "curve": "evidence/shape.curves.json",
        "geometry": "evidence/shape.geometry/geometry-metrics.json"
      }
    },
    {
      "name": "composite",
      "role": "composite",
      "artifact": "outputs/composite.svg",
      "path_ids": ["shape-name", "background"],
      "reports": {
        "structural": "evidence/structural.json",
        "curve": "evidence/composite.curves.json"
      }
    }
  ],
  "required_relationships": [
    {"kind": "separation", "upper": "shape-name", "lower": "other-shape"}
  ],
  "stack_report": "evidence/stack/stack-metrics.json",
  "final_reviews": {
    "visual": "evidence/final-visual-review.json",
    "target_editor": "evidence/target-editor-review.json"
  }
}
```

Every layer requires structural, curve, and independently sourced geometry reports. A composite requires structural and curve reports. `path_ids` must exactly match the curve report. A layered manifest additionally declares `required_relationships` explicitly, including an empty list when there are none, and requires a stack report whose layers, current artifact hashes, and relationship set exactly match the manifest.

Each final-review record uses `raster-to-editable-svg/final-review/v1`, has `kind` equal to `visual` or `target_editor`, a passing `decision`, a nonempty list of hash-bound evidence files, and an `artifacts` list containing the exact path and hash of every manifest artifact. Visual state sets `source_scale_inspected`, `editing_scale_inspected`, and `target_sizes_inspected` to true. Target-editor state records a nonempty `editor` and sets `import_succeeded`, `vector_objects_editable`, and `independent_layers` to true.
