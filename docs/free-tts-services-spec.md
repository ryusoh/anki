# Free TTS services for awesome_tts — design spec (SDD)

| Field    | Value                                                                                                                                                |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Status   | **Implemented** — code written and gate-green; root `conftest.py` extended with Qt stubs so the add-on's GUI classes can be unit-tested outside Anki |
| Research | `docs/free-tts-apis.md` (ranked candidates, cited quotas/licenses)                                                                                   |
| Target   | `awesome_tts/` itself (user decision 2026-07-31: no second add-on — build on the current one)                                                        |
| Method   | SDD → TDD (red → green); ordered steps in §6                                                                                                         |

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
   a. Read the **Front field** text (HTML-stripped with AwesomeTTS's own
   `addon.strip.from_note` sanitizer — the same pipeline the dialog uses:
   tags, `&nbsp;`-style entities, clozes, `[sound:]` tags all handled. A
   naive tag-regex leaves `&nbsp;` literal and edge-tts reads it aloud).
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

## 2.2 Dialog service list (DECIDED 2026-07-31, user requirement)

The three new services MUST also appear in the existing dialog
(`gui.EditorGenerator` etc.), alongside all existing services — but **at the
top of the service dropdown and visually distinguishable**.

Verified mechanism (`awesometts/router.py:get_services` →
`awesometts/gui/base.py:_ui_services`): the dropdown is populated in the
order `get_services()` returns, which is alphabetical by display name
(`key=lambda service: service[1].lower()`). So:

- **Top placement** — `get_services()` MUST pin the three new svc_ids first
  (edgetts, voicevox, kokoro), existing services keep their alphabetical
  order after them. Implement as an explicit pin-list, not a name hack.
- **Highlight** — two layers, both cheap: (a) each new service's display name
  carries a distinguishing marker (star prefix, e.g. `★ Edge-TTS (free)`),
  and (b) `_ui_services` renders those items **bold** via
  `dropdown.setItemData(index, font, Qt.FontRole)` using the same pin-list.
  Keep this the ONLY `gui/` change in the whole feature.
- Tests: dropdown order (first three entries are the new services, rest still
  alphabetical) and the bold/marker presence on exactly those entries.

## 2.3 Runtime dependency bootstrap (DECIDED 2026-07-31, user requirement)

