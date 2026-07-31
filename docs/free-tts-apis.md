# Free TTS options for Japanese + English flashcard audio

Research date: 2026-07-31. Question: what are the best **genuinely free** TTS
options that support **both Japanese and English** with modern **neural/AI**
voices, reliable and accurate enough for generating short flashcard audio from
the `awesome_tts/` Anki add-on (desktop Python; can shell out to local servers
or call HTTP APIs; heavyweight pip deps are possible but painful)?

All claims below are traced to primary sources (official pricing pages, repo
READMEs, license texts). License facts are reported as-is — this is not legal
advice.

## Recommendation summary (ranked for the Anki add-on use case)

1. **edge-tts** (unofficial Microsoft Edge API) — best quality-per-effort:
   excellent neural `ja-JP` + `en-*` voices, zero cost, no key, `pip install`.
   Risk: undocumented endpoint, could break or be shut off at any time.
2. **Kokoro-82M** (local) — best fully-offline, properly-licensed option:
   Apache-2.0 weights, ja + en, 82M params. Cost: torch + espeak-ng native dep.
3. **MeloTTS** (local) — MIT license, CPU real-time, ja + en (4 accents).
   Caveat: repo unmaintained since 2024-12.
4. **Google Cloud TTS free tier** — largest official free quota (1M Neural2 /
   4M WaveNet/Standard chars/month), but requires a billing account (card on
   file).
5. **Azure Speech F0** — 0.5M neural chars/month free, official API; account
   required; whether the F0 tier expires after 12 months is unverified.
6. **ElevenLabs free** — best-in-class quality incl. Japanese, but only
   10k credits/month and ToS limit free use to non-commercial purposes.
7. **gTTS** (unofficial Google Translate) — fine as a last-resort fallback;
   single voice per language, not neural-grade.
8. **Amazon Polly free tier** — neural quota (1M chars/month) is
   first-12-months-only, so it is a trial, not "genuinely free."
9. **OpenAI TTS** — no free quota; excluded.
10. **Japanese-only engines** (VOICEVOX, AivisSpeech, COEIROINK,
    Style-Bert-VITS2, Open JTalk, AquesTalk) — excellent or at least free for
    Japanese, but fail the "both ja AND en" requirement; useful only if paired
    with a separate English engine.

**Verdict for `awesome_tts/`:** ship **edge-tts** as the default free service
(it is already the de-facto free engine in community AwesomeTTS forks) with
**Kokoro** or **MeloTTS** as the offline option for users who accept the heavy
install, and keep Google/Azure free tiers for users willing to bring their own
cloud key.

## Per-option evidence

### edge-tts (unofficial Microsoft Edge read-aloud API)

