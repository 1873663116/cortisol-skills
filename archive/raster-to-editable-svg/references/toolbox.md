# Instrument toolbox

Choose instruments from the source and the current uncertainty. They produce candidates and evidence; none of them approves a stage.

| Instrument | Use it for | Agent decides | Inspect before proceeding |
| --- | --- | --- | --- |
| `segment_layers.py` | Recover candidate-independent visible-region evidence when color is informative | samples, region, Lab tolerance, uncertainty width, morphology, manual corrections | mask, observed region, provenance hashes, confidence, uncertainty, source overlay |
| `extract_contour.py` | Extract an inspectable subpixel contour from a mask or soft field | contour method, iso-level, smoothing, scale | field heatmap and contour overlay |
| `trace_mask.py` | Generate a quick adaptive cubic candidate from a mask | tolerance, segment range, spacing, smoothing, scale | source overlay, anchor structure, local residuals |
| `fit_contour.py` | Generate a globally smooth editable candidate from an accepted contour | smoothing, cubic segment count, intentional corners | control overlay, symmetric contour distance, join continuity |
| `validate_svg.py` | Check the structure of delivered geometry | canvas relationship | reported vector elements and canvas |
| `inspect_svg_curves.py` | Inspect the exact delivered paths | intentional joins, tangent tolerance, minimum spacing, task-scale maximum Bézier arc length | artifact hash, true anchor count, segment types and lengths, join angles |
| `validate_geometry.py` | Compare an exact SVG candidate's rendered silhouette with independently sourced visible evidence | source-evidence provenance, observed region, local-window scale, task-appropriate criteria | dependency hashes, overlap map, edge map, local residual map, exact artifact hash, global and worst-window metrics |
| `validate_stack.py` | Check completed layer support, coverage, and declared overlaps | required-coverage region, layer order, adjacent relationships, criteria | coverage depth, uncovered bands, pairwise overlap metrics, artifact hashes |
| `validate_delivery.py` | Enforce the exact-final completion gate | delivery manifest and required report paths | current artifact hashes, missing or failed gates, one pass/fail decision |
| Direct SVG renderer | Rasterize the exact candidate reproducibly | renderer and output sizes | rendered silhouettes at relevant scales |
| Target editor | Confirm practical editability and import behavior | required editable constructs | paths, handles, transforms, canvases, layer independence |

Alternative tracers such as Potrace or VTracer are valid candidate generators when their input model fits the source. Record their version and parameters and judge them with the same evidence gates. Manual SVG edits are also valid; render and revalidate the edited file before accepting it.

Prefer explicit parameters or an intentional parameter sweep. A sweep automates candidate production; the Agent examines the evidence and chooses the candidate. Preserve the provenance of each candidate that enters comparison. Create comparison criteria before the candidate set so one stable standard judges the alternatives.
