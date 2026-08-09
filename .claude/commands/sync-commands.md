---
description: Regenerate .claude/commands (Claude Code) from the canonical .agents/skills sources
---

`.agents/skills/` is canonical — edit skills there, never `.claude/commands/`.

Progressive disclosure: only the frontmatter `name` + `description` enter an
agent's system prompt; the body is read on demand once the skill triggers. So
the `description` is the only always-loaded surface — write it as a
discriminative trigger ("Use when ..."), and don't contort the body to save
prompt space; length there is free until the skill fires. (Keep `description`
single-line — the generator's frontmatter parser is naive.)

After creating or editing a skill:

1. **Format it** — skill files are Markdown and Prettier owns them; CI's
   `fmt-check` fails otherwise: `make fmt` (or
   `npx prettier --write .agents/skills/<name>/SKILL.md`).
2. **Sync** — `python3 tools/sync_commands.py` (after formatting, so the
   generated copy matches the formatted source).
3. **Verify** — `make sync-check` and `make fmt-check` must both pass.