- Python module wrapping "Microsoft Edge's online text-to-speech service";
  `pip install edge-tts`, CLI included
  ([README](https://github.com/rany2/edge-tts/blob/master/README.md)).
- Free, no API key. Full neural voice catalog including `ja-JP-*Neural` and
  `en-*-Neural` voices (`edge-tts --list-voices`, same README).
- Custom SSML is not supported — the service "only permits a single `<voice>`
  tag"; rate/volume/pitch flags exist
  ([README](https://github.com/rany2/edge-tts/blob/master/README.md)).
- License: LGPLv3 for all files except `srt_composer.py` (MIT) — stated at the
  top of the [LICENSE file](https://github.com/rany2/edge-tts/blob/master/LICENSE).
- Maintenance: last push 2026-03-22, not archived (GitHub API, retrieved
  2026-07-31). Actively maintained after a 2024 period of uncertainty.
- **ToS status:** unofficial and undocumented; no Microsoft sanction. Microsoft
  has broken compatibility before (SSML removal above). Treat as reliable
  today, unguaranteed tomorrow.

### Kokoro-82M (local)

- "An open-weight TTS model with 82 million parameters," Apache-licensed
  weights; `pip install kokoro`
  ([README](https://github.com/hexgrad/kokoro/blob/main/README.md)).
- Languages: American/British English, Japanese (`lang_code='j'`, requires
  `pip install misaki[ja]`), Mandarin, Spanish, French, Hindi, Italian,
  Brazilian Portuguese (same README).
- Requires **espeak-ng** as a native dependency (apt/installer) — this is the
  main packaging pain point for an Anki add-on, plus a torch install.
- License: Apache-2.0 (GitHub API). Last push 2025-08-06 — roughly a year
  stale at research time, but the model/weights are stable artifacts.

### MeloTTS (local)

- "High-quality multi-lingual text-to-speech library by MIT and MyShell.ai"
  with English (US/UK/Indian/Australian/Default), Spanish, French, Chinese,
  **Japanese**, Korean; "fast enough for CPU real-time inference"
  ([README](https://github.com/myshell-ai/MeloTTS/blob/main/README.md)).
- License: MIT, "free for both commercial and non-commercial use" (same
  README).
- Maintenance concern: last push 2024-12-24 (GitHub API, retrieved 2026-07-31).
  Works today; don't expect fixes.

### Piper (local)

- "A fast and local neural text-to-speech engine," `pip install piper-tts`,
  VITS voices on onnxruntime
  ([README](https://github.com/OHF-voice/piper1-gpl/blob/main/README.md)).
- **No Japanese voice** in the official catalog: the supported-language list
  in [docs/VOICES.md](https://github.com/OHF-voice/piper1-gpl/blob/main/docs/VOICES.md)
  has ~40 languages including en_GB/en_US but no `ja`. Fails the ja+en
  requirement out of the box.
- Repo license: GPL-3.0 (original rhasspy/piper was MIT, now archived). Voice
  models carry per-model licenses — the docs warn some "may have restrictive
  licenses."
- Upkeep: actively pushed (2026-07-30) but the README carries a "Looking for
  Maintainers" banner from the Open Home Foundation.

### Style-Bert-VITS2 (local, Japanese-focused)

- Repo license is **AGPL-3.0** (same as upstream Bert-VITS2), with an
  LGPL-3.0 `text/user_dict` module
  ([README](https://github.com/litagin02/Style-Bert-VITS2#license)).
- The recommended JP-Extra pretrained models are Japanese-specialized: the
  author's own English doc says JP-Extra "removes Chinese and English
  components to focus on Japanese performance"
  ([docs/Style-Bert-VITS2_en.md](https://github.com/litagin02/Style-Bert-VITS2/blob/master/docs/Style-Bert-VITS2_en.md)).
  English only via older base models — effectively ja-only in practice.
- Bundled default models carry their own terms (JVNV corpus CC BY-SA 4.0;
  小春音アミ/あみたろ require credit and have usage bans)
  ([docs/TERMS_OF_USE.md](https://github.com/litagin02/Style-Bert-VITS2/blob/master/docs/TERMS_OF_USE.md)).
- Last push 2025-12-07 (GitHub API).

### VOICEVOX (+ AivisSpeech fork) and COEIROINK (local, Japanese-only)

- VOICEVOX: free Japanese TTS/song software; local engine with an HTTP API
  (Windows/macOS/Linux binaries and Docker) — the official site describes the
  engine as usable "from other software or applications"
  ([voicevox.hiroshiba.jp](https://voicevox.hiroshiba.jp/)). Editor code is
  LGPL v3 / dual-licensed
  ([README](https://github.com/VOICEVOX/voicevox/blob/main/README.md)).
- Terms: "商用・非商用問わず利用することができます" (usable commercially or
  not), **credit notation required**, and generated audio must additionally
  follow each voice library's own terms
  ([term page](https://voicevox.hiroshiba.jp/term/)). Very actively maintained
  (editor pushed 2026-07-31).
- AivisSpeech: actively maintained VOICEVOX-UI fork (LGPL-3.0), explicitly
  "日本語音声合成ソフトウェア" — Japanese-only
  ([README](https://github.com/Aivis-Project/AivisSpeech)).
- COEIROINK: free for commercial and non-commercial software use, but
  generated audio requires credit (`COEIROINK:<voice name>`), audio copyright
  stays with the voice provider, and use as ML training data is banned
  ([terms](https://coeiroink.com/terms)). Japanese-only.
- All three fail the English requirement; listed because they dominate free
  Japanese TTS and pair well with a separate English engine.

### Coqui XTTS v2 (local)

- 17 languages including English and Japanese
  ([model card](https://huggingface.co/coqui/XTTS-v2)).
- License: Coqui Public Model License — "This license allows only
  non-commercial use of a machine learning model and its outputs"
  ([CPML text](https://coqui.ai/cpml.txt)). Personal/hobby use is fine;
  redistribution terms apply to outputs too.
- Coqui the company shut down; `coqui-ai/TTS` last push 2024-08-16 (GitHub
  API). Heavy (multi-GB model, GPU strongly preferred).

### Open JTalk and AquesTalk (Japanese-only, non-neural)

- Open JTalk: "a Japanese text-to-speech system," Modified BSD license, last
  release 1.11 dated 2018-12-25; HTS/HMM-based (formant-era sound), Japanese
  only ([project page](http://open-jtalk.sourceforge.net/)). Fails the
  neural-quality requirement.
- AquesTalk: proprietary embedded-oriented engines (AquesTalk1/2/10/pico),
  Japanese only, formant-style "yukkuri" voice
  ([product page](https://www.a-quest.com/products/aquestalk.html)). Fails
  neural + English requirements.

### Google Cloud TTS free tier

- Free monthly quotas per [pricing page](https://cloud.google.com/text-to-speech/pricing):
  Chirp 3 HD 1M chars; **WaveNet 4M chars**; **Standard 4M chars**;
  **Neural2 1M chars**; Studio 1M; Polyglot 1M. Gemini-TTS models: no free
  usage limit listed.
- "You must enable billing to use Text-to-Speech" (same page) — i.e. a Google
  Cloud billing account with a card on file, though staying under the quota
  costs nothing.
- Full ja-JP + en-US neural voice catalog. Official, stable API.

### Azure AI Speech free (F0)

- F0 tier: "0.5 million characters free per month" for neural TTS
  ([pricing page](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/)).
- Whether the F0 free tier is perpetual or only for the first 12 months could
  not be confirmed from the pricing page (see Open questions).
- Official API; ja-JP + en-US neural voices. Requires an Azure account and key.

### Amazon Polly free tier

- Per [pricing page](https://aws.amazon.com/polly/pricing/): Standard 5M
  chars/month free; Neural 1M chars/month, Long-Form 500k, Generative 100k —
  the "for the first 12 months" qualifier is attached to Neural, Long-Form,
  and Generative on the page. So the neural voices are a 12-month trial.
- AWS account (card) required.

### ElevenLabs free tier

- Free plan: 10k credits/month (~10k chars, ~10 minutes of audio)
  ([pricing page](https://elevenlabs.io/pricing)). Japanese is a first-class
  language in `eleven_multilingual_v2` and Eleven v3
  ([models doc](https://elevenlabs.io/docs/models)).
- ToS: a free user "may only use the Services for non-commercial purposes";
  the commercial license starts at the Starter plan
  ([Terms of Service](https://elevenlabs.io/terms), updated 2026-03-31; the
  pricing page likewise gates "Commercial License" to Starter+).
- API key required. Quality is top-tier but the monthly quota is tiny for
  bulk deck generation.

### gTTS (unofficial Google Translate)

- Interfaces with "the undocumented Google Translate speech functionality";
  "This project is _not_ affiliated with Google or Google Cloud. Breaking
  upstream changes _can_ occur without notice"
  ([README](https://github.com/pndurette/gTTS/blob/main/README.md)).
- MIT license; last push 2026-04-06 (actively maintained).
- One voice per language, no neural-voice selection, rate-limited. Acceptable
  fallback for single words; not for quality-sensitive decks.

### OpenAI TTS

- Paid-only: tts-1 is listed at $15 per 1M characters on the official
  [pricing docs](https://developers.openai.com/api/docs/pricing); no free
  monthly quota exists. The "Free" usage tier on the
  [rate limits page](https://developers.openai.com/api/docs/guides/rate-limits)
  is for accounts granted promotional credits; community reports say new
  accounts no longer receive credits (not a primary source — treat as
  anecdotal).

## Open questions / what I couldn't verify

- **Azure F0 expiry:** the pricing page shows the monthly F0 quota but does
  not state whether it ends after 12 months; the fetched Azure free-services
  page did not render the per-service 12-month vs always-free split. Assume
  unverified either way.
- **ElevenLabs attribution:** older ElevenLabs terms required attribution on
  the free plan; the current ToS text fetched (updated 2026-03-31) shows only
  the non-commercial restriction for free users — no attribution clause was
  confirmed in the fetched portion (the tail of the document was truncated).
- **Polly Standard free tier duration:** the pricing page attaches "for the
  first 12 months" to Neural/Long-Form/Generative but the Standard sentence
  lacks the qualifier; whether Standard's 5M chars/month is perpetual is
  ambiguous from the page alone.
- **Voice-quality judgments** (naturalness rankings between edge-tts, Kokoro,
  MeloTTS Japanese, etc.) are inherently subjective and were not benchmarked;
  quality statements above are limited to what the primary sources claim.
- **edge-tts longevity:** no primary source exists for whether Microsoft
  tolerates third-party use of the Edge read-aloud endpoint; the risk
  assessment above is inference from the README's SSML removal note, not from
  any Microsoft statement.
