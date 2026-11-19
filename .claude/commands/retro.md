---
description: Retrospective — turn this session's friction into durable repo improvements (the compounding loop)
argument-hint: "[optional focus area, e.g. 'wiktionary parsing' or 'test setup']"
---

You just finished a task in this Anki addons monorepo. Run a **compounding-loop
retrospective** so the next task here is closer to one-shot. Be honest and
concrete, and prefer patching the repo over re-explaining things in chat.

Work through these steps:

1. **Diagnose the friction.** Look back over THIS session and name the specific
   things that cost tokens or caused back-and-forth: wrong guesses, missing
   context, repeated verification, commands you had to discover, knowledge you
   re-derived from scratch, edits that matched the wrong site, tests run from
   the wrong directory. Quote concrete moments rather than generalizing.
   If `$ARGUMENTS` is non-empty, focus the retrospective there.

2. **Map each friction point to a principle and a durable artifact.** Apply
   _fast scoped verification_, _knowledge capture_, _edit precision_,
   _cache-stable context_, and _the compounding loop_. For each friction point,
   name the artifact that would have prevented it:
   - a knowledge doc under `docs/` (linked from `docs/README.md`);
   - a test under `<addon>/tests/` or root `tests/`;
   - a `Makefile` target;
   - a lint/CI gate under `.github/workflows/`;
   - `AGENTS.md` — only if the rule is broadly useful and stable, since it is
     auto-loaded in every session.

3. **Check what already exists first.** Read the relevant `AGENTS.md` section,
   `Makefile`, `conftest.py`, `docs/`, `.github/workflows/`, and addon `tests/`
   before adding anything, so you patch real gaps instead of duplicating. Repo
   knowledge belongs in a version-controlled file rather than chat or memory.

4. **Implement the safe, high-leverage fixes now.** Knowledge capture, tests
   pinning corner cases, scoped `Makefile` targets, deduplication, and lint/CI
   gates are usually safe to land immediately. Promote standards up the
   ratchet: prose in `docs/` → a test → a lint/type rule → a CI-blocking
   check — a gate makes the prose redundant, so shrink the prose when you add
   one.

5. **Ask before anything heavy or hard to reverse** — new dependencies, tool
   installs, CI workflow changes, file moves, or outward-facing actions (Anki
   addon publishing, R2 uploads, graph pushes). Present the trade-off and let
   the user choose.

6. **Verify and report.** Run the relevant `make` checks (at minimum
   `make check-py` for Python changes, `make check` for cross-cutting ones,
   `make fmt` for Markdown), keep tests and lint green, and summarize what you
   changed and how it pays off next time. Leave commits to the user unless
   explicitly asked.

7. **Distill the session into a skill delta (ACE step).** Ask: "what did this
   session teach about _how_ to do X?" If the answer generalizes beyond this
   task, edit the existing `.agents/skills/*/SKILL.md` or `AGENTS.md` it
   belongs to rather than spawning a near-duplicate skill. Every line in an
   auto-loaded file is paid for in every session, so a line earns its place
   only if it is a repo/environment fact a capable model cannot infer, a user
   preference, or cheaper than rediscovery. Write it as the fact or goal
   ("`data/` is pipeline output — regenerate it"), rather than a new
   prohibition or an incident story (dates and PR numbers belong in commit
   messages and docs). When the section you touch already covers the point,
   merge or replace instead of appending. Run `python3 tools/sync_commands.py`
   and `make sync-check` after any skill edit.

Guiding test: _a correction given today should be impossible to need next month_
— because it now lives in the repo (a doc, a test, a Makefile target, a gate),
not in this conversation.
