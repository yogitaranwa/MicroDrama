# Gate Report e01s03 - 2026-10-26

## Result: GATE FAILED (audio reference non-adherence). No reroll. 768 cr spent of 28,704.

## Job
- job id: cmvon6a7x0lbfjx014iasjln8 (Wan 3.0 via Magic Hour, 720p 9:16, 8s, 768 cr)
- First POST: definitive 422 (missing @-mentions) -> prompt fixed -> one resubmit. No other charges.

## Verify gates (ffprobe ground truth)
- fps 30/1 ACTUAL (MH metadata wrongly reports 24) PASS
- audio track present PASS; duration 8.03s; 0/239 near-static frames PASS
- envelope honor 0.23 FAIL (threshold 0.9)
- ASR: clip = ref minus first line "Dance with me right now." -> REVIEW/blocked

## Audio diagnosis (waveform forensics)
- ref e01-l02-draconia.mp3: 6.88s, speech onset 0.12s (fits 8s budget, no tail truncation possible)
- clip audio 8.03s, speech onset 0.00s
- full-waveform cross-correlation peak 0.78 @ 1.16s lag, but 2s-segment correlations 0.03-0.26
- Conclusion: clip speech is NOT the reference audio (not shifted, not truncated). Wan generated its own speech and dropped the first line. This is a Wan audio-ref adherence failure on this job, distinct from historical h3 stochastic ignores.

## Eye test (dense frames)
- PASS: identity stable both characters; no ghost-duplication; grid+feet visible in step beats
- REVIEW: unrequested glowing blue lightning-arrow effect in several frames; framing not locked (close-up -> wide -> tight two-shot) despite camera-lock prompt

## Code state (this upload)
- production_runner.py: reservation ledger, halt-on-unknown, 400/422-only release, resume polls known job (no re-POST), ref-mention preflight over full manifest
- test_production_runner.py: T1-T8 ALL PASS (one-job gate, pre-network release, unchanged-balance halt, reserved halt, 400 release, post-accept halt, resume-poll zero-POST, mention validator)
- Gates: BLOCKING = fps, audio track, envelope >= 0.9, mannequin risk (>40% sampled static and >30); REVIEW-stop = ASR text delta; warnings = small static counts
- shot-manifest-wan30.json: 50 shots / 299s / 28,704 cr; 0 audio-duration risks; 11 two-body shots; CURSE speaker shots are intentional disembodied voice (e02 s04, s16)
