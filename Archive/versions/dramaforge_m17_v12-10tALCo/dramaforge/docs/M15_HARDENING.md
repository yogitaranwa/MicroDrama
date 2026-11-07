# m15 hardening

Additive failure-handling and regression guards over m14. Both flows are
unchanged: without a route name the legacy flat estimate and manifest are
byte-identical in shape; route-aware execution still fails closed on any
quote/generator mismatch. No paid calls, renders or vendor code were added.
Each item names the failure it exists for.

## Money guards

- `forge/guard/ledger.py`: `reserve()` rejects non-positive, non-numeric and
  non-finite amounts (a negative amount previously *reduced* recorded spend,
  i.e. manufactured credits). The ledger file is validated on every read; a
  crash-truncated or tampered record fails closed with `SpendLocked` naming
  the file, instead of a raw parse error or a misread balance. Writes are
  atomic (temp + fsync + os.replace); a simulated crash mid-write leaves the
  prior counters intact. Concurrent spend is guarded per-thread and, on
  POSIX (Linux/macOS, so also Colab/Kaggle), across processes via an `fcntl`
  advisory lock - proven by a test racing 8 real OS processes that cannot
  overspend the cap. On Windows, where `fcntl` does not exist, protection
  degrades to the thread lock plus atomic writes: two processes racing on
  Windows could both read the same balance. Run paid renders from one
  process at a time on Windows.
- `forge/llm.py`: the Claude fallback cap is checked as
  `spent + reserve > cap`, so a run can never cross its approved USD budget
  (the old check could exceed it by one reserve). Clearly non-retryable
  NVIDIA failures (HTTP 400/401/403/404/422, extracted through the exception
  chain) raise immediately instead of silently spending the paid fallback on
  a request that can never succeed.

## Paid API failure handling

- `tools/video_generator_magichour_api.py`: the submit response must contain
  a job id and be JSON (clear error otherwise). The poll loop tolerates
  transient failures - network errors, 5xx, non-dict or non-string-status
  payloads - with a bounded consecutive-error budget (6), because one flaky
  GET must not kill a job whose credits are already reserved. Terminal
  statuses, missing downloads and the final timeout all name the job id for
  reconciliation with the provider.
- A failed render raises `RenderJobError` carrying the provider job id and
  an explicit do-not-resubmit warning. `recover_job(job_id)` polls an
  existing job without spending anything new. Under `resume=True`, a clip
  recorded as submitted is recovered through `generator.recover_job` instead
  of being resubmitted; a clip whose submit outcome is unknown (no job id)
  fails closed with reconcile instructions. Blind resubmission of a paid job
  is never automatic.

## Resumable episode renders

- `forge/render_plan.py`: `execute_plan(...)` records every clip in
  `.forge/render_execution.json` as it completes. If clip N of M fails, the
  exception propagates (unchanged) but the state survives. **As of m16,
  resume is the DEFAULT**: a normal re-run skips clips already paid for
  instead of charging them again. Deliberate regeneration is explicit:
  `fresh=True` archives the record to `render_execution.json.<timestamp>.bak`
  (recoverable, never overwritten) and re-renders and re-charges everything.
  `resume=False` alone is the untracked legacy mode and refuses to run when
  a record with paid clips exists, so re-charging cannot happen by accident.
  A plan/route/still change after a partial run fails closed with a message
  pointing to `fresh=True`. The resume
  record is bound by a fingerprint of the project, plan prompts and snapped
  durations, the reference-still labels AND their locked byte hashes, and
  the route model/resolution/audio; any change fails closed instead of
  returning stale clips. A recorded output is re-validated before reuse
  (local files must exist non-empty; remote URLs can only be shape-checked
  offline - liveness is owned by the human review gate).

## Audio and pacing

- `forge/audio/pace.py`: `phrase_wpm([])` returns 0.0 instead of
  `IndexError`; zero-duration phrases are skipped instead of dividing by
  zero; `join_lines` rejects an empty input and reports both sample rates on
  mismatch (was a bare `assert`, stripped under `python -O`);
  `stretch`/`trim_silence` fail with a clear message when ffmpeg is missing
  and verify the output file exists and is non-empty.
- `forge/audio/casting.py`: `settings()` on an unknown speaker raises a
  `ValueError` listing the cast and suggesting close matches, instead of a
  bare `KeyError` at generation time.
- `forge/audio/tts.py`: `ElevenLabsFinal.say` refuses empty text before
  spending characters, and validates the paid response (audio content-type
  or RIFF/ID3/fLaC/OggS/MP3 magic bytes) before writing it out - an error
  page or JSON body is never saved as a .wav after characters were charged.

## Plan integrity

