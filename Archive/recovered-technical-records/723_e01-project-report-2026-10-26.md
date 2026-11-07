# E01 durable project report + authority locators (2026-10-26, ~09:29 IST)

## Spend ledger
- charged_total: 2,976 / 28,704 cap. Jobs: cmvon6a7x0lbfjx014iasjln8 (s03 v1, 768, gate_failed), cmvoo3i0801oxix01comk8lhv (s03 v2, 768, user-rejected voice), cmvoovag40qjahy010cvqf5io (s01, 480, user-rejected readability), cmvop50tz02dyix01ou8ouq3g (s02, 960, user-rejected). Receipts: DramaSaga-work/examples/r2v/production-2026-10-26/run-receipts.json. No spend since 08:57; all paid held.

## Authority locators (user's own WhatsApp channel, full message IDs)
- Cap approval (conditional 28,704): 2026-10-26 07:51:04 IST, [private-record-reference] - "First check and verify everything and all checks ... Then this is approved to be spent"
- 768 test approval: 2026-10-26 08:26:54 IST, [private-record-reference] - "Approved and share with me here too"
- E01 release (one episode): 2026-10-26 08:49:18 IST, [private-record-reference] - "Generate 1 episode atleast with this consistency"
- Wan 3.0 30fps direction: 2026-10-26 07:31:26 IST [private-record-reference] and 07:43:09 IST [private-record-reference]
- Still-first reference route: 2026-10-25 14:56:44 IST, [private-record-reference] - "I told you to generate 1000 still frames in images first so that you can then generate video with those references properly"
- Count delegated to us: 2026-10-25 14:59:33 IST, [private-record-reference] - "1000 is just a number. You decide that number how many are required for consistency. Do it properly."
- User rejections: s02 2026-10-26 09:12:15 IST [private-record-reference] ("This is fully wrong"), s01 09:12:52 IST [private-record-reference], reference-route question 09:22:08 IST [private-record-reference]
- project-contributor direction exists only as our own outbound paraphrase (agent msgs 2026-10-26 06:59:44, 2026-10-25 23:48:47); original not recovered; context, not authority.

## Verified API facts (docs.magichour.ai OpenAPI + models page, pulled 2026-10-26 ~09:21-09:28)
- t2v references: named refs (max 10); wan-3.0 supports images/videos/audio refs.
- i2v: NO references array; image_file_path + end_image_file_path only; wan-3.0 supports start+end frame 480p/720p/1080p; audio toggleable no extra credits; 96 cr/s at 720p.
- ai-image-editor: assets.image_file_paths max 10; aspect 9:16 supported; candidates: seedream-v4 from 40 cr (9 inputs, up to 4k), nano-banana-2.1 from 50 cr single 640px/1k or 150 cr grid of 4/9/16 (9 inputs, up to 4k), nano-banana-pro from 150 cr. "From" = lowest res; exact 1k/2k price per model not enumerated in docs.
- lip-sync: video file + audio file inputs; max_fps_limit is a CAP (output retains input fps below cap) so 30fps output possible; lite 1 cr/frame, pro 2x; 10s 30fps = 300 cr lite.
- Failed generations refunded; gate/user-rejected successful generations are NOT refunded.

## E01 combined cost scope (ESTIMATE with named uncertainty, not a quote)
- 23 composed frames (18 start + 5 causality end frames, 1k 9:16): 23 x 40-50 = 920-1,150 cr (seedream-v4 / nano-banana-2.1 single-image; grid batching 150/16 unverified for per-frame control).
- Video: 111s x 96 = 10,656 cr (wan-3.0 i2v 720p audio).
- Lip-sync on face-close dialogue shots (s02, s07, s13, s18, lite): ~870 cr.
- Total ~12,450-12,700 cr ~= 48% of remaining 25,728. Uncertainty: per-resolution image price, grid controllability, lip-sync shot count, redo risk (our history: 2 of 3 paid dialogue jobs rejected after successful generation - not refundable).
- Model justification: nano-banana-2.1 has prior use in this project's image runs (agent msg 2026-10-26 01:04:19) but is NOT proven as the canonical bank's source model (creation records unidentified); seedream-v4 is cheaper with same input capacity. No identity evidence for either on OUR characters yet - that is what the first composed frame would test.

## Route statement (descriptive, no silent switch)
Current: wan-3.0 t2v with named refs (produces video+voice in one pass; voice diverged from accepted takes on all 3 jobs, envelope 0.19-0.23). Proposed, not executed: composed start/end frames (ai-image-editor with ref bank as inputs) -> wan-3.0 i2v -> optional 30fps lip-sync with accepted ElevenLabs line on close dialogue shots. This changes reference conditioning from named-refs-in-prompt to frame-bound: a capability switch requiring explicit approval, not a silent retool. Voice guarantee even then is unproven until a paid probe passes the user's listen.
