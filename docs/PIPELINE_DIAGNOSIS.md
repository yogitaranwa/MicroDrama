# Where the gap is: our film vs the reference (diagnosis, 2026-11-01)

The user's verdict on the Kling film: "better, but really bad; it doesn't look like animated videos/anime; it doesn't match the reference, which is
fast, clear and understandable; it doesn't feel right", and they could not tell whether the fault is in the pipeline, the story writing, the prompt, the
compilation, or the way scenes are handled. This page answers that with measurements, not impressions.

## 1. What the reference actually is

`She swore it was only training... then Potter walked by` (60 s, 1280x720, 24 fps, -14.1 LUFS). Speech recognition on its audio detects **Japanese at
96-99% confidence** ("君が娘の友達かね" = "Are you my daughter's friend?"), and the English you read is **burned-in subtitles**. So it is a
professionally voice-acted anime-style animation with music and sound design, not the output of an image-to-video model. No model on Magic Hour
produces that look or those voices from a still plus a prompt. That is a ceiling, not a bug. It is also why the user now asked to test on **human
references first**: live-action humans are where video models are strongest.

## 2. Same yardsticks on both (measured, `edit_profile.py`)

| Measure | Reference | Our Kling film v1 | v1 + free effects (v2) |
| --- | --- | --- | --- |
| Cuts | 16 found automatically (one per 3.75 s) | 10 found (one per 4.7 s; scene detection missed two near-identical cuts) | same |
| Movement between cuts, mean / 90th percentile | 2.44 / 6.91 | 1.91 / 4.79 | **3.56 / 6.46** |
| Sound-level jump at each cut | 8.3 dB mean, 17 max | 18.3 dB mean, 28 max | 19.0 |
| Loudness range | 10.8 LU | 5.2 LU | 5.2 |
Cut rhythm is **not** the problem. Movement was (about 22% less, big moves 31% smaller) and is now closed by free editor effects. **Sound is still the
problem**: our cuts lurch about twice as much as the reference, and our dynamics are about half as wide (no music bed, no swells, no stings).

## 3. Stage by stage: where each problem lives

