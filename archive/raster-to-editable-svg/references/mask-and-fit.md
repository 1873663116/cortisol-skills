# Geometry recovery and curve fitting

## Interpret the raster

A raster edge records a sampled appearance transition. Infer the intended physical boundary from that transition together with antialiasing, compression, resampling, adjacent layers, repeated motifs, and explicit user intent.

Identify candidate landmarks before extracting independent paths, but measure each shape without borrowing geometry from another. Treat shared endpoints, symmetry, repeated profiles, and spacing as hypotheses until the user explicitly requests them or candidate-independent source evidence establishes them.

## Extract visible evidence

Segmentation extracts visible evidence for constructing a complete object. Preserve the distinction between observed candidate foreground, uncertainty or occlusion, and surrounding pixels. Keep manual corrections and inferred completions identifiable alongside measured pixels.

Color-space sampling, soft confidence, connected components, edge cues, interactive foreground extraction, manual corrections, and region restrictions are all valid. The Agent chooses a method and its parameters from the source, inspects its overlay, and either accepts the visible evidence or tries another candidate. When a binary mask supports a mechanical operation, retain its provenance and accompanying uncertainty evidence.

Control pixel stair-steps before fitting. Depending on the material, this can mean estimating a subpixel iso-contour, smoothing a signed-distance field, oversampling a softened mask, or manually drawing through stable landmarks. Inspect the extracted contour over the source before fitting it. Preserve real corners while suppressing sampling noise.

## Reconstruct complete object support

Treat visible-region masks and complete object geometry as separate models. A foreground layer may hide the receiving layer while its cast-shadow band still reveals their depth order. Continue the receiving shape beneath the foreground using its stable visible arcs and the declared construction of the shape family.

Map the stack before closing paths: identify which layer casts onto which receiver, which contours are true outer silhouettes, and which visible transitions sit inside another shape's support. Review the completed support masks together as a coverage-depth image. Intended overlaps appear as depth greater than one; intended negative spaces remain uncovered.

When an authorized relationship exists, establish its source-derived master or normalized family overlay before completing hidden arcs. Otherwise complete and validate each layer from its own visible evidence and declared inference rule.

## Fit editable paths

Use cubic Bézier curves or another SVG-compatible representation that remains practical in the target editor. Anchor count follows the geometry and editing workflow rather than a fixed minimum. Add an anchor when it represents a landmark, intentional corner, curvature extremum, sustained tangent change, distinct local residual, or the predeclared maximum editable Bézier arc length. Consolidate anchors that merely follow noise or create controls too local to edit meaningfully.

Ordinary joins should have visually continuous tangent flow. Stronger continuity may be appropriate for long designed curves. Deliberate corners remain explicit exceptions. Avoid short consecutive segments, alternating curvature, oversized handles, loops, and clusters of anchors without a corresponding source feature.

The bundled tools expose more than one route. `trace_mask.py` provides a quick adaptive cubic candidate. `extract_contour.py` separates contour extraction from fitting, and `fit_contour.py` provides a globally smooth candidate with explicit intentional corners. Choose their design-affecting parameters deliberately. Inspect errors along the curve in local windows. Refine the evidence, model, segment allocation, controls, or anchors wherever the worst window reveals a lost inflection, flattened shoulder, false bulge, or displaced tangent.

## Handle occlusion and reuse

Complete hidden boundaries from declared design constraints, continuity, symmetry, a validated master, or another defensible model. Preserve observed evidence and inferred construction as distinct provenance. Validate observed arcs against source pixels, inferred arcs against their declared constraints, and the assembled support geometry against its required coverage and overlap relationships.

Reuse one master only when explicit design intent calls for identity or candidate-independent source evidence establishes it. Preserve independent paths and independent measurements otherwise; visual similarity is a comparison result, not permission to impose a shared curve grammar.
