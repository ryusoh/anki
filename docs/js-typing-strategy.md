# JS typing strategy

Why this repo type-checks JS via `jsconfig.json` + `checkJs` instead of
migrating to TypeScript, and how the whitelist grows.

## TL;DR

- **No `.js` → `.ts` migration.** `js/` has **no build step** (see
  `AGENTS.md`'s Layout section); introducing `.ts` would force one.
- **The cheap alternative:** `jsconfig.json` with `"strict": true` and
  `checkJs`, applied to a small, incrementally-growing `include` whitelist.
  JSDoc annotations only — no `.ts`, no runtime change.
- Wired into `make typecheck-js`, part of `VERIFY_GATE` in the `Makefile` (so
  `make verify` / `make precommit SKIP=1` / CI all run it) — **blocking**.
  Since the whitelist starts small, this never fails on an unannotated file
  outside it; it only fails if a whitelisted file regresses.

## Status (2026-07-17) — infra bootstrapped

- Whitelist seeded with `js/utils/host.js` (32 lines, 0 strict errors after
  two `@param` JSDoc annotations).
- `package.json`'s `"imports"` field (`#js/*` → `./js/*`, `#ui/*` →
  `./js/ui/*`) resolves correctly under `moduleResolution: "bundler"` — no
  extra `paths` config needed in `jsconfig.json`.
- Everything else outside the whitelist is unchecked. Expand it
  incrementally: add a file's path to `include` and bring it to zero strict
  errors in the same change, one file at a time.

## Rules

- **Never** use `any`, `@ts-ignore`, `@ts-nocheck`, `@ts-expect-error`, or an
  `eslint-disable` to silence a strict error — type it correctly or leave the
  file out of the whitelist.
- **Never add `@types/node`** — this is browser-facing webview code; Node
  ambient types aren't needed and can drag in unrelated globals.
- `js/vendor/**` is permanently excluded (third-party, not ours to type).
- Shared/global type declarations go in `js/types/*.d.ts` (type-only, `.d.ts`
  files are never served).

## Expanding the whitelist

1. Run `npx tsc -p jsconfig.json` — if it's clean, pick the first-party file
   with the fewest strict errors (check the full-repo scan by temporarily
   setting `include` to `["js/types/*.d.ts", "js/**/*.js"]` with `js/vendor`
   excluded, tally errors per file, then delete the temp config before
   committing).
2. Add that file's path to `include` in `jsconfig.json`.
3. Fix every strict error with JSDoc (`@param`, `@returns`, `@typedef`) —
   never suppress.
4. Confirm `npx tsc -p jsconfig.json` exits 0 and `make typecheck-js` (or the
   full `make verify`) is green.
