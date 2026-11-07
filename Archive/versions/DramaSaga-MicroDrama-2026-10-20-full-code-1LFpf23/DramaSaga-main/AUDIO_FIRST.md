# Audio-first workflow

Current source contract, 20 October 2026. This document replaces historical appended status lists.

## Available commands

```sh
python -m magicdrama.audiofirst.form --out /tmp/my-brief
python audiofirst.py plan --brief brief.json --out writing-request.json
python audiofirst.py run --brief brief.json --story story.json --out /tmp/new-plan
python audiofirst.py run --brief brief.json --local-model INSTALLED_MODEL --out /tmp/local-plan
python audiofirst.py image-plan --brief brief.json --story story.json --image-cap 12 --exposure exposure.json --out images.json
python audiofirst.py produce --package media-package.json --out /tmp/season-preview --backend own
python audiofirst.py produce --package media-package.json --out /tmp/project-owner-preview --backend project-owner
python audiofirst.py inspect-season season1.zip
python audiofirst.py run --brief season2.json --previous-season season1.zip --story story2.json --out /tmp/next-plan
```

Other CLI commands cover story validation, reference planning, measured line timeline/master, subtitles/burn-in, dialogue timing checks, free-audio license checks, optional review chains and safe ZIP pack/extract. Run `--help` for argument names. Use fresh output directories; do not overwrite accepted media or reset ledgers.

## Input and story

The loopback-only form collects character count (1-50), episodes (10-50), genre multi-select, a single era/setting field up to 1,000 Unicode code points, English language, season target and episode maximum (<=180 seconds). Each character needs an ID, name, description and uploaded PNG/JPEG/WebP or Nano Banana generation prompt. Upload limits: 5 MiB/image, 30 MiB/request. Container screening is not image-quality validation.

Story schema: series ID and season matching the brief; each episode has unique ID, title, draft_seconds, setup, turn, cliffhanger, lines and shots. Lines have globally unique IDs, cast speaker or narrator, text and performance direction. Shots cover the ordered lines exactly once and specify location/description, visible characters, camera, action, wardrobe and props. Runtime is estimated until accepted audio is measured. See tests and `writer.py:season_schema()` for examples.

`run` writes the brief, continuation-aware writing request, supplied/generated story, image/voice/soundtrack plans and explicit blocked states. No story means a writing request, not an invented season. `--template-draft` is an opt-in repetitive software scaffold, not a quality creative writer. Automatic planning does not waive paid-use consent or actual quality checks.

## Writers

`writer.py` validates strict model-returned JSON. `local_writer.py` supports only an already-installed loopback Ollama model, with no key, auto-download or cloud fallback. No local Ollama runtime was available during the check; no model weights were downloaded.

`cloud_writer.py` supports NVIDIA `nvidia/nemotron-3-super-120b-a12b` first. A 60-second no-visible-output stall may close its stream and fall back to explicitly approved Claude Sonnet 5. HTTP errors, early empty/malformed/truncated responses and stalls after partial content do not silently trigger paid fallback. A read-only NVIDIA catalog check returned HTTP 200 with the writer listed; inference quota/latency was not tested.

Cloud CLI options: `--cloud-writer-config`, `--writer-approval`, `--writer-ledger`, `--enable-cloud-writing`. No enable flag means refusal. Keys are supplied privately as `SARALYA_NVIDIA_KEY` and `ANTHROPIC_API_KEY`, never inside files/ZIPs. Config pins NVIDIA/Claude model, maximum output tokens, Claude cap <=$2.30/run, current rate-check date, pricing URL and input/output rates. Sonnet 5 base rates checked 20 October: $2/M input, $10/M output; reverify before use. No cache/tools/batch premium options.

Writer approval binds run ID, exact `{body, config}` hash, source approval reference, expiry <=24h, whether fallback is allowed and key identities. Before Claude generation, token-count preflight bounds input plus maximum-output cost. Reserve worst-case spend in the persistent run ledger first. Unknown submissions keep their exposure; no auto-retry. An approval-reference string is an interlock, not authenticated consent. No live writing or Claude request was made in this release.

