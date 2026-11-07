# MicroDrama

Clean source release, 20 October 2026. Preserves the supplied `DramaSaga-main/` ZIP layout and adds the day's audio-first implementation. This is a code release, not a claim that generated films have passed quality review.

## Start

Python 3.10+, ffmpeg/ffprobe and `requests` are needed. Node.js is needed only for the alternate project-owner joiner. No GPU, model weights, paid service setup or media assets are bundled.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python audiofirst.py --help
python -m magicdrama.audiofirst.form --out /tmp/my-brief
python audiofirst.py run --brief /tmp/my-brief/brief.json --story story.json --out /tmp/new-plan
python audiofirst.py produce --package media-package.json --out /tmp/season-preview --backend own
```

The form saves inputs on loopback only. `run` prepares a season from a supplied story, optional local/cloud writer or explicitly labeled template scaffold. `produce` actually assembles accepted local audio/images/videos with captions, speaker/introduction bars, optional licensed soundtrack and a season ZIP. Image-only shots are an animatic, not animated acting. See [AUDIO_FIRST.md](AUDIO_FIRST.md) for contracts and default-off provider adapters.

## Two paths, kept separate

- New: `audiofirst.py` and `magicdrama/audiofirst/`. Audio-first planning, exact-manifest execution locks, tagged dialogue, image-first dependencies, local assembly and continuation ZIPs.
- Legacy: `run.py` delegates to `magicdrama/production.py`, configurable native-audio v5 rendering. `python run.py` is a no-network plan using `examples/honesty.json`. Historical quotes are not current prices. Legacy `--live --accept-costs` can spend money and is NOT protected by the new audio-first approval token. Do not activate either path without fresh scoped approval.

Legacy rendering needs actual reference images, a current verified quote, key, ffmpeg and two independently configured transcription commands. The bundled `transcribe_whisper.py` is only one optional engine; its package/model are not installed by this release. Archive notebooks/scripts may install dependencies, download models, prompt for keys or call APIs. Do not run archives blindly.

## What is included

The original modular pipeline, QA, tests, v5 scripts, episode JSONs, notebooks and benchmark research are preserved. Today's code adds the form, story/writer interfaces, NVIDIA-first/Claude fallback, Nano Banana requests, tagged ElevenLabs dialogue, execution ledger, subtitles, local media assembly, soundtrack license checks and ZIP continuation. `SOURCE_MANIFEST.json` lists file hashes; `CHANGE_SUMMARY.json` compares this release with the supplied ZIP.

Six unchanged H3 components are isolated under `vendor/h3-film-reference`, with their original manifest. Only `join.mjs` is used by our optional `--backend project-owner` local assembly wrapper; our Python assembly path is also available. This is not the entire H3 repository. See [EXPORT_NOTES.md](EXPORT_NOTES.md) and `NOTICE` for scope and rights restrictions.

## Verification and limits

192 tests passed during release preparation, using mocked provider HTTP and real local ffmpeg assembly fixtures. No live text/image/voice/video generation or paid compute was used. Tests establish code behavior, not creative quality, emotion, lip sync or perfect caption timing. Actual audio/pixel checks, current account access, prices, licenses and full playback remain necessary.

Keep source private/restricted. No public redistribution or deployment license is asserted. Model weights, media caches, credentials, spend ledgers and generated outputs are excluded. No automatic top-up, key generation or secret collection is part of this source release.
