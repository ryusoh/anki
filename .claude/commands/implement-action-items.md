---
description: Execute the work orders in an action-items doc one at a time, verifying and committing after each item without pushing. Use when the user points you at a doc containing tagged work orders (Find/Change/Verify) and asks you to implement them.
argument-hint: "[path/to/action-items.md]"
---

# Implement action items

Execute the work orders in **$ARGUMENTS** (or the doc from the conversation) in
order, one at a time. You are the implementer: the authoring agent verified the
anchors and snippets, so apply them literally and report anything that fails to
match rather than redesigning it.

Invoking this skill (including via a `/goal` wrapper, though the skill stays
harness-agnostic) authorizes a local commit per verified work order. Pushing
stays with the user.

## Per work order

1. **Tags.** `[skip]` → record as skipped (routed to a stronger model).
   `[visual]` → implement, and flag "visual — human review required" in the
   report (unit tests cannot observe Anki's WebView render).
2. **Anchor.** Find the exact `Find` string in the named file. If it fails to
   match exactly, record the mismatch and move to the next item — the doc's
   author fixes work orders, not you.
3. **Change.** Make exactly the stated change and nothing else; leave `data/`
   and vendored trees (`review_heatmap/libaddon/`, `_vendor/`, minified
   bundles) untouched.
4. **Verify.** Run the item's Verify commands from the repo root (root
   `conftest.py` mocks `aqt`/`anki`; scoped Python runs go through
   `make test-py SUITE=<addon>/tests`) plus the preamble's format/lint
   commands. On failure, apply the item's fallback once if it has one;
   otherwise undo only your edits for that item (confirm with `git diff <file>`
   that every hunk is yours), record the failure, and move on.
5. **Commit that item alone.** Stage by name (`git add <files you changed>`;
   leave `precommit-fix` `YOLO=1`/`MSG=` unused since it runs `git add -A`),
   commit with a Conventional Commits subject (`type(scope): summary`, ≤ 72
   chars) referencing the work-order number in the body. Each item gets its own
   new commit — leave earlier commits and the remote as they are.

## Final report

List each work order as done (commit hash) / skipped (`[skip]`) / failed
(anchor mismatch or red verification, with the failing command's output).
Report only what you verified this run.

## Resume protocol

After an interruption or compaction: check `git status --short`,
`git log -n 5 --oneline`, and the state ledger
(`python3 -m tools.task_harness status <task-id>` or `.agents/state/<task>.json`
/ governing doc) to locate the first work order without a commit. State its
number, target file, and Verify command before calling tools.