## Images before video

`images.py` plans shared character/location/prop references before every shot keyframe. Uploaded character images are not regenerated. Missing dependencies fail rather than dropping identity references. Fresh keyframes prevent accidental chaining across location changes. Hash-bound pixel evidence is required before video consumes the reference plan.

Pinned model/route: `nano-banana-2.1`, single image, explicit `1k`, portrait `9:16`; generator `/v1/ai-image-generator`, referenced editor `/v1/ai-image-editor`. Official docs checked 20 October quote 50 credits for one 640px/1k image. Grids of 4/9/16 have different 150-credit total pricing and are excluded; 2k/4k are not quoted here.

Default cap: 12 new images/episode, up to 600 image credits, within (not added to) 3,000 total Magic Hour credits/episode and 30,000/batch. Explicit image-cap changes remain within hard credit caps. Shared assets are charged once at first use. Exposure includes actual/reserved image/video/replacement/unknown jobs; missing exposure is not zero. Pixel receipts bind bytes but cannot prove the inspection occurred or guarantee acting/geometry. These are 2D references, not true reconstructed 3D.

## Tagged dialogue and captions

`voices.py` plans one continuous `eleven_v3` dialogue request per episode, with conservative performance tags and separate exact spoken/submitted character counts. The selected named Clara/Clara Bennett role defaults to Amelia; Oliver/Oliver Reed defaults to Peter Harwood. Other cast get trait profiles and unresolved catalog choices, not inferred genders. Override via `--voices` mapping. Tags do not certify emotion. Catalog access, license and surcharge/model compatibility require a fresh check.

`dialogue_timing.py` checks exact provider text/speaker segments, monotonic times and coverage of the actual PCM16 WAV. It rejects the earlier early-ending provider alignment. Waveform coverage is not word-level sync certification. Automatic local word-alignment recovery is not bundled in this runner; supply checked actual-audio cue timings, never a guessed global shift.

Subtitle text stays exact English, at most two lines, <=25 chars/second with safe margins. Speaker bars and first-appearance introduction bars are separate overlays. Existing line-timeline commands require hash-bound accepted audio evidence. Optional audit review chains are not spend permission.

## Live-capable execution, default off

`live.py` supports approved Magic Hour image/editor/video create, poll, upload and download plus ElevenLabs tagged dialogue. `production_run.py` can execute an exact approved job manifest and then assemble accepted media. No live provider generation was exercised. Supported video request builders do not establish perfect fixed-audio/multi-speaker sync or exact current video pricing.

A media package optionally has `manifest: {run_id, batch_id, jobs, uploads}`. Each job has ID, stable batch-scoped episode ID, provider, kind, exact request `{endpoint, body}` and current verified quote `{amount, unit, verified_on, source_url}`. Magic Hour uses integer credits; image requests are pinned at 50 credits. Video requires fresh exact cost plus `image_evidence: {plan, accepted}` that passes hash/pixel checks. Approved upload records bind input SHA-256 and media kind.

ElevenLabs quote amount is exact tagged characters. It also needs verified billing `{unit: credits|INR|USD, max_amount, rate_verified: true}`. Submitted characters are not a verified credit charge. Verify included allowance and overage controls before activation.

CLI live jobs require `--approval token.json --enable-live --ledger /private/shared-batch.sqlite`. The token binds run/batch IDs, exact manifest hash, approval source, expiry <=24h, exact job counts/totals, voice billing limits and designated key identities. Key values come only from `project-owner_MAGICHOUR_IMAGE_VIDEO_KEY` and `project-owner_ELEVENLABS_KEY` or private injection. The image/video key is never routed to voice/writing. Do not put secrets in manifests, tokens, notebooks or source.

