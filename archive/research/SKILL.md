---
name: research
description: Investigate a question against high-trust primary sources and return evidence-backed findings to the caller, persisting a report only when it has standalone value.
---

Spin up a **background agent** to do the research, so the caller can keep working while it reads.

Its job:

1. Investigate the question against **primary sources** — official docs, source code, specs, first-party APIs — not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Return a concise synthesis with the evidence for each material claim, source links, disagreements, version boundaries, and unresolved questions.
3. Follow the caller's output contract. When another skill needs the findings inside its own artifact, return them to that skill without creating a second permanent document.

Create a standalone Markdown report when the user directly requests research, the caller explicitly asks for one, or the question and evidence have independent reuse or continued-investigation value. Save it where the repo already keeps such reports; match the existing convention, and if there is none, put it somewhere sensible and say where.
