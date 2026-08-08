---
name: write-discoverable-code
description: Use when writing or renaming code to make its definitions and constraints discoverable through plain-text search.
---

# Write discoverable code

Plain-text search is the common baseline for finding code. Write each changed concept so a likely search reaches its authoritative definition and the surrounding text supplies the constraints needed to use it correctly.

## Names are search queries

- Give a symbol the shortest name that searches uniquely in its repository context. Include a domain word when a generic name would collide; give generic verbs their object, such as `sanitizeEmailHtml` rather than `sanitize`.
- Do not rely on a module path to repair an ambiguous symbol name unless the repository has a rigid convention that makes the path authoritative.
- Use one spelling for one concept and reuse the repository's existing vocabulary. Near-synonyms split future searches.
- Keep one authoritative definition site for a symbol. When code moves, remove the old definition in the same change; shared code has one concept-named home.
- Rename when behavior, audience, or visibility changes. A stale name is misinformation at every future search hit.
- Treat filenames as names. Prefer domain-bearing filenames to bare roles such as `config`, `types`, `utils`, `helpers`, or `handlers`; keep `index` as a thin re-export when project convention uses it.

## Types expose constraints

Use the type system when it can make a domain distinction or invalid state visible to the compiler. Examples include branded IDs or newtypes for interchangeable primitives, capability-bearing parameter types for privileged operations, and discriminated unions for state that would otherwise be encoded by nullable fields. Give types domain names that remain meaningful in compiler errors, and avoid unconstrained types where they erase a distinction the caller must preserve.

## Say it where the search lands

- At a definition, add a concise doc comment only for a constraint the name, type, and code cannot show, such as units, timezone, ownership, ordering, or source-time semantics. Include the natural-language phrase people are likely to search when the identifier itself will not match it.
- A caller should understand an imported symbol's contract from its name, type, and necessary definition comment without opening its implementation.
- Keep externally observed event names, flags, error codes, and stable message prefixes as searchable literals. A value seen in a log or external system should search back to its source.
- Give each question-sized concept one named home. Keep orchestrators thin enough to point to the implementation, split files that answer unrelated questions, and keep helpers that only serve one concept with that concept.
- Follow the repository's test-layout convention while keeping behavior and its tests reachable from the same search path.
- Mark obsolete paths with `@deprecated` or the repository's equivalent and point to the replacement.

The change is complete when an expected plain-text query finds each changed concept, the definition exposes the contract a caller must preserve, and moved or renamed definitions no longer leave an unmarked old path.