Supersedes the manual install in §4 Q6: after real-Anki testing showed
edge-tts failing (Anki's bundled Python is frozen — no pip), the user
required zero-setup operation ("just open Anki and use it").

- `awesometts/deps.py` puts `<Anki2>/awesome_tts_deps/` (a sibling of
  `addons21`, outside the git tree) on `sys.path` at add-on load.
- If edge-tts is still missing, a daemon thread installs it with an external
  python3's pip using `--python-version <Anki's X.Y> --only-binary=:all:
--platform <mac tags> --target`, so it works even when no python on PATH
  matches Anki's interpreter (verified: Homebrew py3.14 cross-installing for
  Anki's py3.13). Install is staged in a temp dir and renamed atomically.
- Silent by design: success needs no restart (next click works); failure
  surfaces via the existing §2 failure tooltips.
- **Blocked-network fallback (added 2026-08-01):** the edge-tts service
  retries a failed direct connection once through a detected local proxy
  (aiohttp ignores proxy env vars, so the proxy URL is passed to
  `Communicate(proxy=...)` explicitly). Port probing is the vendored,
  byte-identical `awesome_tts/proxy_fallback.py` (canonical:
  `shared/proxy_fallback.py`; sync pinned by
  `tests/test_proxy_fallback_sync.py`). HTTP-level errors are not retried —
  they reached the server.

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
tests) + `requirements.txt` (edge-tts) + root `conftest.py` (Qt stub
additions needed to collect the new add-on tests) + `.coveragerc` (explicit
per-file omit of the untested legacy awesome_tts tree so the combined floor
stays ≥ 75%; the list doubles as Testpilot's coverage work queue) +
`docs/README.md` (index links) + this doc. Every other
directory MUST have zero diff (`git status` / `git diff --stat` at the end).

## 4. Requirements — RESOLVED 2026-07-31 (user answers, verbatim intent)

- **Q1 ToS posture → edge-tts accepted as main.** Unofficial status is fine.
- **Q4 Local-engine deployment → manual install, "just make it work".** The
  user is the only user. No auto-download, no install UX: if a backup engine
  isn't reachable, the both-engines-failed tooltip (§2) names it. Setup steps
  go in the add-on README comment/doc only. **Amended 2026-08-01:** silent
  auto-download/auto-launch was prototyped and rejected — the VOICEVOX engine
  archive is ~1.8 GB, too heavy to pull invisibly at add-on load. Manual
  setup is documented in §7; the failure tooltips point there. (The
  edge-tts _pip package_ bootstrap in §2.3 stays automatic — it is ~7 MB.)
- **Q5 Voices → fixed defaults, no picker in v1.** Defaults: edge-tts ja
  `ja-JP-NanamiNeural`, edge-tts en `en-US-AvaNeural`. VOICEVOX speaker id and
  Kokoro voice pack are chosen at implementation time by querying the local
  engine (`/speakers` / installed packs) — do NOT hardcode an unverified id.
- **Q6 Dependency → `requirements.txt` + documented one-time
  `pip install edge-tts`** into Anki's Python (repo rule: third-party packages
  are declared in `requirements.txt`; Anki bundles some itself but not
  edge-tts). Vendoring rejected: edge-tts pulls an aiohttp/certifi tree —
  heavy and unreviewable. Import edge-tts lazily inside the service so the
  add-on still loads (and existing services keep working) when it's missing;
  the missing-dep path produces the §2 failure tooltip. **Amended 2026-07-31:**
  the manual install proved impossible (Anki's bundled Python is frozen);
  installation is now fully automatic via §2.3.
- **Q7 Cache → reuse awesome_tts's existing cache as-is.** Its key already
  includes service+voice, so main/backup output cannot collide. No new cache
  layer.
- **Q8 `[sound:]` target → Back field, standalone new line at the end.**
  If Back is non-empty: append `<br>` + `[sound:<file>]`; if empty: just the
  tag. Never reorder or touch existing Back content. **Amended 2026-07-31
  (real-Anki testing):** (a) the file MUST be copied into `collection.media`
  via `editor._addMedia(path)` — exactly like AwesomeTTS's own dialog — and
  the tag built from its return value; a tag pointing at the AwesomeTTS cache
  renders but plays nothing (mute bug). (b) The new line is a `<div>` block,
  NOT `<br>`: after block-ending content (`</div>`) a `<br>` renders as a
  blank line, adjacent blocks never do. Trailing `<br>`/whitespace runs at
  the end of Back are collapsed before appending for the same reason.

## 5. Non-goals

- No removal or modification of awesome_tts's existing services (paid or
  otherwise) — only additions plus the button-behavior change.
- No support for engines beyond the four slots in this phase.
- No new dialog for the single-click flow (it is dialog-free by design); no
  voice picker UI in v1.
- No mixed-language cards in v1: detection picks ONE language per click
  (Japanese if any Japanese character present, else English).

## 6. Implementation plan (TDD, red → green)

Behavior matrix (each row becomes a test; mocked engines, no network):

| #   | Front field       | Main result     | Expected outcome                                                |
| --- | ----------------- | --------------- | --------------------------------------------------------------- |
| 1   | `日陰` (ja)       | edge-tts ok     | Back += `<div>[sound:x.mp3]</div>`, tooltip names edge-tts      |
| 2   | `apple` (en)      | edge-tts ok     | same, en voice                                                  |
| 3   | `日陰`            | edge-tts raises | VOICEVOX used; tooltip `VOICEVOX — edge-tts failed`             |
| 4   | `apple`           | edge-tts raises | Kokoro used; tooltip names Kokoro                               |
| 5   | `日陰`            | both raise      | tooltip names BOTH failures; Back byte-identical                |
| 6   | empty Front       | —               | tooltip "no text"; no engine call, no field change              |
| 7   | `日陰` twice      | edge-tts ok     | 2nd click served from awesome_tts cache (engine called once)    |
| 8   | Back = `existing` | edge-tts ok     | result is `existing<div>[sound:x.mp3]</div>` — prefix preserved |
| 9   | single click      | —               | flow runs, dialog NOT opened                                    |
| 10  | double click      | —               | dialog opened, flow NOT run                                     |
| 11  | `meta.json`       | —               | pinned test: `update_enabled is false` (§2.1)                   |
| 12  | dialog dropdown   | —               | first 3 entries are the new services, rest alphabetical (§2.2)  |
| 13  | dialog dropdown   | —               | new-service entries carry the star marker + bold font (§2.2)    |

Ordered steps (each: write failing test(s) → implement → verify):

1. **Scaffold + vendor-update pin.** Create `awesome_tts/tests/` (house
   pattern: per-addon tests dir, collected by `make check-py`); first test is
   row 11 (`meta.json` `update_enabled is false`) — red, then flip the flag.
2. **Language detector** — small local helper (Unicode ranges; ja if any
   hiragana/katakana/kanji, else en) + unit tests incl. empty/mixed input.
3. **`service/edgetts.py`** — `Service` subclass; lazy `import edge_tts`;
   ja/en default voices from Q5; errors surface as service failure (not
   crash). Tests mock `edge_tts.Communicate`; missing-package path tested via
   import patching.
4. **`service/voicevox.py`** — stdlib `urllib` against `localhost:50021`
   (`/audio_query` → `/synthesis`, or `/synthesis` mora API per engine
   version); speaker id from `/speakers` at first use. Tests mock `urlopen`.
5. **`service/kokoro.py`** — CLI/library invocation of the local Kokoro
   install; failure if binary/module absent. Tests mock the subprocess/import.
6. **Register services** in `awesometts/service/__init__.py` (pattern:
   `from .amazon import Amazon`). Verify rows 1–2 against the Service base
   contract (cache reuse = row 7).
7. **Dialog ordering + highlight** — pin-list in `router.get_services()` and
   star/bold item data in `gui/base.py:_ui_services` (rows 12–13).
8. **Button handler** in `awesometts/__init__.py` (`editor_button()` /
   `addAwesomeTTSEditorButton`): QTimer single/double-click split, flow per
   §2, failover per §2 step 1d, Q8 append. Rows 3–6, 8–10.
9. **Gate** — `make test-addon ADDON=awesome_tts`,
   `make typecheck-addon ADDON=awesome_tts`, then full `make precommit SKIP=1`.
   Manual: reload add-on in Anki, click once on a ja card and an en card
   (mocked tests cannot prove real-Anki behavior).

DO-NOT list:

- Do NOT edit existing services or any directory outside `awesome_tts/`
  (except `requirements.txt` + this doc). The ONLY permitted `gui/` change is
  the §2.2 service-list highlight in `gui/base.py` — no dialog layout changes.
- Do NOT import across add-ons (import-linter) — the detector is a local copy.
- Do NOT auto-download or auto-launch engines (Q4).
- Do NOT hardcode a VOICEVOX speaker id without querying `/speakers` (Q5).
- Do NOT reorder/modify existing Back content (Q8) — append only.

## 7. Local engine setup (manual, one-time)

Auto-download was rejected (§4 Q4, 2026-08-01): the backup engines are only
needed when edge-tts is down, and their installers are far too heavy to fetch
invisibly. Set them up once, by hand, if you want the failover paths live.

### VOICEVOX (Japanese backup, `localhost:50021`)

**Easiest — the app:** download VOICEVOX from <https://voicevox.hiroshiba.jp/>
and launch it; the app starts its engine on `:50021` automatically. Keep the
app (or its engine) running while using Anki.

**Headless — engine only (verified 2026-08-01, engine 0.25.2, ~1.8 GB):**

```sh
curl -LO "https://github.com/VOICEVOX/voicevox_engine/releases/download/0.25.2/voicevox_engine-macos-arm64-0.25.2.7z.001"
brew install sevenzip                       # macOS has no built-in 7z
mv voicevox_engine-macos-arm64-0.25.2.7z.001 voicevox.7z   # single-part archive
7z x voicevox.7z
./macos-arm64/run &                          # listens on :50021
```

Either way, verify with `curl http://localhost:50021/version`. The add-on
picks a speaker automatically from `/speakers` (§4 Q5) — no id to configure.

### Kokoro (English backup)

Kokoro needs a native `espeak-ng` plus pip packages in Anki's Python (frozen
— so install into the deps dir from an external python3, the same pattern
§2.3's bootstrap uses):

```sh
brew install espeak-ng
python3 -m pip install --target "$HOME/Library/Application Support/Anki2/awesome_tts_deps" \
    --only-binary=:all: --python-version 3.9 \
    --platform macosx_11_0_arm64 --platform macosx_11_0_universal2 \
    --platform macosx_10_13_universal2 --platform macosx_10_9_universal2 \
    kokoro soundfile torch
```

Notes: torch is the heavy piece (~100 MB+ wheel); the Kokoro voice model
downloads from Hugging Face on first synthesis. This path is documented but
**untested on this machine** — the English backup is optional; edge-tts (§2.3)
covers the main flow.
