# Flaw log - Wan 3.0 probe e01s13 (2026-10-26)

Clip: /tmp/probe-out/wan30-e01s13.mp4 | job cmvom7uua0ko5jx01dj3geifi | 4s 720p 9:16, 384 credits (approved single probe)
Review method (honest scope): still-frame inspection at 0.33s intervals (12-frame temporal grid), full-res face crops at 0.5s intervals, feet/floor and hand/background crops, ffprobe, ASR (whisper-base), audio envelope correlation, consecutive-frame motion profile. NOT real-time playback; viseme/phoneme correctness and final acting judgment remain for human viewing.

## Passes
- Actual fps: 30/1 (ffprobe on delivered file). MH API metadata said 24; metadata untrustworthy for fps.
- Audio ref honored: envelope correlation 0.993; ASR(probe) == ASR(submitted ref).
- No mannequin holds: 0/119 near-static consecutive frame pairs; motion arc 1.45 -> 9.38 (2.5-3.0s) -> 3.83.
- Identity/wardrobe: face, glasses, hair, black robe + red lining + bow tie consistent across all 12 sampled frames and full-res crops; no melting/warping observed.
- Hand at 3.33s: plausible fingers, no extra-digit artifact at inspected scale.
- Background dancers: no ghost-duplication observed at inspected scales; grid reflections on marble physically coherent.

## Flaws (observed, with timing)
1. CAMERA NOT LOCKED - framing holds medium close frames 0-7 (0-2.33s), widens to full-body wide by frame 8 (~2.7s) despite explicit "static locked camera, no movement, medium close" prompt. Consequence: face/performance shrinks in the final 1.3s; the decisive action beat lands exactly when framing changes.
2. WRONG-STEP BEAT NOT CLEARLY LEGIBLE - motion peak at 2.5-3.0s coincides with the framing change; feet only visible in the wide tail at small scale. Reads as a stride/cross-step (frame 100 crop), not unmistakably "wrong steps, on purpose."
3. GRID VISIBILITY LATE - glowing waltz grid out of frame during 0-2.3s medium close while Harry "looks down at" it; viewer cannot see what he sees until the wide tail (frames 8-11, frame 110 crop).
4. PARTNER ABSENT vs scene intent - shot 13 sits mid-dance with Draconia ("break the grid WITH ME"); clip shows Harry alone. Deliberate probe choice (avoid two-body ghost-duplication), but two-person dance shots remain UNPROVEN on Wan 3.0 and are load-bearing for production.
5. SUSPECTED LOOSE LIP-SYNC EARLY (unverified) - ref audio speech onset ~0.0s; sampled mouths at 0.5s and 1.0s closed, open from ~1.5s. Two closed samples could land on closures; stills cannot settle this. Needs human playback.

## Unverified (not claimed)
- Viseme/phoneme accuracy; emotional acting quality; real-time motion smoothness; audio sync under playback. All require human watch of the clip (delivered to main 07:42).

## Production implications
- Lock-camera prompt wording insufficient on Wan 3.0; production prompts need stronger framing constraints (e.g., "no zoom, no pull-back, fixed focal length, framing unchanged entire shot") and action beats timed away from any framing drift.
- Two-character dance shots: untested risk; first production run should probe one two-body shot before committing full episodes.
- Script fork resolved: accepted rev audio (qa.json, ASR-verified per line) matches /home/sandbox/work/scripts/ variants (E01 v3, E02 v2, E03 v2 human-dialogue), NOT docs/E01-script-v3-human-dialogue.md. Canonical = work/scripts set.