| Stage | Verdict | Evidence |
| --- | --- | --- |
| Target / expectation | **Largest gap, cannot be closed by us** | The reference is Japanese voice acting plus drawn animation plus music. Our anime frames are pretty but animate stiffly. Switch the test to human, live-action references. |
| Story writing | Contributes | Structure copied the reference (12 lines) but `lint_story` finds 91% of the runtime is someone talking, one shot without dialogue, one camera setup three times in a row, no zoom or flash. The reference spends time on reaction art (lightning, giant eye, walking in). |
| Prompt | Contributes | The style line literally said "limited-animation look" and 8 of 13 shots said "locked" camera. Measured result: stiff, low-movement shots. Fixed: lint warns on both; `zoom`/`flash_frames` exist. |
| Model | Real but not the main cause | Voices are generated per shot and differ (pitch of one line varies about 3 semitones across models, up to 5-7 across a character's shots); Kling adds "Ugh"/stutter unless told not to; no model gave a visible leap in picture quality (veo3.1 full vs lite). Lip sync and voice quality can only be judged by the user. |
| Compilation / assembly | **Contributes most among fixable things** | No music bed, flat dynamics, sound jumps 18-19 dB at cuts, no sound stings. Free fix for movement done; the music bed needs credits (about 47 for a 47 s score). |
| Scene handling | **Not the problem** | The locked environment plate worked: the same street in all 13 shots. |
| Measurement | Fixed a blind spot | Words are now checked by speech recognition; the old mouth-sync proxy was invalid and retracted. |

## 4. What other people do (read 2026-11-01; mostly vendor and tutorial pages, so treat as practitioner advice)

* **Keyframe-first, then animate.** Creators build characters, locations and props, make a keyframe per important shot, then generate video; many chain each clip's last frame into the next clip's first frame and check each *cut*, not just the stills. ([Dreamina/CapCut guide](https://dreamina.capcut.com/ai-video/best-ai-animation-tools-for-creators), [invideo first/last-frame pipeline](https://invideo.io/faq/what-is-a-first-last-frame-frames-first-pipeline-in-ai/), [Artlist transitions](https://artlist.io/blog/?p=53880), [Nemo short, Kling + Nano Banana](https://aitoolsforkids.com/projects/nemo-ai-short-film-kling-nano-banana))
* **Music, sound effects and the edit are separate steps**, not whatever the video model emits: a 1:47 AI short used one tool for music, another for sound effects, and CapCut for the final edit. (the Contra "Last Delivery" case study)
* **Multi-shot agents** pick reference images from earlier frames and have a vision model judge candidates for character, space and prompt fidelity: [ViMax](https://github.com/HKUDS/ViMax), [MovieAgent](https://github.com/showlab/MovieAgent); pipeline skeletons: [AutoVideo-Agent](https://github.com/wangxin6x/AutoVideo-Agent), [anim-studio](https://github.com/DvaitAI-tech/anim-studio) (cloned-voice TTS).
* **Fixed voice + audio-driven mouth** is the open-source answer to voice drift and lip sync: [InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk) and [MultiTalk](https://github.com/MeiGen-AI/MultiTalk) generate talking video from an audio track. Nothing found fixes a character's voice across shots inside a text/image-to-video model. Magic Hour's equivalent is `/v1/audio-to-video` (audio file + reference image + prompt, 24/48/72 credits per second at 480/720/1080p) plus the voice cloner (0.1 credit per character).

## 5. What changed in the code

* `native_mix`: `zoom` and `flash_frames` per shot (free movement), 16:9, music/voice/audio-to-video price helpers, `plan_music` (1 credit per second, 15 s minimum).
* `edit_profile.py`: `detect_cuts`, `edit_profile`, `compare_profiles`: measures a video's edit feel and names the gaps against a reference.
* `native_plan.lint_story`: warns about stiff cameras, wall-to-wall talking, no reaction beats, repeated setups, no free effects. Printed in every plan.

## 6. Still open (needs credits and the user's judgement)

1. A **continuous music bed** (about 47 credits) and a **sound sting** on impacts: expected to fix the sound-jump and dynamics gaps. Not yet generated, so not yet proven.
2. **Fixed voice per character** via voice cloner + `audio-to-video`: untested here; proposed as a cheap A/B on one shot.
3. **Human references**: new live-action characters and a short scene to test whether the pipeline "feels right" where the models are strong.

## 7. Per-cut sound review (2026-11-03, local only)

Normal `assemble_native_episode` now writes `mechanical.cut_audio` into `assembly.json` and its returned result. Every planned boundary has a timestamp,
zero-based left/right shot index, overlap length, before/after RMS levels in dBFS, signed delta and absolute jump. `native_report(video, cut_times)` and
`edit_profile(video, cuts)` expose the same measurement under `cut_audio`; pass known timeline cuts to avoid missing visually similar shots.
For dissolves, the timestamp is the incoming shot's start, so its windows include the overlap; it is not a before/after comparison outside the whole dissolve.

The default review threshold is **12 dB**, an editorial triage setting, not a quality gate or a target derived from the reference. The measurement uses
adjacent 250 ms windows and stereo channel power (no phase-cancelling mono downmix). Incomplete edge windows are reported as skipped. Existing aggregate
`audio_jump_*` profile fields retain their historical mono calculation for comparability. The warnings do not change `mechanical_pass` or the audio.
Listen at flagged timestamps, check the adjacent clips' gain and ambience continuity, and keep deliberate impacts, speech onsets and quiet beats.
This does not identify speech, detect sample clicks, or prove a perceived loudness mismatch; very closely spaced cuts may share measurement windows.

The current mixer already has gain matching, linear edge fades, optional ambience/music and final loudness normalization. At hard cuts the edge fades do
not overlap. Short fades can suppress sample clicks but do not establish continuity between sustained levels. Audacity's
[Fade and Crossfade manual](https://manual.audacityteam.org/man/fade_and_crossfade.html) describes equal-power overlaps for uncorrelated sounds; applying
those automatically here would require separate review of overlap timing and dialogue. This change adds diagnostics without modifying fades, dialogue,
timeline or intentional dynamics. A continuous bed remains an unproven creative remedy, not an automatic fix.

Read-only checks of the existing `clean.mp4` renders reproduced **18.3 dB** mean / **8 of 10** cuts flagged for Kling v1, **19.0 dB** / **12 of 14** for v2,
and **8.3 dB** / **6 of 16** for `output/reference/ref.mp4`. V1's largest change is **+27.9 dB at 11.625 s** (-44.5 to -16.6 dBFS); another is **-24.1 dB
at 30.0 s** (-22.3 to -46.4 dBFS). These checks used visual scene detection to match the earlier diagnosis, not the assembly timeline. V2's added flashes
also affect visual cut detection. Input SHA-256 hashes were identical before and after; no episode renders were written. The local detailed report is
`output/verification/cut-audio-local-20261103.json` (ignored output, regenerate through `cut_audio_report` as needed).

Verification: all **32 tests** in `tests.test_edit_profile` and `tests.test_native_mix` passed, including a known 20 dB step, silence/edge skips,
opposite-phase stereo, a single-sample impulse, and final-assembly warning persistence without failing the mechanical gate. The overlap attribution
test was rerun successfully after adding its timestamp/shot assertions. Tests used the bundled Python 3.12 runtime and a workspace temporary directory
because the repository venv launcher points to an unavailable Windows Store Python. No paid calls or listening-quality claims were made.