- `forge/dialogue_shots.py`: new `verify_dialogue_preserved(script_shots,
  planned)` proves every scripted (speaker, text) line survives the
  shot/reverse-shot expansion exactly once, in order, with at most one line
  per clip. `plan_summary` now really detects multi-line clips (the old
  check compared a shot against itself and could never fire) and reports
  `total_seconds`. `write_plan_and_lint` attaches the check as
  `lint["dialogue_check"]` for human review.

## Assembly and review

- `forge/assemble/compose.py`: `burn_captions` escapes the ASS path for the
  ffmpeg filtergraph (quoted, quote/backslash escaped), so Colab-style paths
  with spaces no longer break caption burns, and a missing ASS file is a
  clear `FileNotFoundError`.
- `forge/gates/review.py`: `review_episode` flags negative, non-finite or
  non-numeric shot durations as issues instead of silently summing them.
- `forge/gates/common.py`: gate state writes are atomic; a corrupt state
  file raises `GateLocked` (fail closed) and `python -m forge.gates status`
  prints `CORRUPT` instead of crashing.

## Verification (this sandbox)

- 364 tests + 30 subtests pass (302 + 30 before m15, 62 hardening
  regressions). Old-flow smoke: legacy flat estimate, no route report.
  New-flow smoke: veo3.1-lite 720p+audio snaps 2.0/1.5/3.4s clips to 4s at
  72 credits/s. Caption burn and pace stretch/trim ran end-to-end against
  real ffmpeg (incl. a path containing spaces). Cross-process ledger safety
  is proven with 8 real OS processes; crash-mid-write tests prove atomic
  writes preserve prior state.
- Caveat: the project targets Python >=3.12; this sandbox ran Python 3.10
  with a tomli-backed tomllib shim. Re-run on 3.12 before production use.
  These tests do not prove generated acting, voice, lip-sync or final-watch
  quality - the human review gates still own those judgments.
The resume
  record is bound by a fingerprint of the project, plan prompts and snapped
  durations, the reference-still labels AND their locked byte hashes, and
  the route model/resolution/audio; any change fails closed instead of
  returning stale clips. A recorded output is re-validated before reuse
  (local files must exist non-empty; remote URLs can only be shape-checked
  offline - liveness is owned by the human review gate).

## Audio and pacing

- `forge/audio/pace.py`: `phrase_wpm([])` returns 0.0 instead of
  `IndexError`; zero-duration phrases are skipped instead of dividing by
  zero; `join_lines` rejects an empty input and reports both sample rates on
  mismatch (was a bare `assert`, stripped under `python -O`);
  `stretch`/`trim_silence` fail with a clear message when ffmpeg is missing
  and verify the output file exists and is non-empty.
- `forge/audio/casting.py`: `settings()` on an unknown speaker raises a
  `ValueError` listing the cast and suggesting close matches, instead of a
  bare `KeyError` at generation time.
- `forge/audio/tts.py`: `ElevenLabsFinal.say` refuses empty text before
  spending characters, and validates the paid response (audio content-type
  or RIFF/ID3/fLaC/OggS/MP3 magic bytes) before writing it out - an error
  page or JSON body is never saved as a .wav after characters were charged.

## Plan integrity

- `forge/dialogue_shots.py`: new `verify_dialogue_preserved(script_shots,
  planned)` proves every scripted (speaker, text) line survives the
  shot/reverse-shot expansion exactly once, in order, with at most one line
  per clip. `plan_summary` now really detects multi-line clips (the old
  check compared a shot against itself and could never fire) and reports
  `total_seconds`. `write_plan_and_lint` attaches the check as
  `lint["dialogue_check"]` for human review.

## Assembly and review

- `forge/assemble/compose.py`: `burn_captions` escapes the ASS path for the
  ffmpeg filtergraph (quoted, quote/backslash escaped), so Colab-style paths
  with spaces no longer break caption burns, and a missing ASS file is a
  clear `FileNotFoundError`.
- `forge/gates/review.py`: `review_episode` flags negative, non-finite or
  non-numeric shot durations as issues instead of silently summing them.
- `forge/gates/common.py`: gate state writes are atomic; a corrupt state
  file raises `GateLocked` (fail closed) and `python -m forge.gates status`
  prints `CORRUPT` instead of crashing.

## Verification (this sandbox)

- 364 tests + 30 subtests pass (302 + 30 before m15, 62 hardening
  regressions). Old-flow smoke: legacy flat estimate, no route report.
  New-flow smoke: veo3.1-lite 720p+audio snaps 2.0/1.5/3.4s clips to 4s at
  72 credits/s. Caption burn and pace stretch/trim ran end-to-end against
  real ffmpeg (incl. a path containing spaces). Cross-process ledger safety
  is proven with 8 real OS processes; crash-mid-write tests prove atomic
  writes preserve prior state.
- Caveat: the project targets Python >=3.12; this sandbox ran Python 3.10
  with a tomli-backed tomllib shim. Re-run on 3.12 before production use.
  These tests do not prove generated acting, voice, lip-sync or final-watch
  quality - the human review gates still own those judgments.
