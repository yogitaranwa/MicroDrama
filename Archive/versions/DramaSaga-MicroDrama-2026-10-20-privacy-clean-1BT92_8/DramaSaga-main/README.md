# MicroDrama

Clean source release, 20 October 2026. Preserves the supplied `DramaSaga-main/` ZIP layout and adds the day's audio-first implementation. This is a code release, not a claim that generated films have passed quality review.

## Start

Python 3.10+, ffmpeg/ffprobe and `requests` are needed. Node.js is needed only for the alternate H3 joiner. No GPU, model weights, paid service setup or media assets are bundled. Pillow is required for local image checks; install dependencies only from official PyPI. Use [portable/README.md](portable/README.md) for explicit official-source local model installation, laptop PowerShell, Linux, Kaggle/Colab and already-provisioned RunPod setup. Inference itself never downloads models.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python audiofirst.py --help
python -m magicdrama.audiofirst.form --out output/my-brief
python audiofirst.py run --brief output/my-brief/brief.json --story story.json --out output/new-plan
python audiofirst.py produce --package media-package.json --out output/season-preview --backend own
```

The form saves inputs on loopback only. `run` prepares a season from a supplied story, optional local/cloud writer or explicitly labeled template scaffold. `produce` actually assembles accepted local audio/images/videos with captions, speaker/introduction bars, optional licensed soundtrack and a season ZIP. Image-only shots are an animatic, not animated acting. See [AUDIO_FIRST.md](AUDIO_FIRST.md) for contracts and default-off provider adapters.

## Two paths, kept separate

- New: `audiofirst.py` and `magicdrama/audiofirst/`. Audio-first planning, exact-manifest execution locks, tagged dialogue, image-first dependencies, local assembly and continuation ZIPs.
- Legacy: `run.py` delegates to `magicdrama/production.py`, configurable native-audio v5 rendering. `python run.py` is a no-network plan using `examples/honesty.json`. Historical quotes are not current prices. Legacy `--live --accept-costs` can spend money and is NOT protected by the new audio-first approval token. Do not activate either path without fresh scoped approval.

Legacy rendering needs actual reference images, a current verified quote, key, ffmpeg and two independently configured transcription commands. The bundled `transcribe_whisper.py` is only one optional engine; its package/model are not installed by this release. Archive notebooks/scripts may install dependencies, download models, prompt for keys or call APIs. Do not run archives blindly.

## What is included

The original modular pipeline, QA, tests, v5 scripts, episode JSONs, notebooks and benchmark research are preserved. Today's code adds the form, writers, image/voice/video adapters, execution ledger, subtitles, assembly and ZIP continuation. This revision adds CPU/local word-alignment recovery, fail-closed semantic QA/automatic-acceptance orchestration, installed-local vision transport, free licensed Commons audio discovery/download, a gated local H3 graph/runtime adapter and a small procedural OBJ blockout. `SOURCE_MANIFEST.json` lists file hashes; `CHANGE_SUMMARY.json` compares this release with the immediately previous clean ZIP.

Six H3 reference components with sanitized nonfunctional comments are isolated under `vendor/h3-film-reference`, with their original manifest. Only `join.mjs` is used by our optional `--backend h3_join` local assembly wrapper; our Python assembly path is also available. This is not the entire H3 repository. See [EXPORT_NOTES.md](EXPORT_NOTES.md) and `NOTICE` for scope and rights restrictions.

## Verification and limits

227 tests passed during release preparation, using mocked provider HTTP and real local ffmpeg assembly fixtures. Real CPU faster-whisper, SmolVLM and MediaPipe smoke tests also ran; see `evidence/cpu_smoke.json`. No paid generation or GPU compute was used. Tests establish code behavior, not real semantic-model accuracy, creative quality, emotion, phoneme lip sync or perfect caption timing. ASR and small vision/face models were installed and exercised on this Linux CPU environment. Strict ASR timing and strict video tracking rejected the test inputs. H3 inference, full semantic acceptance, moving-mouth/phoneme lip sync, Windows and hosted notebook execution remain unverified and fail closed. See AUDIO_FIRST.md for the exact remaining limits. Actual audio/pixel checks, current account access, prices, licenses and full playback remain necessary.

Keep source private/restricted. No public redistribution or deployment license is asserted. Model weights, media caches, credentials, spend ledgers and generated outputs are excluded. No automatic top-up, key generation or secret collection is part of this source release.

## Portable runtime revision

See [portable/README.md](portable/README.md) for pinned publisher sources, license notes, CPU/GPU prerequisites, exact commands and measured limits. The source is ready to push; installing a runtime is not proof that all creative-quality features are complete. H3 code is unit-tested against the official template structure, not real GPU inference. Small vision descriptions and mouth geometry do not automatically approve drama output.
