# Audio-driven duration contract

The pinned MultiTalk and InfiniteTalk muxers use25fps and explicitly crop source audio to frame_count/25 before muxing. A successful video file alone is not proof that the full dialogue survived.

For dialogue use `forge.integrations.audio_timing.execute_audio_job_preserving_speech`. This probes every source with ffprobe and refuses a launch that would truncate audio. It does not speed speech. A1.2s input needs at least33frames(1.32s) under the4n+1frame rule. A17frame proof is0.68s.

The legacy execute_audio_job entry point remains intact for compatibility. It does not enforce source duration. Do not use it to accept dialogue completeness. The new wrapper must be selected for any episode dialogue route before production resumes.

Only isolated technical validation may opt into allow_test_truncation=True. Its result carries rejected_truncated_test_audio and is not dialogue acceptance.

InfiniteTalkV3 validation on2026-11-06: runtime passed1671.87s,0.680svideo/AACstreams,17frames448x832at25fps. Source1.200s WAV was prefix-cropped, discarding0.520s with nonzero audio energy. Decoded AAC has0.704s including codec padding. Outputprefix/sourceprefix correlation0.9984,zero lag: cropping, not retiming. Mouth changes and reference fidelity were visually plausible for this tiny proof, but full-speech/AV-sync/multi-speaker/episode acceptance were not established.

## Selectable plan route (additive)

The actual `forge.render_plan.execute_plan` entry point now accepts `local_backend='multitalk'` or `'infinitetalk'` with explicit `local_options`. Default arguments preserve the legacy generator path. Mixed paid/local routes or fresh regeneration flags are refused.

The selected local path calls `plan_execution.execute_local_plan`, then `prepare_local_plan` from actual build_render_jobs output, then `execute_audio_job_preserving_speech`. It rechecks repository and project generation holds, refuses disabled gates, enforces existing still/angle/proof gates and requires a backend-specific reviewed dialogue proof before episode mode. No code grants that review. Missing acceptance remains blocking.

Preparation can run under a hold: `python -m forge.integrations.plan_execution prepare --project-dir DIR --backend infinitetalk --options-json OPTIONS.json`. Execution uses the same command with `execute` and passes through actual execute_plan dispatch. The options include root, ckpt_dir, wav2vec_dir, audio_by_plan_n, and any explicitly reviewed runtime controls. Preparation does not generate media or authorize execution.

Each execution attempts one selected clip only, records pending_review or failure, and stops for inspection. It never treats a successful file as accepted, never silently retries a prior attempt, and never claims unselected/silent shots are complete. Continuation and reviewed-output assembly are still intentionally blocked, not implemented as automatic approval. Full episode orchestration/assembly has not been runtime validated and no episode generation is authorized.

## Review continuation and compositor handoff

`plan_review.require_local_clip_review` now permits skipping a prior successful attempt ONLY with an explicit reviewer/source record, exact prepared-job hash, unchanged output hash, actual mux-duration verification and identity/wardrobe/location/full-speech/text/AV-sync/speaker-mapping checks. A missing, changed, failed or unknown result still stops. It does not rerender earlier clips.

`plan_review.assemble_reviewed_local_plan` verifies complete original plan coverage, including separately hash-reviewed silent shots, then calls the existing MoviePy compose route without a new voice/music track, preserving each clip's muxed audio. It rechecks repository and project holds. It refuses overwrites and returns assembled_pending_final_review, never episode_accepted. These are callable code paths with synthetic contract/media tests, not a claim that E01 clips exist or are approved. No review approval files are created by these functions.

The duration-safe executor now checks actual output video frames/fps/duration and actual muxed audio duration after successful inference. Source capacity checks alone are not treated as output proof. Duration verification still does not establish transcript accuracy or lip synchronization.

Revision note: the earlier statement that continuation/assembly was unimplemented describes the initial wiring checkpoint only. The review-bound functions below are the subsequent code implementation. They remain unvalidated with actual E01 model outputs and cannot override holds. Local routing refuses legacy director/prompt/audio/resolution/credit options rather than silently ignoring them.

`python -m forge.integrations.plan_execution assemble --project-dir DIR --backend infinitetalk --options-json OPTIONS.json` selects the reviewed compositor handoff directly. Assembly options are `audio_jobs` (the exact prepared jobs including their runtime_contract), `out`, and optional `plan_path`. Changed sample steps, precision/runtime profile, checkpoint path or related runtime controls invalidate a prior clip review. No route auto-creates the review records or relaxes the user hold.

## Actual-audio-first frame sizing

The selectable route now calls the existing plan bridge with `preserve_full_speech=True` (legacy default remains unchanged). It probes every speaker source before choosing frames, uses the greater of planned duration and longest source duration, then rounds UP to4n+1 at25fps. A stale0.68s plan with1.2s audio therefore becomes33frames/1.32s capacity, not17frames/0.68s. The original plan and source audio remain unchanged, with both durations recorded. Audio requiring more than377frames is refused with an explicit reviewed-sentence-split requirement, never automatically cut or sped up. The guard rechecks duration immediately before inference and verifies actual output stream durations afterward. This corrected frame route has local tests, not a new GPU runtime proof.
