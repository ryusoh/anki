---
description: Execute the work orders in an action-items doc one at a time, verifying and committing after each item without pushing. Use when the user points you at a doc containing tagged work orders (Find/Change/Verify) and asks you to implement them.
argument-hint: "[path/to/action-items.md]"
---

# Implement action items

Execute the work orders in **$ARGUMENTS** (or the doc from the conversation)
mechanically, one at a time, in order. You are an implementer, not a designer:
the doc's anchors and snippets were verified by the authoring agent — follow
them literally.

## Per work order

1. **Read the tags.** `[skip]` → skip the item entirely and record it as
   skipped (it is routed to a stronger model). `[visual]` → implement normally,
   but flag "visual — human review required" in your final report (unit tests
   can't see the Anki WebView render).
2. **Match the Find anchor.** Locate the exact `Find` string in the named
   file. If it does not match — even slightly — **stop that item, record the
   mismatch, and move to the next item.** Do not improvise an alternative
   anchor, and do not "fix" the work order.
3. **Make exactly the stated change.** Nothing more: no drive-by edits, no
   refactors, no comment rewording, no touching generated `data/` or vendored
   code (`review_heatmap/libaddon/`, any `_vendor/` tree, minified bundles).
4. **Verify.** Run the item's **Verify** commands from the repo root (the root
   `conftest.py` mocks `aqt`/`anki`; scoped Python runs go through
   `make test-py SUITE=<addon>/tests`, never bare `pytest` inside an add-on
   subdir), plus the doc's preamble formatting/lint commands. If verification
   fails and the item gave a fallback instruction, apply it once; otherwise
   revert your edit for that item (`git checkout -- <the files you changed for
this item>` — only those files, never anything else in the tree), record
   the failure, and move on.
5. **Commit that item only:**
   - `git add <the specific files you changed>` — never `git add -A` or
     `git add .` (other agents' work may share the tree; `precommit-fix`'s
     `YOLO=1`/`MSG=` mode has the same `git add -A` hazard — do not use it).
   - Commit with a Conventional Commits subject
     (`type(scope): summary`, lower-case imperative, ≤ 72 chars; scope is the
     affected add-on/area), referencing the work-order number in the body.
   - **Never push, never amend, never rebase.** Pushing is the human's call.

## Final report

List each work order as done / skipped ([skip] tag) / failed (anchor mismatch
or red verification), with the commit hash for each done item and the failing
command's output for each failed item. Do not claim anything you didn't
verify this run.

## Resume protocol

When resumed, invoked on an in-progress task, or recovering from context compaction:

1. **Never trust conversation memory** for progress tracking.
2. **Inspect authoritative ground truth**:
   - Run `git status --short` and `git log -n 5 --oneline`.
   - Query the task state ledger: `python3 -m tools.task_harness status <task-id>` (or check `.agents/state/<task>.json` / governing doc).
3. **Locate the Program Counter**:
   - Identify the first work order where the corresponding commit/verification is missing.
4. **Re-anchor working memory**:
   - State the current work order number, target file, and entry verification command explicitly before calling tools.

## Unattended runs

For a hands-off sweep, the user may wrap this skill in a goal-mode session
(e.g. a `/goal` whose completion criterion is "all non-`[skip]` items
committed, each item's Verify commands green"). That wrapping is the user's
choice per run — this skill itself stays harness-agnostic and must not require
goal tooling.
