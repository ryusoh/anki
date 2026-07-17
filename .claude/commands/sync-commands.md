---
description: Regenerate .claude/commands (Claude Code) from the canonical .agents/skills sources
---

`.agents/skills/` is canonical — edit skills there, never `.claude/commands/`.
Then execute the sync script: `python3 tools/sync_commands.py`.
