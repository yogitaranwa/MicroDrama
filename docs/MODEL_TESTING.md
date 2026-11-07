# Model testing log: what each video model gave us, what it cost, what to use

Written 2026-11-01 from real renders on Magic Hour (image-to-video with audio on). Every number below is either **billed**
(read from the account/ledger), **measured** (a script), or **judged by the user** (a person watching and listening). Where the
tooling cannot judge something (voice quality, lip sync, acting) it says so. Sample sizes are small, often one shot with one
line: treat rankings as leads, not proof.

## 1. Which model for what (short version)

| Need | Use | Why / caveat |
| --- | --- | --- |
| Dialogue shots, anime, best value so far | **kling-3.0** (72 cr/s with audio) | User preferred it in the 4-way test; cheapest of the preferred two; any whole second 3-15. Without speech rules it prepends "Ugh" / "A- A-" (seen in 3 of 4 tries); with the SPEECH RULES prompt the next 3 shots were clean. Can turn the speaker's back to the camera. |
| Same, if budget allows | **wan-3.0** (96 cr/s, audio included) | User preferred it too; natural staging (Lyra turns toward the listener); exact words in the one clip. Only tested on one 3 s shot, 33% dearer than Kling. |
| Words must be exact, fixed 4/6/8 s shots | veo3.1-lite (72 cr/s) | Words usually exact, but user judged the whole film "very bad"; one shot added mumbled words; cannot do 3 s; a multi-speaker take cut away mid-line. |
| Premium Veo | veo3.1 full (120 cr/s) | In the one same-shot comparison the frames showed no visible gain over lite for +67% cost. Not recommended without new evidence. |
| Cheapest experiments | ltx-2.5 (48 cr/s at 720p, 24 at 480p) | Worst result of anything tested: exaggerated mouths, burned-in subtitles, artificial acting. Fine only for throwaway tests. |
| Cheap native audio at low resolution | seedance-2.0-mini 480p (48 cr/s) | One 4 s test: wide exaggerated eyes, lowest resolution. Not retested. |
| Never again | dubbed route: silent video + preset voice + separate lip sync | Rejected by the user: wrong voices, flat acting, no sound effects, publish-blocking (see 3.1). |
| Not tested | minimax-h3, seedance-2.0, seedance-2.0-fast, seedance-2.5, gemini-omni-1.1 (no audio), kling-2.6 (no audio), wan-2.2 (no audio) | Prices in section 2. |

