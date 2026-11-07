# Classroom reference - feasibility vs Magic Hour docs (read 2026-10-27 ~03:51 IST, no calls, no spend)
Sources: https://docs.magichour.ai/api-reference/models , .../video-projects/image-to-video , .../video-projects/audio-to-video , .../video-projects/lip-sync
Balance, plan state and per-job rounding NOT checked live (needs GET /v1/account / get-details; not done, no key use).

## What the docs say
- Image-to-video body: end_seconds, model, resolution, audio (bool), style.prompt, assets.image_file_path, optional assets.end_image_file_path. No audio INPUT field. audio=true means the model generates its own native audio (wan-3.0: no extra credits). So locked dialogue cannot be fed into wan-3.0 I2V.
- wan-3.0 durations: integers 2-10, then 15,20,25,30 (min 2s). 720p = 96 credits/s, 480p 48, 1080p 180. minimax-h3 720p 48/s, 480p 24. wan-2.2 no audio.
- Audio to Video endpoint: assets.audio_file_path + optional reference image, start/end seconds, resolution 480/720/1080, style prompt. 24/48/72 credits/s. No model field documented. Unverified whether it handles multi-person framing or how it follows a prompt.
- Lip Sync endpoint: audio + video in, 1 credit/frame (doubled on pro), max_fps_limit option. Existing project already used it in earlier failed runs (costume/camera drift came from the stills/I2V stage, not lip sync as far as memory shows).
- Images: nano-banana-2.1 50 credits for 1 image at 1k; batch rates differ. Editor mode takes up to 9 extra input images (useful for reference-guided stills with a character sheet).
- Voice: Magic Hour AI voice generator 0.1 credit/char exists; ElevenLabs plan capacity not verified.

## Billing implications for this reel
- 18 shots, durations 0.5-4.8s. Wan-3 minimum 2s and integer lengths: rounding each shot up gives about 55 billable s (3,5,4,2,2,3,4,3,2,3,3,2,4,3,3,2,3,4) vs 45 edited s. At 720p that is about 5,280 credits for one video pass, before stills, lip sync, retries. Alternative models rounding is different (minimax-h3 any integer from 1: ~46 s at 48/s ~2,200). Not verified that any of them follow the shot content.
- Lip sync only on speech shots (about 12 shots, ~30 s) at ~30 fps = about 900 credits (1800 if pro) per pass. Unverified fps.
- Stills: 18 shots + character sheets; at 50 each about 900 plus; unverified batch pricing.
So "one pass" realistic order of magnitude: roughly 7-8k credits for Wan route, not 4,320; this is arithmetic from docs, not a quote.

## What technically differs from the prior failed method
1. Prior failure: independent start-frame per beat (rooms, costume, tie drifted), I2V invented own dialogue. Changes available per docs: (a) stills made with the editor mode from a character sheet + master hall image (up to 9 refs, so one still can include face ref + room ref); (b) wan-3.0 end_image_file_path (end-frame control) to hold the pose; (c) lip-sync stage for the locked ElevenLabs audio; (d) dialogue and voice done first, cut to the reel's line windows (S1-S15 timing in shotlist).
2. Not changed by docs: no multi-character reference-to-video on wan-3.0 is documented in the I2V body (seedance-2.0 / minimax-h3 descriptions mention "reference-led"/"reference-driven", but the I2V body has only one start image and optional end image, so how references are passed is unconfirmed here).
3. So there is no documented route that guarantees the reel's consistency. Best honest candidate: master hall + character-sheet stills (editor mode), short 2-5s I2V clips with silent/native audio off, then lip-sync with ElevenLabs lines, assembled to the reel's cuts. Unproven; could still fail on faces/rooms.

## Open inputs
- Speaker per line (3, 11, 13 uncertain) and voices for 4 female + 2 male characters. Voice mapping needed from user or inferred from context; STT only.
- Number of character reference images needed: not established; frames suggest at least 6 named looks (blonde Draco, ginger lanyard girl, dark-haired girl, black-haired girl, Harry, Ron-like redhead).
- Current credits, plan, ElevenLabs remaining characters: unchecked.
- Approval scope: not asked, no number recommended here.

## UPDATE 03:55 IST - S14-S16 test quote (read-only account checks)
Live reads: Magic Hour account (project-contributor) tier creator, 113,463 credits balance. ElevenLabs Creator: 13,323 / 131,000 chars used, overage not allowed. No generation, no writes.
Test S14,S15,S16 (2.8, 2.6, 1.8 s) -> wan-3 integer rounding 3,3,2 = 8 s -> 768 credits at 720p (96/s), 384 at 480p.
Stills: master hall + 3 shot stills = 4 x 50 = 200 (nano-banana-2.1 1k single rate; batch/editor rate not verified).
Lip sync on S14,S15 (3 s each, 30fps assumed): 180 frames std, 360 if pro tier doubling. fps and tier not verified.
Voices: 2 lines, ~65 characters, inside Creator plan; no extra cost.
Total uncovered if lipsync pro: 768+200+360 = 1,328 credits upper estimate; 1,148 if standard.

## UPDATE 03:57 IST - sources archived (price/schema)
Lip sync tool page https://docs.magichour.ai/tools/video/lip-sync : generation_mode lite=1 credit/frame, standard=1, pro=2 (pro on Creator+ tiers); example max_fps_limit=30; credits only for rendered frames, completed job credits_charged = exact cost. standard and pro require visible mouth movement in the input clip's opening seconds; lite has no such statement on that page. Still portraits should use AI Talking Photo instead (not chosen).
Stills charge evidence: hybrid-four-frame-test-complete.zip receipts (4 x 50, nano-banana-2.1 image editor 1k 9:16) - same-config price evidence only.
Shot S14/S15/S16 durations 2.8/2.6/1.8 s. Speaker/line mapping inferred (STT + on-screen mouth), medium confidence.
