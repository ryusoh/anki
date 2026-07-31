# Free TTS services for awesome_tts — design spec (SDD)

| Field    | Value                                                                                                 |
| -------- | ----------------------------------------------------------------------------------------------------- |
| Status   | **Requirements clarification in progress** — decision recorded, no code written; do NOT implement yet |
| Research | `docs/free-tts-apis.md` (ranked candidates, cited quotas/licenses)                                    |
| Target   | `awesome_tts/` add-on (service layer: `awesome_tts/awesometts/service/`)                              |
| Method   | SDD → TDD (red → green); ordered steps to be added after §3 is resolved                               |

Add genuinely free neural TTS services covering Japanese and English to
`awesome_tts/`, whose built-in services are mostly paid or defunct. Each
language gets a **main** service (best quality-per-effort) and a **backup**
service (immune to the main's failure mode).

## 1. Decision (recorded 2026-07-31; user-approved in chat)

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
  gray zone (see §3, Q1).
- **ElevenLabs free** — 10k credits/mo, non-commercial ToS.
- **Polly / OpenAI** — trial-only / no free tier.

## 2. License/attribution facts to surface in the UI (not legal advice)

- VOICEVOX generated audio carries per-voice-library usage terms and credit
  notation requirements (voice-character dependent). The add-on MUST surface
  the chosen library's credit terms somewhere user-visible (config dialog or
  README), per the facts cited in `docs/free-tts-apis.md`.
- edge-tts is LGPLv3 (library); the endpoint is undocumented — flag in the
  config UI as "unofficial, may break".

## 3. Open requirements — PENDING user clarification (blocking)

Nothing below is decided. Each item needs an explicit user answer before the
spec gets its ordered red-green steps (parity-cut rule from
`docs/delegation-specs.md`: a hedge here is not sign-off).

- **Q1 ToS posture.** Is edge-tts's unofficial status acceptable for the main
  slot, or MUST the main be fully official (→ Google Cloud free tier with a
  billing account, or local engines as mains)?
- **Q2 Failover semantics.** Automatic fallback to the backup when the main
  errors/times out (with a tooltip noting which engine produced the audio), or
  manual service selection only (awesome_tts's current model)?
- **Q3 Integration shape.** New services inside `awesome_tts/awesometts/service/`
  (its registry pattern) vs a thin separate add-on? awesome_tts's config GUI
  must at minimum expose: per-language main/backup selection and voice choice.
- **Q4 Local-engine deployment.** How should the add-on handle engines that
  aren't running? Candidates: (a) detect `localhost:50021`/import failure and
  disable the service with instructions, (b) auto-download/launch the engine,
  (c) document manual install only. Kokoro's torch+espeak-ng install inside
  Anki's bundled Python may be impractical — is "advanced users only,
  documented manual install" acceptable for the en backup?
- **Q5 Voice defaults + controls.** Which default voices per language
  (e.g. `ja-JP-NanamiNeural`, `en-US-AvaNeural`; which VOICEVOX speaker; which
  Kokoro voice pack), and MUST speed/pitch controls be exposed or is
  rate-only enough?
- **Q6 Dependency policy.** `edge-tts` is a third-party pip package — repo
  rule says non-stdlib deps go in `requirements.txt`; confirm that's the
  intended mechanism inside Anki (user_files vendoring? documented
  `pip install`?) rather than vendoring the package.
- **Q7 Cache/dedup.** awesome_tts caches audio by text+service+voice. MUST the
  cache key distinguish engine identity so main/backup output never collides?

## 4. Non-goals

- No replacement of awesome_tts's existing services (paid or otherwise).
- No support for engines beyond the four slots above in this phase.
- No GUI redesign — minimal additions to the existing config dialog.

## 5. Implementation plan

TBD after §3 is resolved. Will include: diff-scope prediction as an acceptance
criterion (`git diff --stat` limited to `awesome_tts/` + `requirements.txt`),
behavior matrix with worked examples, ordered red-green steps with verify
commands, and a DO-NOT list.
