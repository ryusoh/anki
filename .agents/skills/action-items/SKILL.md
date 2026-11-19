---
name: action-items
description: Turn a findings/analysis doc into mechanical, anchor-verified work orders that a cheaper implementation agent can execute without interpretation. Use when the user asks to compile, distill, or convert findings/recommendations into action items for later implementation.
argument-hint: "[path/to/findings.md]"
---

# Action items

Convert the improvements in **{{args}}** (or the findings doc from this
conversation) into implementation-ready work orders **in place** inside that
same doc, written so a cheaper implementation model can execute them
mechanically via `/implement-action-items`.

## Verify every anchor first

Read every target file right now and confirm every `Find` string, path, and
snippet against current file contents — spend authoring tokens up front so the
implementer pastes instead of searching or guessing.

## Format

Replace or extend the doc's action-items section with:

1. **Preamble for the implementer:** one work order at a time; `Find` strings
   are unique anchors (report mismatches rather than improvising); line numbers
   may drift; exact format/lint commands (`make fmt`, `make lint-fix`,
   `make fmt-py` for Python); `data/` is pipeline output and vendored trees
   (`review_heatmap/libaddon/`, `_vendor/`, minified bundles) stay untouched;
   commit locally after each item and leave pushing to the user.
2. **Numbered work orders**, ranked by impact, each tagged:
   - `[trivial]` — markup, attribute, or deletion only (include paste-ready
     snippets)
   - `[low]` — small logic change
   - `[visual]` — requires human review in Anki's WebView afterward
   - `[skip]` — requires design judgment or new tests (two-line pointer only;
     routed to a stronger model)

   Each order specifies **File**, **Find** (exact unique anchor), **Change**,
   **Verify** (scoped commands like `make test-py SUITE=<addon>/tests`,
   `make test-addon ADDON=<dir>`, `npx stylelint <file>`), and a one-line
   guardrail for any verified trap (fallback path, execution order, minified
   twin).

## Finish

Format the doc with `make fmt` (Prettier owns Markdown here) and tell the user
where the work orders live and which items are tagged `[skip]`.
