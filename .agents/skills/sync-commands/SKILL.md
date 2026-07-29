---
name: sync-commands
description: Regenerate .claude/commands (Claude Code) from the canonical .agents/skills sources
---

`.agents/skills/` is canonical — edit skills there, never `.claude/commands/`.

After creating or editing a skill:

1. **Format it** — skill files are Markdown and Prettier owns them; CI's
   `fmt-check` fails otherwise: `make fmt` (or
   `npx prettier --write .agents/skills/<name>/SKILL.md`).
2. **Sync** — `python3 tools/sync_commands.py` (after formatting, so the
   generated copy matches the formatted source).
3. **Verify** — `make sync-check` and `make fmt-check` must both pass.
