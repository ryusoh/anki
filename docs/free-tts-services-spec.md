# Free TTS services for awesome_tts — design spec (SDD)

| Field    | Value                                                                                                 |
| -------- | ----------------------------------------------------------------------------------------------------- |
| Status   | **Requirements clarification in progress** — core flow decided, no code written; do NOT implement yet |
| Research | `docs/free-tts-apis.md` (ranked candidates, cited quotas/licenses)                                    |
| Target   | `awesome_tts/` itself (user decision 2026-07-31: no second add-on — build on the current one)         |
| Method   | SDD → TDD (red → green); ordered steps to be added after §4 is resolved                               |

Add genuinely free neural TTS covering Japanese and English to `awesome_tts/`,
whose built-in services are mostly paid. The user's only requirement is the
**single-button flow** below; everything else builds on awesome_tts's existing
infrastructure (service registry, audio cache, config, player).

Note on vendoring: `awesome_tts/` is a first-party directory in this monorepo
(with its own `tests/`); the repo's "never touch vendored code" rule covers
`review_heatmap/libaddon/`, `_vendor/` trees, and minified bundles — NOT
`awesome_tts/`. User direction 2026-07-31: extend the current add-on directly;
do not create a wrapper add-on.

## 1. Engine decision (recorded 2026-07-31; user-approved in chat)

| Slot      | Engine                         | Why                                                              | Key risk / cost                                                     |
| --------- | ------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------- |
| ja main   | edge-tts (`ja-JP-*Neural`)     | Best free neural ja, no API key, `pip install edge-tts`          | Unofficial Edge endpoint; can break/vanish any day; no ToS standing |
| ja backup | VOICEVOX (local HTTP engine)   | Best free ja neural, actively maintained, offline, no key/limits | Requires VOICEVOX engine binary running locally (`:50021`)          |
| en main   | edge-tts (`en-*-Neural`)       | Best free neural en, same integration as ja main                 | Same unofficial-endpoint risk                                       |
| en backup | Kokoro-82M (local, Apache-2.0) | Maintained, offline, English is its strongest language           | torch + native `espeak-ng` — heavy in Anki's bundled Python         |

Design logic (failure-mode diversity): both mains share edge-tts's single
risk (unofficial endpoint), so both backups are **local engines** — immune to
endpoint shutdown, network outage, and rate limits. A cloud backup (Azure/Google
free tier) would not survive the same outage as the main.

Explicitly rejected for these slots (evidence in `docs/free-tts-apis.md`):

- **gTTS** — single non-neural voice per language; fallback-of-last-resort only.
- **MeloTTS** — unmaintained since 2024-12; a rotting backup is no backup.
- **Azure F0 / Google Cloud TTS** — official but account+billing-card gated;
  Google has the largest official free quota (1M Neural2 chars/mo) and MAY be
  added later as an optional official-grade service if the user wants zero ToS
  gray zone (see §4, Q1).
- **ElevenLabs free** — 10k credits/mo, non-commercial ToS.
- **Polly / OpenAI** — trial-only / no free tier.

## 2. Single-button flow (DECIDED 2026-07-31, user-approved)

awesome_tts already installs one editor toolbar button
(`awesometts/__init__.py`, `editor_button()` — opens `gui.EditorGenerator`).
That button's behavior changes to:

1. **Single click** — the whole workflow, no dialog:
   a. Read the **Front field** text (HTML-stripped).
   b. **Auto-detect language**: Japanese if the text contains Japanese
   characters (Unicode-range heuristic, local helper inside awesome_tts —
   no cross-addon imports allowed by import-linter); otherwise English.
   c. Generate audio with the language's **main** engine (edge-tts).
   d. On failure (network error, endpoint change, non-200, empty audio):
   **automatically** fall back to the language's **backup** engine
   (ja → VOICEVOX at `localhost:50021`; en → Kokoro).
   e. Insert the resulting `[sound:<file>.mp3]` tag (target field: see §4, Q8).
   f. Tooltip MUST name the engine that produced the audio, and MUST say when
   the backup was used, e.g. `Added audio for '日陰' (edge-tts)` vs
   `(VOICEVOX — edge-tts failed)`.
2. **Double click** — open the existing `gui.EditorGenerator` dialog,
   unmodified. Implementation note: Anki's `addButton` produces a QToolButton
   with no native single/double-click split — disambiguate with a
   `QTimer.singleShot` (~300 ms): first click starts the timer, a second click
   within the window cancels it and opens the dialog instead. This handler
   MUST have tests (single→generate, double→dialog, triple→dialog once).

