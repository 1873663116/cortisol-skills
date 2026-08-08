---
name: raster-to-editable-svg
description: Reconstruct JPG or PNG references as smooth, independently editable SVG geometry whose silhouettes, landmarks, layer relationships, and curve families agree with the source and design intent.
disable-model-invocation: true
compatibility: Requires Python 3 with the declared image and curve libraries, plus an SVG renderer for visual validation.
---

# Raster to editable SVG geometry

Operate like an illustrator using measurement instruments. Source pixels are evidence, user-stated design intent is a constraint, and the SVG is a new editable geometric model. Scripts perform mechanical work and report evidence; the Agent chooses methods and parameters, judges candidates, and owns every stage transition.

## Work as an evidence-driven loop

At each meaningful stage:

1. inspect the current image, candidate, and evidence;
2. state the relevant interpretation or uncertainty;
3. choose a suitable instrument and task-specific parameters;
4. run the instrument and inspect its visual and numeric outputs;
5. accept the candidate, revise the decision, or try another method.

A candidate advances only after its evidence has been inspected and accepted. Mechanical sweeps may generate several candidates in one call; the Agent compares and selects them. Use the instruments that fit the source and the current uncertainty.

The required evidence follows the source structure. Every delivered shape has source-derived landmark or contour evidence, an exact-final-path curve inspection, and a local geometric comparison. A layered source with occlusion or cast shadows also has an exact-final-layer stack validation. These artifacts form the completion gate for their corresponding claims.

Choose design-affecting parameters explicitly from the current image and decision. Scripts may retain implementation defaults that do not alter the intended geometry, such as output formatting.

Read [toolbox.md](references/toolbox.md) when choosing instruments. Read the stage-specific reference only when entering that stage.

## Prepare the runtime

Verify a Python environment against `scripts/requirements.txt` and verify a direct SVG renderer. Reuse a suitable environment or create an isolated one in the runtime workspace and install the declared requirements. If a required capability is unavailable, report what failed and what it blocks.

## Interpret the source

Inspect the source at original resolution. Determine the requested layers, stacking order, shared landmarks, repeated-shape relationships, intended display sizes, and which boundaries are observed, occluded, or inferred. Classify visible transitions as object silhouettes, occlusion boundaries, cast-shadow bands, or illumination changes. Resolve conflicts between explicit design intent and accidental raster differences before tracing.

Before fitting, record the current geometric claims and acceptance plan in the runtime workspace: observed comparison regions, inferred regions and their construction rules, intended viewing sizes, the task-scale maximum length of one editable Bézier segment, and the numeric and visual evidence that will support each claim. Keep these criteria stable while comparing a set of candidates.

Measure and accept every shape independently before comparing the family. Establish a shared landmark, master, symmetry, or spacing relationship only when the user explicitly requested it or source-derived evidence independent of all candidates supports it. Similar appearance alone is not relationship evidence.

## Recover visible evidence and geometry

Read [mask-and-fit.md](references/mask-and-fit.md).

First recover visible evidence. Keep observed, uncertain or occluded, manually corrected, and inferred regions distinguishable in runtime evidence. Inspect overlays before fitting.

For every partially covered layer, maintain both its observed visible region and its completed support geometry. Cast-shadow bands encode a casting-shape-over-receiving-shape relationship: the receiving geometry continues beneath the casting layer. Build that hidden continuation from the visible arcs, stacking order, curve continuity, and only those shared landmarks or family models that have an authorized basis.

Then choose a contour and fitting method. Compare the fitted path against independently source-derived evidence, never a mask or contour rendered from that candidate. Prefer smooth tangent flow, intentional curvature changes, distributed anchors, stable landmarks, and practical editability. Add anchors where a single cubic would span multiple curvature extrema, sustained tangent changes, distinct visible shape behaviors, or the declared maximum editable segment length. Do not use a fixed minimum anchor count. Anchor count is sufficient when the worst local residual and exact-final curve-structure checks both pass.

Complete hidden boundaries from explicit design constraints, continuity, authorized symmetry, a validated master, or another defensible model, and record them as inferred. When an authorized relationship establishes a shared design grammar, model its common construction, landmarks, curve behavior, and spacing after the independent measurements. Fit closed object geometry to the completed support model while using the observed region as pixel evidence.

Accept each independent shape, then assemble the full stack and inspect interactions among shapes. Occlusion order, intended overlap, negative space, and any authorized shared endpoint or family relationship are part of the geometry. Validate declared overlap and separation relationships inside their source-derived measurement regions so accidental intersections and incorrect gaps fail mechanically. Render a stack-coverage view that makes overlap depth and uncovered regions explicit. Regions explained by occlusion or cast shadow in the source receive continuous object coverage in the geometric stack.

The delivered SVGs express authoritative boundaries as direct vector objects with flat fills. Each independent layer contains its common canvas, its intended geometry, and the paint used by that geometry. The composite reuses the accepted path data and stacking order from those layers.

## Validate the exact result

Read [validation.md](references/validation.md). Validate source agreement, local curve fidelity, cross-shape consistency, editability, and target-editor compatibility as separate gates. Bind measurements to the exact candidate file and chosen evaluation region. Every declared shared relationship receives direct evidence, such as shared landmark coordinates, a normalized curve overlay, or reuse of an accepted master. Any later edit creates a new candidate and receives fresh evidence.

Metrics locate and quantify discrepancies. The Agent grants approval after inspecting the exact candidate at source scale, editing scale, and intended display sizes. The geometry report records a hash-bound source-evidence dependency chain that excludes the candidate SVG and its renders. The curve report records true topological anchors, segment types and lengths, and enforces the predeclared maximum Bézier arc length. Missing, self-referential, mismatched, or failed evidence is `not evaluated` and keeps the stage open.

## Deliver results separately from runtime evidence

Keep source copies, masks, confidence fields, contours, candidates, overlays, differences, metrics, hashes, render logs, and rejected variants in an isolated runtime directory such as `tmp/raster-to-svg/<slug>/`.

Place finished assets in the delivery directory:

```text
<output>/
  layers/             # independently editable SVG layers when requested
  composite.svg       # assembled editable result when requested
  README.md           # concise usage notes only when useful
```

Package runtime evidence separately only when requested. Report inferred geometry, compatibility limitations, and unresolved exceptions in the handoff.

The run is complete only when a final delivery manifest verifies the current file hashes and passing structural, exact-final curve, and independently sourced local-geometry reports for every delivered layer; structural and curve reports for the composite; stack evidence for a layered source; and explicit passing visual-review and target-editor records bound to every current artifact. Missing, stale, or failed reports prevent completion.

Method provenance is recorded in [method-sources.md](references/method-sources.md); execution guidance lives in this file and the stage references.