Use one shared ledger for the entire batch across restarts/directories. Reservations are transactional; unknown/submitting/failed jobs never automatically resubmit. Pending jobs resume the provider project. Completed outputs are rehashed. Overcharges stop the batch after detection; local software cannot undo provider charges. No silent paid retries, fallback or top-up. Conservative provider-host checks refuse arbitrary downloads/redirects.

Future generated bytes, uploaded dependency paths, actual voice timings and precise video quotes are unknown initially. Generate/check/quote the next stage under scoped approval; do not fabricate acceptance or timing to force an uninterrupted first-time paid run.

## Actual local assembly and soundtrack

Package `season` needs series ID, season number, reviewed canon and episodes. An episode needs:
- `id`, `audio: {path, sha256}`, `audio_checked: true`, `cue_audio_sha256` matching that audio.
- `spoken_lines` containing exact dialogue; `names` mapping speaker IDs to display names.
- `cues: [{start, end, text, speaker, actual_audio_checked: true}]` in measured seconds.
- `shots: [{path, sha256, kind: image|video, frames, pixel_checked: true}]` covering `ceil(audio_seconds*24)` frames exactly.

Do not set evidence booleans true without inspecting/listening. Output: conformed shot MP4s, continuous master, clean MP4, ASS/SRT, captioned MP4 and season ZIP. Image-only input is explicitly a still animatic; short videos fail instead of silently freezing. Generated clip audio is discarded; accepted master plays once. Output is a preview pending full playback/continuity/mix review.

Optional soundtrack entries need local path/hash, approved license, creator/title, source/license HTTPS URLs, checked date, hashed terms file, commercial/sync verification and required attribution, plus start_seconds/gain. CC0/CC-BY/YouTube Audio Library evidence is checked; arbitrary uploads and paid libraries are not presumed free. Local mixing applies gain/delay/limiting; listening still checks speech clarity. Automatic track discovery/download is not implemented.

`--backend own` uses our ffmpeg implementation. `--backend project-owner` invokes unchanged hash-pinned `join.mjs` for local trim/concat/master audio, then our subtitle/name-bar pass. No vendor caption Python/font path is invoked. Both paths pass real synthetic-media integration tests. These fixtures are software tests, not dialogue/emotion samples.

## Continuation, exclusions and remaining checks

Season ZIPs enumerate every asset path/size/hash plus canon characters/facts/unresolved/ending. ZIP inspection rejects unsafe paths, symlinks, encryption, duplicates, hash mismatch, suspicious compression and size limits. Arbitrary old videos are not reliable canon. No file is executed on import.

Six H3 source modules remain unchanged in the vendor folder. Only local `join.mjs` executes. `render-all.mjs`, paid service orchestration, Modal/RunPod and MiniMax H3 weights are not activated. Model license/compute permission is separate and remains blocked. Full H3 source/deployment/media/weights, secrets, output caches and private ledgers are excluded.

Remaining: real inference quality/account/model access, current video and voice billing quotes, actual word alignment, emotional acting/lip sync, soundtrack licensing/listening, creative continuity and final full-playback review. No live film-quality guarantee, true 3D engine or hosted production deployment is claimed.

## Official references

- https://docs.magichour.ai/api-reference/models
- https://docs.magichour.ai/api-reference/image-projects/ai-image-generator
- https://docs.magichour.ai/api-reference/image-projects/ai-image-editor
- https://docs.magichour.ai/api-reference/files/generate-asset-upload-urls
- https://docs.magichour.ai/api-reference/image-projects/get-image-details
- https://docs.magichour.ai/api-reference/video-projects/get-video-details
- https://docs.magichour.ai/api-reference/video-projects/audio-to-video
- https://docs.magichour.ai/api-reference/video-projects/image-to-video
- https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert-with-timestamps
- https://docs.api.nvidia.com/nim/reference/llm-apis
- https://platform.claude.com/docs/en/models/sonnet-5/overview
- https://platform.claude.com/docs/en/about-claude/pricing
- https://docs.ollama.com/api/chat
- https://docs.ollama.com/api/tags