Failure of BOTH engines → tooltip naming both failures; no field modification.

## 2.1 Vendor update notification (DECIDED 2026-07-31, user requirement)

We own this fork — vendor updates would silently overwrite local changes (the
repo is symlinked into Anki's `addons21`, so an AnkiWeb update replaces the
working tree's files). awesome_tts's `meta.json` currently carries
`"update_enabled": true`, which is Anki's add-on-manager switch for including
the add-on in "Check for Updates".

- `awesome_tts/meta.json` MUST be changed to `"update_enabled": false`.
- Acceptance: a pinned test asserting `update_enabled is false` in
  `awesome_tts/meta.json` (house style: repo-fact pin, cf.
  `tests/test_makefile_*.py`), so a future `meta.json` regeneration or
  upstream sync can't silently re-enable it.
- Note: Anki's add-on manager can also flip this via GUI; the file is the
  deterministic source and the test guards it.

## 3. Integration points inside awesome_tts (verified 2026-07-31)

- **New services** — `awesometts/service/edgetts.py`, `voicevox.py`,
  `kokoro.py`, each subclassing `awesometts/service/base.py:Service` (model:
  `amazon.py`, `azure.py`). Registered per the service `__init__.py`
  convention. Reuses awesome_tts's existing cache/router/player — the
  `[sound:]` file handling and audio caching come free.
- **Button handler** — `awesometts/__init__.py` (`editor_button()` and
  `addAwesomeTTSEditorButton`): swap the click wiring for the
  single/double-click split of §2; the dialog launch stays as-is.
- **Language detection** — small local helper (Unicode ranges), e.g.
  `awesometts/langdetect.py` or inside the button module.
- **Config** — reuse `awesometts/config.py` for per-language main/backup
  service + voice defaults (whether a GUI panel is needed: §4, Q5).

Diff-scope prediction (acceptance criterion): changes confined to
`awesome_tts/` (new service modules, `__init__.py` button wiring, config,
tests) + `requirements.txt` (edge-tts) + this doc. Every other directory MUST
have zero diff (`git status` / `git diff --stat` at the end).

## 4. Open requirements — PENDING user clarification (blocking)

- **Q1 ToS posture.** Is edge-tts's unofficial status acceptable for the main
  slot, or MUST the main be fully official (→ Google Cloud free tier with a
  billing account, or local engines as mains)?
- **Q4 Local-engine deployment.** When a backup engine isn't installed/running:
  (a) detect and disable with install instructions in the tooltip, (b)
  auto-download/launch, or (c) documented manual install only? Kokoro's
  torch+espeak-ng install inside Anki's bundled Python may be impractical — is
  "advanced users only, documented manual install" acceptable for the en
  backup?
- **Q5 Voice defaults + controls.** Which default voices per language
  (e.g. `ja-JP-NanamiNeural`, `en-US-AvaNeural`; which VOICEVOX speaker; which
  Kokoro voice pack), and is a fixed default enough for v1 or MUST the user
  pick voices (via the existing awesome_tts config GUI)?
- **Q6 Dependency policy.** `edge-tts` is a third-party pip package — repo
  rule says non-stdlib deps go in `requirements.txt`; confirm the mechanism
  (documented `pip install` vs vendoring into the add-on).
- **Q7 Cache.** awesome_tts already caches generated audio — confirm: reuse it
  as-is (its key includes service+voice, so main/backup output cannot
  collide), no new cache layer?
- **Q8 `[sound:]` target field.** Append the tag to the **Back** field (like
  auto_wiktionary/auto_itaigi append their output) or to **Front** next to the
  source text?

## 5. Non-goals

- No removal or modification of awesome_tts's existing services (paid or
  otherwise) — only additions plus the button-behavior change.
- No support for engines beyond the four slots in this phase.
- No new dialog for the single-click flow (it is dialog-free by design).
- No mixed-language cards in v1: detection picks ONE language per click
  (Japanese if any Japanese character present, else English).

## 6. Implementation plan

TBD after §4 is resolved. Will include: behavior matrix with worked examples
(ja text, en text, empty field, main-down-fallback, both-down, single vs
double click), ordered red-green steps with verify commands
(`make test-addon ADDON=awesome_tts`, `make typecheck-addon ADDON=awesome_tts`),
and a DO-NOT list (no edits outside `awesome_tts/`; no cross-addon imports;
don't break the existing EditorGenerator path).
