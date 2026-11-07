# v10 REVIEW DRAFT - v9 plus prompt-contamination fix and offset hardening (2026-10-26)

Everything from REVIEW-NOTES-v9.md still applies: s16 9s timing and audio
offset are PROPOSED, wardrobe pin PROVISIONAL, no budget approval, v7 remains
the delivered artifact, no 100% claims.

New in v10 (code/test only, no paid generation, no visual proof claims):
1. Prompt contamination fix: video prompts previously pinned BOTH leads'
   front-close references on every beat, including inserts where no lead is in
   frame. 15 of 16 beat units' prompts changed; each beat's declared frame
   references now own its video-prompt reference set. Off-frame faces are no
   longer pinned, and the tie-inconsistent Harry front-close reference no
   longer reaches the 3 no-leads beats.
2. audio_offset_s validation hardened: offsets on undivided shots, offsets
   without audio, off-grid/negative offsets, and offsets that do not match the
   leading wordless beats are now hard errors instead of silent misalignment.
3. Stress proofs (real ffmpeg, local): over-long approved audio with an offset
   STOPS assembly instead of truncating; offset places the take at exactly
   2.00s with merged duration exactly 9.00s.

Suite: 55/55 local tests green.
