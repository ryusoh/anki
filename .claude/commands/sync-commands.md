---
description: Regenerate .claude/commands (Claude Code) from the canonical .agents/skills sources
---

`.agents/skills/` is canonical — edit skills there, keeping `.claude/commands/`
generated.

Only frontmatter `name` + `description` enter the always-loaded prompt; the
body loads on demand. Write `description` as a single-line discriminative
trigger ("Use when ...") and omit `---` horizontal rules from skill bodies
(`tools/sync_commands.py` parses frontmatter via `content.split("---", 2)`).

After creating or editing a skill:

1. **Format it** — Prettier owns Markdown here (`make fmt`, or
   `npx prettier --write .agents/skills/<name>/SKILL.md`).
2. **Sync** — `python3 tools/sync_commands.py` (after formatting, so the
   generated copy matches).
3. **Verify** — `make sync-check` and `make fmt-check` both pass.
