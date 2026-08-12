# Missing Media Files

Why a card can show a `[sound:...]` reference but play nothing, how to confirm
it, and how to recover. Written after a 2026-08 incident where 24 referenced
audio files turned out to be absent from `collection.media` — initially feared
to be caused by a batch card edit, proven to predate it.

## Symptoms vs. causes

A silent play button means the **file** is gone; a missing play button means
the **reference** is gone. They have different causes, so check which one you
have first. References live in note fields; files live in
`~/Library/Application Support/Anki2/<profile>/collection.media/`.

To list every referenced-but-missing file (read-only, run from repo root):

```bash
python3 - <<'EOF'
import sqlite3, os, re
media = os.path.expanduser('~/Library/Application Support/Anki2/LZ/collection.media')
con = sqlite3.connect(os.path.expanduser('~/Library/Application Support/Anki2/LZ/collection.anki2'))
missing = set()
for (flds,) in con.execute('SELECT flds FROM notes'):
    for ref in re.findall(r'\[sound:([^\[\]]+)\]', flds):
        if not os.path.exists(os.path.join(media, ref)):
            missing.add(ref)
print('\n'.join(sorted(missing)))
EOF
```

To prove a batch edit didn't remove references, compare `[sound:` counts per
note against a backup (see "Backups exclude media" below for how to open one):

```python
old = {nid: flds.count('[sound:') for nid, flds in backup.execute('SELECT id, flds FROM notes')}
new = {nid: flds.count('[sound:') for nid, flds in live.execute('SELECT id, flds FROM notes')}
lost = [nid for nid in old if new.get(nid, 0) < old[nid]]  # [] means no refs lost
```

## Zero-byte files (poisoned TTS cache)

A different failure mode: the file **exists** but is 0 bytes, so the card
plays silence. Cause: a TTS download fails mid-stream and leaves an empty file
at AwesomeTTS's cache path; the next fetch treated it as a cache hit and copied
the empty file onto the card. Fixed at the source on 2026-08-12
(`awesome_tts/awesometts/router.py` — a cache hit now requires a non-empty
file), but files poisoned before the fix stay broken until repaired.

Sweep for them (both locations):

```bash
find ~/Library/Application\ Support/Anki2/addons21/awesome_tts/user_files/cache \
     ~/Library/Application\ Support/Anki2/LZ/collection.media -size 0 -name "*.mp3"
```

Repair one (Anki running, AnkiConnect up): delete the 0-byte file from both
the cache and `collection.media`, regenerate the clip with the same voice the
add-on uses, then store it and re-point the note's `[sound:]` tag:

```bash
# edge-tts is importable from the add-on's deps dir; afinfo confirms real audio
PYTHONPATH=~/Library/Application\ Support/Anki2/awesome_tts_deps python3 -c "
import asyncio, edge_tts
asyncio.run(edge_tts.Communicate('WORD', voice='en-US-AvaNeural').save('/tmp/word.mp3'))"
afinfo /tmp/word.mp3  # 'estimated duration' must be > 0
```

```python
rpc('storeMediaFile', filename='edgetts-WORD.mp3', data=<base64 of the mp3>)
rpc('updateNoteFields', note={'id': NOTE_ID, 'fields': {'Back': back.replace(dead_tag, f'[sound:{fname}]')}})
```

## What actually causes missing files

- **Illegal-in-filenames characters (`*`, `?`, `:`, `"`, `<`, `>`, `|`).**
  Illegal on Windows/Android, so such files can't survive a multi-platform
  sync fleet (cf. AnkiDroid issue #8148 — special characters in media
  filenames break sync). Tell-tale: EVERY referenced `*`-named file is missing
  while no `*`-named file exists on disk at all. Prevention: never put `*` in
  a media filename; rename existing ones (`dou3 dou3*2.mp3` →
  `dou3 dou3-2.mp3`) in both the field reference and the filename.
- **Incomplete media sync.** Notes sync as text immediately; media syncs
  separately and lags or silently fails on slow networks. The reference
  arrives; the file never does. If the origin device is then wiped or
  reinstalled, the file is gone for good.
- **Check Media → delete unused, at the wrong moment.** It deletes files not
  referenced by any note. If it runs on any device while a note is temporarily
  deleted/re-imported (or before the reference is added), the file is marked
  unused and deleted — and media sync propagates deletions to every device.
- **Restoring an automatic backup.** `.colpkg` backups exclude media (the
  embedded `media` index is empty). A restore resurrects the references but
  not the files.

## Backups exclude media

Automatic backups in `~/Library/Application Support/Anki2/<profile>/backups/`
contain only the collection, so they are useless for recovering media — but
useful for forensics. To read one: unzip the `.colpkg`, then
`zstd -d collection.anki21b -o col.db` (the real data is in the zstd-compressed
`.anki21b`; the plain `collection.anki2` beside it is a ~50 KB stub).

## Recovery

1. **Another device still plays the card?** Sync from it (one-way upload if
   needed: Anki → Preferences → Syncing → "On next sync, force changes in one
   direction"), then sync everywhere else.
2. **TTS-generated files** (`azure-*.mp3`, `googletts-*.mp3`): just regenerate
   them with the awesome_tts add-on.
3. **Manual recordings**: re-record. `Tools → Check Media` enumerates every
   referenced-but-missing file; it can also tag the affected notes.