**Worst-to-best by what we saw (small samples):** old dubbed route < ltx-2.5 < seedance-2.0-mini (480p) < veo3.1-lite (accurate words,
user unhappy) <= veo3.1 full < kling-3.0 (with speech rules) ~ wan-3.0 (user's pick of the 4-way test).

## 2. Cost cheat sheet (credits)

Credits per second of output, from Magic Hour's published table (re-read 2026-11-01). Audio column = extra per second when audio is on.

| Model | 480p | 720p | 1080p | Audio | 720p with audio | Whole seconds allowed |
| --- | --- | --- | --- | --- | --- | --- |
| veo3.1-lite | - | 48 | 72 | +24 | **72** | 4, 6, 8, 16, 24 ... 56 |
| veo3.1 | - | 96 | 120 | +24 | **120** | 4, 6, 8, 16, 24 ... 56 |
| kling-3.0 | - | 48 | 72 | +24 (720p/1080p) | **72** | 3 to 15 |
| wan-3.0 | 48 | 96 | 180 | included | **96** | 2 to 10, 15, 20, 25, 30 |
| seedance-2.0 | 96 | 216 | 528 | included | 216 | 4 to 15 |
| seedance-2.0-fast | 84 | 180 | - | included | 180 | 4 to 15 |
| seedance-2.0-mini | 48 | 120 | - | included | 120 | 4 to 15 |
| seedance-2.5 | 168 | 336 | 840 | included | 336 | 4 to 30 |
| minimax-h3 | 24 | 48 | 72 | included | 48 | 1 to 30 |
| ltx-2.5 | 24 | 48 | 72 | included | 48 | 1 to 60 |

Other prices: image (nano-banana-2.1, 1k) **50** each, image editor with references also 50; voice generator or cloner **0.1 per character**;
instrumental music **1 per second** (56 s = 56); lip-sync pass about **90 per 3-5 s clip** (five passes cost 456 on the old route).
Failed generations are not charged. Video jobs return an estimate and the final charge is corrected after render; in practice every
job here billed exactly its quote.

Rules of thumb: one finished minute of dialogue video costs about 4,300 credits on veo-lite or kling at 72/s, about 5,800 on wan,
about 7,200 on veo3.1 full, about 13,000 on seedance-2.0 at 720p. Models that take any whole second (kling, wan) save about 17% by
fitting each shot to its line (47 s instead of 57 s for the anime film).

## 3. Every test, in order

### 3.1 Old route, before this work (historical, from the repo)
Silent Kling-3.0 video (no audio) + Magic Hour preset voices ("Harry Potter", "Ron Weasley" ...) + separate standard lip sync + synthesized foley.
Harry Potter "Uninvited Guest", 14 shots: **4,218 credits** (images 1,000, video 2,688, voices 18, music 56, five lip-sync passes 456). 
**User judged: rejected.** Ron sounds like Hermione, crashes do not read, delivery is bland. Root causes found: every clip's own audio was
discarded, voices were celebrity-impersonation presets (all 1,264 of Magic Hour's voices are impersonations, so nothing can be published),
the voice was generated separately from the mouth.
Also in the repo: ltx-2.5 480p with native audio, "Missing Minute", five shots, **360 credits**: native speech worked and was intelligible to a
recogniser, but mouth shapes were exaggerated, two raw clips burned in unwanted subtitles (the edit cropped them), and the performance stayed artificial.

### 3.2 First native-audio test, 4 s, one original character (2026-10-29), 818 credits
Same still, same line ("You told me the door was locked."). 1 image 50 + veo3.1-lite 288 + kling-3.0 288 + seedance-2.0-mini 480p 192.
| Model | Billed | Output | Loudness | What the frames showed |
| --- | --- | --- | --- | --- |
| veo3.1-lite | 288 | 720x1280 | -10.9 LUFS (loud) | speaks early, rounded slightly exaggerated mouth shapes |
| kling-3.0 | 288 | 716x1284 | -24.8 LUFS (quiet) | most restrained speaking, closest to the quiet brief |
| seedance-2.0-mini | 192 | 496x864 (480p) | -20.8 LUFS | wide eyes, exaggerated mouth, lowest resolution |
**User judged:** picked Veo. Note: the mouth-vs-audio offsets I reported then (40-170 ms) came from a motion/loudness proxy that later failed calibration (section 5); they are not valid.

### 3.3 Harry Potter benchmark, native route, 14 shots (2026-10-29), 4,608 credits
veo3.1-lite 720p portrait, reused reference frames, billed exactly as quoted. Words: not yet measured then (no recogniser installed). **User judged:** "better than before".
A bug here (fps-filter joins dropped frames and truncated the video) was found and fixed; the first version sent to the user was missing about 4.5 s of picture.

### 3.4 The Last Ferry, original story, 11 shots, 13 lines (2026-10-30), 4,388 credits (3,888 video + 10 images)
veo3.1-lite. Words (recogniser, later): 0.0-0.09 error on every speaking shot. Voice pitch drift between shots of the same character, measured: Mara about 5 semitones
(262-348 Hz); Jonas 7 or more (one shout over a storm read an octave high, probably a tracking error). **User judged:** background not constant, voice changes, continuation feels off, not publishable.

### 3.5 Anime story "Only Training": images (2026-10-31), 600 credits
Environment plate + 3 portraits + 7 frames from plate/portraits/previous frame. One portrait came back as a four-view turnaround sheet and was redone (+50). **Result: the locked-street background worked**: the same street (kettle sign, windows, archway, clock tower) in every frame and shot.

### 3.6 One 16 s multi-speaker take, veo3.1-lite (2026-10-31), 1,152 credits
Four beats, two speakers, one generation. Words: 0.0 error, all five lines once, in order. Background held about 12 s, then the last close-up went soft/bokeh with different lamps; Lyra's robe lost its green lining.
**Failure:** around 12.5 s the model cut from Lyra to Aldric while Lyra was still saying "Impossible", so Aldric's moving mouth carried Lyra's voice. **User judged:** lip sync bad, story bad, nothing understandable. Lesson: **one on-screen speaker per shot** (now enforced by the planner); a multi-speaker take lets the model choose cuts.

### 3.7 "Only Training" per shot on veo3.1-lite, 13 shots, 58 s (2026-10-31/11-01), 4,176 credits
Words: 12 of 13 shots 0.0-0.2 error (names and non-words aside); **shot 9 scored 0.67**: the model added mumbled extra words ("Moles the King Wham") inside the line. Same street in all 13. One dropped connection during polling was resumed from the ledger without a second charge.
**User judged:** "the generation is very bad", suspects the model.

### 3.8 Same shot on four models (2026-11-01), 1,056 credits
Lyra's line "Really, it's only training!", same start frame, same prompt, 720p, audio on.
| Model | Billed | Length | Words (error) | Pitch | Frames |
| --- | --- | --- | --- | --- | --- |
| veo3.1-lite (baseline from the film) | 288 | 4 s | 0.0 | 296 Hz | holds together |
| veo3.1 full | 480 | 4 s | 0.0 ("Really? ...") | 250 Hz | holds together, no visible gain over lite |
| kling-3.0 | 288 | 4 s | **0.25 ("Ugh, really? ...")** | 258 Hz | bigger gestures, Lyra moves more |
| wan-3.0 | 288 | 3 s | 0.0 | 271 Hz | Lyra turns toward Aldric, natural conversational staging |
**User judged: the 3rd and 4th (kling and wan) are better.** Pitch of the same line varied by about 2.9 semitones between models, so the voice is unstable even for identical text.

### 3.9 "Only Training" on kling-3.0, tightened cut (2026-11-01), staged, cap 3,800
Planned 47 s = 3,384 credits.
| Shots | Billed | Words (error) | Notes |
| --- | --- | --- | --- |
| 1-3 (old prompt) | 216+216+288 | 2.0 ("A- A- Father!"), 0.25 ("Ugh, really?"), 0.0 | Lyra turns her back to the camera mid-line in shot 1; steam cloud drawn oddly beside Aldric in shot 3 |
| 4-6 (prompt with SPEECH RULES) | 288+216+216 | 0.0, 0.0, 0.5 ("Hm" for "Hmph", a non-word) | expressive faces, mouth clearly open on words, same street |
| 7-12 and 13 (prompt with SPEECH RULES) | 216+216+288+360+216+360 (+288 silent shot 6) | 0.0, 0.0, 0.0, 0.29, 0.0, 0.0 | shot 9, which veo-lite garbled, is clean; shot 10's 0.29 is the invented name "Kai Orren" heard as "Hi, Oren"; Kai's bow and Aldric's grin read well |
| 1 regenerated (SPEECH RULES + "face the camera") | 216 | 0.0 ("Father!") | Lyra spins to face the camera, mouth visible; no stutter |

**Final film:** 13 shots, 47.0 s, 1,128 frames exactly as planned, -16.2 LUFS, no dead air or silent seams, captions timed from per-shot words and an adaptive onset detector, hook title and end card. Total **3,600 credits** (3,384 plan + 216 regeneration) against a 3,800 cap, billed exactly as quoted. That is 576 credits (14%) less than the veo3.1-lite film of the same story (4,176, 58 s), 11 s shorter, and measurably cleaner on words (one non-word and one invented-name miss, no garbled shot, versus one garbled shot). `shot 2a` ("Ugh, really?") was left as is: regenerating it (216) would have exceeded the cap by 16 credits, and the extra word reads as a panicked disfluency with the script shown in the caption.
**User verdict on this film: pending.**

## 4. Failure catalogue (what goes wrong, by model)

| Failure | Seen on | Fix that worked or is planned |
| --- | --- | --- |
| Extra sounds before a line ("Ugh", "A- A-") | kling-3.0 (3 of 4 tries without rules) | SPEECH RULES clause in every dialogue prompt (clean in the next 3 shots) |
| Speaker turns back to camera mid-line | kling-3.0 shot 1 | same clause: "face toward the camera, mouth visible" |
| Mumbled extra words inside a line | veo3.1-lite shot 9 | regenerate that shot (432 credits), or edit the prompt |
| Cuts away mid-line, voice stays on the wrong face | veo3.1-lite 16 s take | one on-screen speaker per shot (planner rule) |
| Background changes between shots | every route before plate-lock | one environment plate per scene, every frame built from plate + portraits + previous frame |
| Clothing drift (robe loses green lining) | veo3.1-lite long take | stronger clothing line; only partly solved |
| Voice differs between shots | every model | not solved: pitch-match within 3 semitones, regenerate outliers, or fixed-voice route (untested) |
| Burned-in subtitles | ltx-2.5 | crop (loses resolution); avoid ltx for finals |
| Reference sheet used as portrait gives a multi-view sheet | nano-banana-2.1 | ask for a single-figure head-and-shoulders portrait |

## 5. What the tools can and cannot tell us

* **Reliable:** word accuracy (local speech recognition, `intelligibility.py`); frame counts; loudness; dead air and silent seams; cost (ledger vs account balance matched every time).
* **Noisy, use as a flag only:** pitch per shot (`voice_check.py`); it misreads shouts, gasps and noisy shots.
* **Invalid:** the mouth-motion vs audio-loudness "sync" proxy. On a clean professional reference clip it returned -333, +333 and -333 ms with weak or negative correlation, so no sync number from it counts.
* **Only a person can judge:** voice quality, lip sync, acting, whether the story lands. The user is the judge for those; the notes above record their verdicts.

## 6. Process lessons that saved money

Stage big renders (first 3 shots, check, then the rest); keep a hard cap per batch in the ledger; re-verify prices on the current day (the guard refuses stale quotes); never resubmit a job whose state is "submitted" or "unknown"; plan one speaker per shot; build an environment plate first; check every start frame by eye before paying for video.

## 7. Credits spent on this testing (billed)

| Item | Credits |
| --- | --- |
| 4 s native test, 3 models + image (3.2) | 818 |
| Harry Potter benchmark film (3.3) | 4,608 |
| The Last Ferry (3.4) | 4,388 |
| Only Training images (3.5) | 600 |
| 16 s take (3.6) | 1,152 |
| Only Training on veo3.1-lite (3.7) | 4,176 |
| Four-model same-shot test (3.8) | 1,056 |
| Only Training on kling-3.0, 13 shots + one regeneration (3.9) | 3,600 |
| **Total on this testing** | **20,398** |

Reconciliation: the account balance read 113,463 before the first test and 93,065 now, a drop of exactly 20,398, equal to the sum above. The account is shared, so in general a balance change can include other people's use; the per-job ledgers are the budget record.

## 8. Human-reference test and the fixed-voice route (2026-11-01), 1,417 credits of an 1,800 cap

Original live-action scene "Working Late" (`examples/late-night`): two realistic people, one kitchen, 4 shots, 13 s. Billed: 7 images 350 (plate + 2 portraits + 4 frames built from them),
four kling-3.0 shots 936 (216+216+216+288), voice clone 4, audio-to-video 112, music 15 = **1,417**.
* **Looks:** the same kitchen in every frame, both people consistent, strong readable acting (Mia's wide-eyed shock turning into a strained grin; Tomas still for 1.2 s before speaking). Words: 0.0 error on Tomas's lines; Mia's 0.67 is only the recogniser tripping on the accent in "Tomás".
* **Fixed-voice route works.** Voice cloned from Tomas's own generated line (1.65 s sample, MP3), then `/v1/audio-to-video` driven by that audio. The video's audio is the cloned audio exactly (same pitch, 124.0 Hz); the mouth follows it; words 0.17 (the recogniser wrote "6" for "six"). The cloned pitch sits 2.6 semitones below his native first line (144 Hz); his own two native lines differ by 1.35, so close but not identical (timbre unjudged; listen).
* **Cost:** about 116 credits for a 2.3 s line (cloner 4 + 112), against 72 credits per second native (about 165 for the same length). The route returns only the voice: no room tone, no effects, little body motion; ambience and music must come from the edit.
* **Gotchas found (all free to hit, all fixed):** (1) the cloner returns WAV bytes even when saved as .mp3; send a real MP3 (`ensure_mp3`). (2) the audio window must not run past the end of the audio ("couldn't read your audio file" was this, twice: a 3 s window on 2.38 s of audio). (3) audio-to-video is billed per whole frame at 24 fps: 2.3 s = 56 frames = 112 credits at 720p, one above a naive 111; the quote helper now rounds frames up. (4) The overcharge guard halted the batch on that 1-credit difference before downloading a finished, paid video; it was reconciled by downloading from the ledger's stored result, and the rest ran in a fresh capped batch.
* **Safety:** voice cloning is allowed by the guard only from project-generated audio (never a real person's recording), only with explicit voice approval, and only with an exact per-character quote.
* **Music bed (15 credits for the minimum 15 s) fixed the sound-continuity gap in the measurement:** level jump at cuts fell from 18-19 dB to about 3 dB (reference 8.3). Loudness range stays low (2-3 LU on a 13 s clip, reference 10.8 over 60 s), so dynamics are not yet like the reference.
* Free effects: push-ins keep average movement at the reference level (cut A 2.96 vs 2.44), though big moves remain smaller (p90 4.8 vs 6.9).

## 9. Directed retry of the human scene (2026-11-02), 1,683 credits (cap 1,700)

User diagnosis after watching the earlier cuts: the light turned on by itself, the cut from her to him looked like a different film, there was no camera movement, acting was exaggerated, the story did not make sense; the cause is thin prompts. Fix: a director's script (`examples/late-night/directed-story.json`, readable form `DIRECTORS_SCRIPT.md`; `directed.py` validates and builds the prompts) and **sequential chaining**: every shot starts from the real last frame of the previous one, or from a keyframe built from the room plate, the people and that last frame, and every prompt states how the previous shot ended.
Billed (kling-3.0, 720p): first frame 50, shot 1 (5 s) 360, shot 2 (3 s) 216, shot 3 (5 s) 360, shot 4 frame 50 + shot 4 (4 s) 288, shot 5 frame 50 + shot 5 (4 s) 288, music 21 = **1,683**. Running total on all testing: 23,498 credits (balance 113,463 to 89,965).
What looking at the footage caught (each was fixed, none by luck):
* The lit kitchen at the end of shot 2 showed an **empty table**, while the script had Tomas sitting at it. Rewrote the geography: he sits in a chair against the left wall a few steps inside the door, hidden from the hallway by the doorframe; shot 3 now continues from shot 2's last frame and pans left to reveal him.
* The reveal shot had no reference for his face, so the model invented a clean-shaven man in a dark sweater, unlike his bearded portrait. The on-screen man became canonical: later keyframes use that frame as his identity (`keyframe_refs`, `last:<shot id>`), and the wardrobe notes were updated to match.
* Freshly generated first frames were much warmer and brighter than the chained frames: at the cut into shot 4 brightness jumped 31% and red/blue went from 0.58 to 1.52. A per-shot `grade` (about 60% of the way back to the previous look) cut that to 39 to 43 luma and 0.57 to 0.85.
* Shots 4 and 5 opened with about 2 s of near-silence before the line. Trimming the lead-in (`source_start_frame`) and a steadier music bed (`steady`) brought the mean level jump at cuts from 16.6 dB to **7.8 dB** (reference 8.3). The final film is 18.7 s; movement 2.67 mean / 5.16 p90 (reference 2.44 / 6.91); cut rhythm is slower than the reference because chained shots do not cut.
* Prompts: Kling accepts 2,500 characters; the first drafts were 2,700 to 3,000. The builder now keeps motion, camera, action, performance, sound and continuity and drops wardrobe/format/set reminders only as needed, because the start image already carries the look.
* Words: shot 3 "Working late?" (reveal), shot 4 "Tomas... you're still up." (recogniser spelled the name differently, 0.25), shot 5 exact (0.0). Voices, lip sync and acting remain unjudged.
Remaining issues: Mia is seen only from behind through shots 1 to 3 (the planned tilt up to her face did not happen), loudness range is flat (1.0 LU), and a 5-shot scene is too small to judge a whole story.

## 10. Spatial continuity: the model does not know the room (2026-11-02)

User finding after the directed cut: at a cut the woman's position changed. She came in from outside, but the next shot showed her inside the room, with the background looking "kinda same": the model keeps the set looking similar and moves the people. Cause, confirmed in the footage: shot 3 ends with Mia in the doorway; the shot 4 keyframe put her several steps inside with the table and window BEHIND her, which a camera behind Tomas looking at the doorway cannot see (those are behind the camera; the doorway and dark hallway should be behind her). Shot 5 likewise showed the window and fridge behind Tomas and Mia in the doorway behind him, which that camera cannot see. Every frame was a fresh generation from "the plate + portraits + the previous frame", with no floor plan.
Fix (`blocking.py`, `directed.py`, `examples/late-night/directed-story.json` `plan`): a floor plan in metres, a camera position/target and each person's position/facing at the start and end of every shot, and from that:
* a continuity checker that fails the script when a person moves more than 0.4 m between consecutive shots, when a shot's `must_show` is not in frame, when its `must_not_show` would be (what is behind the camera), when a speaker is out of frame or has their back to the camera, or when a shot has no blocking;
* an exact `FRAMING` paragraph in every prompt (camera direction, who is where and how far, what is behind them, `NOT in frame (do not draw)`);
* a layout guide image (flat blocks: red = Mia, blue = Tomas) rendered from the same numbers and passed as the last reference of every keyframe, plus the framing text;
* floor-plan and layout drawings for human review (`render_floor_plan`, `render_layout`).
Building it also caught the plan's own errors: cameras 0.6 m behind a person (her back filled the whole frame), a camera that cannot see Tomas because the doorway wall hides him, and a layout renderer that drew furniture through a wall. Footage generated before this (shots 1 to 3) agrees with the plan; shots 4 and 5 do not and need regenerating. Untested: how closely the image model follows the layout guide (to be checked on the first new keyframe before any video is paid for).

## 11. Re-rendering shots 4 and 5: Kling provider failures and the Veo fallback (2026-11-02), 726 credits of a 750 cap

Goal: regenerate the two shots whose room position was wrong (see section 10) using the floor-plan layout guides.

* Kling 3.0 (`/v1/image-to-video`, 720p, audio on) returned Magic Hour `unknown_error` on five attempts at shot 4: two different first frames and three prompt variants, including one without the FRAMING paragraph. All five were uncharged (actual cost 0), so the fault looks like the provider's Kling service, not the prompt or frame. The guard counted each failed job's 288-credit quote against its batch cap, so every retry needed a fresh reconciled batch with the remaining cap.
* Fallback: veo3.1-lite, same 72 credits/s, 288 per 4 s shot. Shot 4 rendered first time. Room position is right (Mia inside the kitchen, dark doorway behind her, Tomas over the shoulder, no table or window), constant across the shot. Words heard: "Thomas. I'm dumbing. You're still up." against the script "Tomas... you're still up." Veo inserted an extra phrase, the same class of stray speech seen on Kling, so the fix is the speech-check gate, not the model.
* Shot 5: first frame with layout guide (50 credits) matched shot 3's background (wall and door behind Tomas); video 288 credits; words exact ("Your office closed at six.").
* Colour: new frames were warmer than shot 3. Per-shot `grade` set from measured mean colour, 60% of the way to shot 3's last frame (shot 4 r/g/b 0.66/0.90/1.17, shot 5 0.62/0.75/0.85). Final cut 21 s, 504 frames, no mechanical defects.

Spend: two earlier first frames 100, shot 4 video 288, shot 5 first frame 50, shot 5 video 288 = 726 of the 750 approved (24 left). Balance after: 89,239.

What this does and does not show: one shot per model is not a comparison. The position fix came from the layout guide and corrected first frame, not from Veo. Veo gave one clean and one flawed dialogue shot; Kling was not able to run. Quotes are the same for both models at this length. Treat Veo as a working fallback when Kling is failing, run the word-check gate on every shot before assembly, and do not claim either model is better until the same shots are rendered on both. Voices, lip sync and acting are still unjudged by tooling.

## 12. Cold Cycle: a 60 s, 15-shot film on Kling 3.0 from fixed master frames (2026-11-02), 5,280 credits

Goal: make a new original story (a laundromat, two characters, 8 spoken lines) and keep the room, objects and positions constant across all cuts, the failure found in the Working Late films.

Method (examples/cold-cycle/, `build_story.py` generates `directed-story.json`): a floor plan in metres for a single closed room, fixed camera and person marks per shot, `check_blocking` run before any spend (0 problems), then ONE master first frame per side of the room reused by every shot on that side. The checker caught two mistakes in the script itself (it claimed machines 6 and 7 were visible behind Dev from the Dev-side camera, and Dev stood in line behind Nora's camera so his body hid her).

Results (Kling 3.0, 720p, audio, 15 x 4 s at 288 = 4,320):
* Provider: Kling rendered all 15 shots (the earlier `unknown_error` did not recur). One network drop (DNS) cut the download of shot 7 after Kling had finished and charged it; the paid clip was fetched with a read-only status call, no new charge.
* Words: all 8 dialogue shots passed the speech check (WER 0.0, no extra words). Silent shots are less safe: shots 1, 7 and 13 got invented speech ("Thanks Cory!", "Alright.", "I'm on my phone."), so their audio was replaced by the room's own ambience in assembly.
* Continuity from frames of all 15 shots: sign, orange chairs, window and neon behind Nora in every Nora-side shot; vending machine, clock, washers behind Dev in every Dev-side shot; marks held. Not fixed: Nora and Dev smile more than the script asks (restraint is not controllable), Dev's face may differ between close and wide shots, and Dev's hood looks up in the Nora-side foreground shape.
* Image models: the first attempt at several masters ignored the layout guide (a hands insert came out as two faces; the drum insert as a face; the final wide with both people standing). Re-prompting with an explicit "extreme close-up, hands only" style instruction and a stated seated pose fixed them, at 50 credits each. A failed image job (connection error) was still charged.

Spend: plate and two portraits 150, 15 master frames and retries 1,000, 15 videos 4,320, score 60; total 5,280 of an approved ~5,350. No credit left for re-renders, which is the main risk of a plan that quotes its reserve and then spends it on frame retries.

Code changes in this PR: `blocking.py` now supports a single closed room (no hallway/doorway; `_render_open_room`), `directed.py` names the people in the layout-guide text from the plan, `tests/test_directed.py` updated for the longer Working Late cut (37 s, 9 shots).
