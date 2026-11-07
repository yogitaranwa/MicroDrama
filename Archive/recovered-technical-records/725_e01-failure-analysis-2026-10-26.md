# E01 s01/s02 rejection - failure analysis and recommendation
2026-10-26 ~09:16 IST. Basis: delivered frames of e01-s01.mp4 (480 cr) and e01-s02.mp4 (960 cr), canonical script/prompts, accepted-audio set, receipts. User rejected s02 ("fully wrong") and s01 ("what is this / its on you to judge"). All paid generation held; no rerolls; charged_total 2,976/28,704 unchanged.

## 1. What is verifiable (evidence, not impression)
- Both shots pass technical gates: 30fps actual (ffprobe), audio tracks present, ASR word-diff exact vs canonical lines.
- Draconia identity matches canonical reference bank in s02 (braided crown, gown, shawl; hash-verified refs). Harry reads consistent; glasses not resolvable at his on-screen size.
- The black spark and the dropped programme in s02 are scripted beats, confirmed in the shot prompt.
- Wan3 resynthesizes audio by design: envelope correlation vs the approved reference lines measured 0.19-0.23 on all three dialogue jobs. The approved ElevenLabs performance is used as timbre reference only; delivered delivery is a new performance.
- Wan3 did not honor the explicit locked-camera instruction in either shot (both drift wide-to-close).

## 2. Story-readability judgment (the verdict dimension main owns)
- s01 (5s establishing): the reflection motif is not legible without the script in hand; the translucent figure reads as a glitch, not "she is already watching him". Harry himself goes translucent in the final beat, confusing who is real. Danger is not established. A fresh viewer learns only "ball, Harry".
- s02 (10s): the spark is present but small and dark (reads as artifact on phone). Her advance is toward the camera, not visibly toward Harry; the line "walk over here slowly" depends on a spatial relationship that never reads on screen. The closing close-up drops the scripted floor-grid/feet motif.
- As a sequence, the s01->s02 cut carries no causality: nothing connects reflection-woman to alarmed-woman or the spark to her line. Judgment: fails story readability as assembled. Main's verdict (not usable) is confirmed from frames.

## 3. Structural causes (why prompt iteration is not the fix)
1. Voice lottery: approved audio is a reference, not the soundtrack. Every paid dialogue shot produces a new, unverifiable-until-delivered performance. Both user rejections (08:43 "emotionless", 09:12 "fully wrong") are consistent with this.
2. No staging control: camera lock and blocking are not honored; shot designs must be robust to drift, and ours were not.
3. I cannot listen. Vocal emotion cannot be pre-verified by me; routing every shot through the user's ear outsources QA to the customer. Rejected as process.
4. Cost asymmetry: 480-960 cr per probe, quality knowable only after spend. 2,976 cr bought two rejected shots. Remaining cap 25,728 cr cannot cover 15 more E01 shots plus E02/E03 at this hit rate.

## 4. Recommendation (my own, as requested)
The Wan3-only text-to-video route has not met the requested bar, and I cannot honestly promise another prompt recipe will. Minimum defensible changes, in order:
1. FREE, immediate: audio-truth assembly. Episode soundtrack = the 46 pre-approved ElevenLabs lines + licensed score; video is cut to that audio. Voice quality becomes a constant (already user-approved), removing the per-shot voice lottery. Demonstrated in e01-s02-accepted-audio-mux.mp4 (s02 visuals + approved line; lip-sync approximate by construction).
2. FREE, immediate: story-first review form. e01-animatic-s01s02.mp4 renders the same beats as keyframes + approved audio + score + caption. Story readability can be judged without burning paid shots; weak beats get redesigned before generation, not after.
3. IF generated-video episodes remain the goal: change class, not recipe - image-to-video from locked storyboard frames (consistency by construction) or a route with native audio-input lipsync. Needs research and fresh approval. No spend queued; no quality guarantee implied.
4. Recommend against: further Wan3 text-to-video dialogue probes at 480-960 cr each under the current design. Two bought data points say the same thing.

## 5. State preserved
- Receipts/jobs/ledger intact: production-2026-10-26/run-receipts.json, charged_total 2,976, no spend since 08:57. Stage C held. No rerolls performed or queued.
- Synced to Drive folder 1CDuuvFlC0kuy2YBgIzY6HGVkJCWw_wcM: this analysis, receipts, runner, mux demo, animatic.
