### Opening a PR

Invoked at the end of every other playbook.

**Worktree.** Work from a git worktree off main. `delegate_to_agent` does not create or inherit worktrees. Before dispatching, create one worktree per writer and pass its absolute path as `working_dir`; never point concurrent writers at the same branch or directory. Dirty branch with unrelated work: patch out, fresh worktree, apply. Snarled worktree: start a fresh worktree from main and redo minimally.

**Commits.** Commit liberally; rebase into small, ordered commits before opening PRs. Each commit is a future PR: landable, ordered to tell the story. Amend when the fix belongs in a just-made commit; new commit when separable.

**PRs.** Apply the **unslop** skill to the diff before commit and `/no-comments` before review. Apply **unslop** to the PR description and commit bodies. Small PRs, 5 narrow over 1 fat; stack follow-ups, branch off main only for genuinely independent work. For stacked PRs, use whatever stacking tool your team uses; the principle is small, ordered slices with the stack visible to reviewers. `gh pr view <number>` before referencing PR status. Rebase on `main` before substantial stack work. No `## Summary` / `## Test plan` boilerplate on small PRs; commit bodies don't restate the subject. After opening, run Cursor's built-in **babysit** skill; push back when feedback drifts from intent.

A subagent that opens a PR runs `interrogate`, applies **unslop**, runs `/no-comments`, returns the URL, and does NOT babysit. Return to the parent.
