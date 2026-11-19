---
name: research
description: Investigate a question against primary sources and write a cited Markdown findings doc. Use when the user asks you to research, investigate, or gather authoritative background on a topic.
---

# Research

Investigate a question thoroughly against **primary sources** and capture the
findings as a single cited Markdown file, so the answer is durable and
re-checkable instead of living only in chat.

## Run it in the background

Delegate the investigation to a background subagent so you can keep working
while it runs. Give it the question, the primary sources to prefer, and the
output location decided below.

## Investigate

- Consult **official documentation, source code, specifications, and first-party
  APIs**, tracing every claim to its authoritative origin rather than to
  secondary write-ups.
- For this repo's own subsystems, the primary source is the addon source itself
  plus the governing doc under `docs/` (AGENTS.md maps them).
- For Anki behavior (hooks, collection schema, WebViews), the primary sources
  are the Anki source (`anki`/`aqt`) and the official addon docs at
  <https://addon-docs.ankiweb.net>.
- For Claude / Anthropic API questions, use the `claude-api` skill as the
  primary source.

## Document

Compile findings into **one Markdown file** with a source citation for each
claim (URL, file path, or spec section). Structure: the question, the answer,
then claim-by-claim evidence with citations, and an explicit "open questions /
what I couldn't verify" section.

## Store

Save following this repo's convention: durable subsystem knowledge lives under
`docs/`. Extend an existing doc when the finding fits there (e.g.
`docs/js-testing.md`, `docs/graph-analysis-guide.md`); for a genuinely new
area, add `docs/<topic>.md`, link it from `docs/README.md` (enforced by
`tests/test_docs_index.py`), and format with `make fmt`. For throwaway
investigation, use the session scratchpad instead.

## Output constraints

- Quote verbatim source language sparingly — **max ~125 characters** per quote,
  in quotation marks; paraphrase otherwise.
- Respect open-source licenses and omit reproducing whole files or long
  passages.
- Report what you found and what you couldn't verify, leaving gaps explicit
  rather than guessing.
