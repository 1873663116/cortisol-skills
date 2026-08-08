# Geometry acceptance and runtime evidence

Read [evidence-contracts.md](evidence-contracts.md) when producing source provenance or the final delivery manifest.

Acceptance covers source agreement, cross-shape consistency, editability, and target-editor compatibility. Each gate supports a distinct claim.

## Geometry gate

Render the candidate as a plain silhouette in the source canvas and coordinate system. Compare masks and edge positions inside regions where the source supports a geometric claim, then inspect the actual curves over the source.

Review landmarks, alignment, spacing, silhouette, corners, tangent flow, curvature extrema, and occluded completions for each shape independently. Measure both minimum anchor spacing and the predeclared task-scale maximum Bézier arc length so dense nodes and abnormally long editable spans cannot hide behind aggregate pixel scores. Report topological anchor and segment counts explicitly. Mark the joins that are intentional corners; ordinary joins should remain smooth.

Partition each observed boundary into local arc windows and inspect the worst windows rather than only their global average. A sufficient path preserves every stable curvature transition visible at source scale. Add or redistribute anchors when one cubic flattens a shoulder, merges separate curvature behaviors, introduces a false bulge, or moves a tangent across a sustained arc.

An accepted path has smooth intended flow, explained corners, stable curvature, meaningful anchor placement, and agreement with the declared design relationships. Local defects remain visible in overlays even when a global score is strong.

The source image and observed geometry evidence share provenance that is independent of the candidate. Record their hashes and derivation inputs, reject any evidence chain containing the candidate SVG or its render, and bind the comparison to the exact candidate hash. Regenerate the render, curve inspection, local-window measurements, and stack evidence after every edit. Criteria recorded before candidate generation remain the comparison standard for that candidate set.

## Consistency gate

Inspect the assembled geometry as a system only after its shapes pass independently. Check stacking order, intended intersections, negative-space rhythm, and any authorized shared landmarks or curve grammar. A relationship enters validation only from an explicit user request or source-derived evidence independent of every candidate; give it direct evidence such as measured landmark coordinates or a source-derived normalized overlay.

Occluded boundaries are judged against their declared construction: continuity, symmetry, a shared master, or another explicit model. The runtime record identifies which arcs are observed and which are inferred.

For a layered source, validate the complete support stack as well as the visible composite. Produce a coverage-depth view from the independent layer masks. Mark the source regions whose pixels express overlap, cast-shadow, or negative-space relationships. Measure required overlap inside overlap regions and maximum intersection plus permitted gap inside separation regions. Inspect uncovered bands at normal scale; their width directly tests whether hidden geometry was completed far enough.

## Editability gate

Open or inspect the SVG as the target editor will. Confirm that intended shapes remain editable vector objects, canvases and transforms are predictable, and independently adjustable layers remain independent.

Judge whether a human can make meaningful local adjustments without untangling dense nodes, microscopic segments, extreme handles, or unnecessary compound structures. The most editable path is the simplest path that preserves the intended geometry, not the path with the fewest anchors in isolation.

## Final visual gate

Render the final SVG directly at source resolution and at the sizes that matter for use. Normalize canvas, crop, scaling, renderer, and color handling before comparison.

Choose and record the region that supports the claim. Use complementary comparisons:

- a same-canvas alpha overlay to reveal registration drift;
- an edge or silhouette overlay to isolate geometric displacement;
- a coverage-depth view to reveal missing support and unintended gaps between layers;
- a flicker or rapid A/B comparison to expose movement and shape changes;
- a side-by-side view for overall composition and family character.

Inspect the result at normal viewing scale as well as magnified scale. Return to the relevant evidence, contour, construction rule, or path whenever a visible defect remains at an intended size.

## Metrics and decisions

IoU and bidirectional edge distance are useful geometric signals. Select metrics and thresholds from source quality, image scale, intended output size, and the user's fidelity claim. Declare them before judging the result and keep them stable while comparing candidates.

The Agent makes the acceptance decision from the full evidence set. Scripts report facts and mechanical checks. Each delivered layer requires exact-final structural, curve, and independently sourced local geometric evidence. A composite requires exact-final structural and curve evidence, and layered geometry additionally requires exact-final stack evidence. The final manifest also requires visual-review and target-editor records with explicit passing state, evidence-file hashes, and the exact path and hash of every current artifact. Missing evidence, self-reference, a hash mismatch, a failed report, or an uninspected result is `not evaluated` and keeps the stage open.

## Runtime evidence

Keep the evidence needed to reproduce and review the decision together in the runtime workspace. It normally includes the source checksum, observed and uncertain evidence, contours, candidate SVGs, anchor overlays, same-canvas overlays, difference images, direct renders, metrics, renderer identity, candidate hashes, and a concise accept or reject record.

Runtime evidence is temporary by default. If the user requests it, copy or archive the evidence as a separate artifact. The ordinary result directory contains only finished SVG assets and concise usage notes.

## Structural checks

Require a valid numeric viewBox, explicit dimensions, nonempty direct vector geometry, flat paint, and a structure suitable for direct path editing. Each independent layer contains the definitions it uses. Confirm matching canvases across separately delivered layers and the composite when the task requires assembly without registration work.
