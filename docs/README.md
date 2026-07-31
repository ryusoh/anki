# Docs index

## Anki knowledge graph

- [anki-knowledge-graph-architecture.md](anki-knowledge-graph-architecture.md) — data flow, GitHub/R2 split, schema (start here)
- [security-protocol.md](security-protocol.md) — private-data protection layers, pre-commit security check, incident response
- [anki-data-fetch.md](anki-data-fetch.md) — `make fetch` / `data/anki/fetch` mechanics
- [fetch-data-lag.md](fetch-data-lag.md) — why `make fetch` can lag behind live Anki edits (WAL)
- [incremental-staging.md](incremental-staging.md) — hash-map-based incremental R2 staging
- [r2-upload-guide.md](r2-upload-guide.md) — R2 staging directory layout and upload
- [r2-sync-guide.md](r2-sync-guide.md) — the `--sync` flag and orphaned-note deletion
- [graph-analysis-guide.md](graph-analysis-guide.md) — `graph/analyze.py` CLI usage
- [deck-aliases.md](deck-aliases.md) — deck alias table (`J`, `C`, `E`, `S`, `T`, `F`)

## Repo-wide conventions

- [creating-an-addon.md](creating-an-addon.md) — anatomy of a self-contained addon + test pattern
- [js-testing.md](js-testing.md) — which JS test suites actually run
- [js-typing-strategy.md](js-typing-strategy.md) — `jsconfig.json`/`checkJs` strict-mode whitelist strategy
- [lint-and-quality.md](lint-and-quality.md) — formatting/lint/type/security gate
- [limited-network.md](limited-network.md) — slow-uplink survival: push retry/chunking, NET_DEADLINE upload caps, `make -n` refusal
- [delegation-specs.md](delegation-specs.md) — how to write a design spec for another agent to implement
- [anki-editor-mathjax-undo.md](anki-editor-mathjax-undo.md) — why Cmd+Z can't restore deleted MathJax in the editor; workarounds

## Historical records

Point-in-time snapshots kept for context, not maintained as living reference —
verify against current code/Makefile before trusting specifics.

- [project-handover.md](project-handover.md) — March 2026 handover doc and security incident writeup
- [git-ignore-audit.md](git-ignore-audit.md) — March 2026 `.gitignore` audit report
- [graph-merger-tdd.md](graph-merger-tdd.md) — TDD build log for the original graph/PageRank module

## Design specs

- [terminal-calendar-ranges.md](terminal-calendar-ranges.md) — year/quarter calendar time filters for the stats terminal
- [precommit-speed.md](precommit-speed.md) — measured baseline + parallelization plan for `make precommit-fix` (SKIP/YOLO)
- [field-snapshot-undo.md](field-snapshot-undo.md) — `field_snapshot_undo` addon spec: field revision ring to recover deleted MathJax
- [auto-itaigi-spec.md](auto-itaigi-spec.md) — `auto_itaigi` addon spec: Taiwanese Hokkien lookup from itaigi.tw
- [free-tts-apis.md](free-tts-apis.md) — research notes on free TTS APIs for AwesomeTTS
- [free-tts-services-spec.md](free-tts-services-spec.md) — AwesomeTTS free-ja/en TTS service integration spec
