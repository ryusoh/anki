# Writing a design spec another agent will implement

How to write a spec (a `docs/*.md` design doc) when the research/design is done
by one agent and the implementation is delegated to a cheaper/smaller one.
Distilled from the calendar-time-filter feature (2026-07-11):
`docs/terminal-calendar-ranges.md` is the worked example — a two-phase spec
whose Phase 2 was implemented by a smaller model with zero design deviations
and zero source edits outside the predicted files.

## What made delegation work (keep doing these)

1. **Verify every load-bearing claim before writing it, and cite evidence.**
   The spec's core claim ("the router needs zero changes — every range
   position is gated by `isValidRange`") was verified by trace before
   writing. Payoff: 5/7 of the implementer's new routing tests passed
   _before it touched the router at all_, and it knew that was expected
   rather than suspicious.
2. **Predict the diff scope and make it an acceptance criterion.** "Source
   changes ONLY in X and Y; file Z has zero diff" + a `git diff --stat`
   check. This is the single best guard against a smaller model wandering:
   when a test failed, the spec could say "the bug is in step 1, not in
   `due.js` — do not edit `due.js`."
3. **Include reference implementations for the genuinely tricky code**
   (parsers, date math, boundary tables) — near-complete, lint-conformant
   snippets. Prose descriptions of tricky logic invite drift; code doesn't.
   For everything else, surgical edit instructions are enough.
4. **Behavior matrix with worked examples** whose expected values come from
   independent hand computation (e.g. "2027 from today 2026-07-11 → offsets
   174..538"). These become test expectations that can actually disagree
   with the implementation.
5. **DO-NOT list with the reason attached** ("the reviews array has 17 date
   gaps — never index arithmetic"). Reasons survive; bare prohibitions get
   second-guessed.
6. **Ordered red-green steps, each with its verify command**, plus explicit
   "known intermediate state" notes ("after step 1 calendar tokens route but
   render full history — acceptable mid-branch, do not stop here").
7. **Document known pre-existing failures** (with how you confirmed they
   predate the branch, e.g. `git stash` + rerun) so the implementer doesn't
   burn a session chasing unrelated red. Put repo-wide ones in
   `docs/js-testing.md`, not only in the feature spec.

## The two lessons that cost a full extra round-trip

1. **Parity cuts need explicit user sign-off, up front.** The request was
   "equivalent implementation" of a reference system. The spec cut the
   reference's colon syntax (`2020:2023`, `f:2026`, `to:2028`) based on a
   wrong classification ("multi-token" — it is single-token) and hedged only
   in a buried Open Questions section. The user came back for parity, which
   meant a second spec + second implementation pass. Rule: **enumerate the
   reference's complete user-facing surface as a table with a ported/cut
   status per row, and get the cuts explicitly approved before anyone
   implements.** A hedge in "open questions" is not sign-off.
2. **Cite anchors, not just line numbers.** Line-number citations
   (`handler.js:318,463,...`) drift the moment earlier edits land. Phase 2's
   mitigation worked and is now the rule: cite the **construct name or a
   unique literal** first, line numbers as hints only, and tell the
   implementer "re-verify each cited line before editing; if drifted, locate
   by name."

## Mechanical checklist for the doc itself

- Run `make fmt` after hand-authoring — Prettier owns markdown table/list
  formatting and `make fmt-check` will fail otherwise (see AGENTS.md).
- **No bare double-open-braces anywhere in the file** — not even inside code
  fences or inline code. GitHub Pages builds every non-dot-directory
  markdown file with Jekyll **3.10**, whose Liquid pass either crashes the
  whole Pages build (JSDoc `@typedef` braces did this twice on 2026-07-11)
  or silently blanks the span (Anki template-field syntax). The
  `render_with_liquid: false` front matter does NOT work — it's a Jekyll 4
  feature that 3.10 ignores. Either wrap the span in
  `{% raw %}`…`{% endraw %}` tags or reword to avoid the braces. Gated by
  `tests/test_docs_liquid_guard.py`.
- Keep a **Status** row in the header table and update it when a phase
  ships; "design complete, no code written" sitting on top of shipped code
  misleads the next reader. Tick acceptance-criteria checkboxes with what
  was _actually_ verified (and say what wasn't — e.g. "not manually
  exercised in the live UI").
- RFC 2119 keywords (MUST/SHOULD/MAY) + numbered sections give the
  implementer unambiguous cross-references ("§14.3 says do not edit this
  file").
