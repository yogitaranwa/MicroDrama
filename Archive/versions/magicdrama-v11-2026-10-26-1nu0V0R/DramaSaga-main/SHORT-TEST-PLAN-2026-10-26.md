# Bounded R2V test plan v2 + 3-episode arc review (2026-10-26, supersedes v1)

v1 proposed three non-adjacent non-speaking shots as a "continuity" test. That was wrong: e01s01, e01s08, e01s09 are not contiguous, so cut continuity could not be tested, and picking only non-speaking shots cherry-picked around the user's actual goal. v2 fixes this: one truly contiguous connected sequence, declared end/start states at every cut, visible speech included, exact quotes, and honest review requirements.

No spend is authorized by this document. Every number is an exact quote from the verified 2026-10-26 catalog; live submission still needs manifest approval and the user's budget/payment decision.

## Account facts (read-only GET /v1/account, 2026-10-26 ~02:12 IST)

- Magic Hour balance: 137,493 credits (creator tier). Balance read only; no charge, generation or mutation.

## Reference-type contract validated against the actual model contract (not the SDK union)

Source: endpoint reference, fetched 2026-10-26:
https://docs.magichour.ai/api-reference/video-projects/text-to-video
Quoted contract: "Reference media for video generation... Maximum 10 references total. Supported models and reference media: gemini-omni-1.1: images, videos, up to 10. kling-3.0: images, videos. minimax-h3: images, videos, audio. seedance-2.0 / 2.0-fast / 2.0-mini / 2.5: images, videos, audio. veo3.1: images, up to 3, requires end_seconds of 8. wan-3.0: images, videos, audio." Per-model duration ranges and audio-toggle pricing from the same page and https://docs.magichour.ai/api-reference/models match `magichour_catalog.py` exactly (spot-rechecked after this fetch; no drift).

Consequences for model selection: kling-3.0, veo3.1, gemini-omni-1.1 are EXCLUDED from any spoken-shot probe (no audio references). Eligible audio-reference models: minimax-h3 (48 cr/s @720p), wan-3.0 (96), seedance-2.0-mini (192), seedance-2.0 (288), seedance-2.5 (576).

### Pending unknowns the docs do not answer (probe must establish empirically)

1. Audio-reference semantics: nowhere do the docs state what an audio reference DOES - soundtrack direction, voice timbre guidance, or exact-waveform use. Exact-soundtrack preservation and lip sync are NOT documented anywhere.
2. Whether an audio reference counts toward the 10-reference cap (the cap text says "references total" without per-kind breakdown).
3. Per-reference file size/duration limits and accepted audio formats for uploads.
4. Interaction between the `audio: true` native-audio toggle and an audio reference on the same job (both, either, precedence).

## The probe: one contiguous connected sequence, e01s07 -> e01s08 -> e01s09 -> e01s10 (23s)

Four actually-adjacent shots forming one continuous action beat on the dance floor, chosen because the script gives explicit physical state at every cut, so cut continuity is testable rather than vibes:

- e01s07 (4s, close, Draconia visible SPEAKING): "Then count faster." END STATE: Draconia grinning mid-dance, both dancing on the corrected beat, close framing.
- e01s08 (7s, wide, Harry visible, Draconia offscreen voice "Show-off."): START STATE: wide of the same floor position, both dancing (matches s07 end). END STATE: Harry's right wrist wrapped by a silver string, two cut strings falling.
- e01s09 (5s, close, Draconia visible, Harry offscreen "Efficient."): START STATE: Draconia at Harry's wrapped wrist (matches s08 end - the wrap must be visible). END STATE: Draconia pulling Harry upright, both back in dance hold.
- e01s10 (7s, wide, Draconia visible SPEAKING "I definitely planned that."): START STATE: wide, both upright in dance hold (matches s09 end). END STATE: Draconia ducking an armor swing, drinks trolley mid-roll.

This covers both questions with one spend: cut-to-cut continuity (identity, wardrobe, positions, prop state across 3 cuts) AND visible-speech behavior (s07 close and s10 wide), including what the output audio actually contains.

References per shot from the hash-bound 10-PNG bank, plus the accepted E01 waveform slice for each line as an audio reference (zero new voice cost):
- s07: @draconia_front_close @draconia_speaking_profile @yule_ball_location + audio e01s07l1
- s08: @harry_fullbody @two_shot_action @yule_ball_location + audio e01s08l1
- s09: @draconia_front_close @two_shot_action @yule_ball_location + audio e01s09l1
- s10: @draconia_fullbody @two_shot_action @yule_ball_location + audio e01s10l1

## Exact quote (durations 4+7+5+7 = 23s @720p, audio toggle on, rates verified 2026-10-26)

| model | cr/s | credits |
|---|---:|---:|
| minimax-h3 | 48 | 1,104 |
| wan-3.0 | 96 | 2,208 |
| seedance-2.0-mini | 192 | 4,416 |
| seedance-2.0 | 288 | 6,624 |
| seedance-2.5 | 576 | 13,248 |

Cheapest eligible: 1,104 credits on minimax-h3 = 0.8% of the 137,493 balance. Model upgrade choice belongs to the user with this table, not to a default. All durations are within every listed model's verified duration range.

## Review requirements (corrected; the earlier mouth-tracker promise is withdrawn)

Automated mouth-drift measurement (0.25s tolerance) is a SCREEN ONLY. Measured mouth motion does not certify the words. Every probe output requires:

1. Full-speed human watch + listen of the actual API output, no slow-motion-only review.
2. Audio-content identification: state plainly what the output audio track contains - the reference dialogue as words, different generated speech, music/ambience only, or silence. This answers pending unknown #1 with evidence.
3. Lip-motion plausibility against the HEARD words at full speed (human judgment; the tracker number is supporting evidence, not proof).
4. Identity review against the bank PNGs per visible character per shot.
5. Action review against the script beat per shot.
6. Emotional-delivery review against the E01 per-line detailing (lines 6, 7, 8, 9 of the addendum).
7. Cut-continuity review: each shot's end state vs the next shot's declared start state (positions, wardrobe, prop state - specifically the wrist wrap across the s08->s09 cut).

Outcome rule: R2V becomes a candidate route for connected episode footage only if items 1-7 pass on all four shots. If spoken shots fail 2 or 3 but continuity passes, R2V is scoped to non-speaking shots and spoken shots stay on the exact-audio + lip-sync route.

## 3-episode arc + emotional-direction review (E01-E03)

- Arc coherence: E01 ends on Draconia's "I tried to warn you"; E02 opens on Harry demanding exactly that answer and ends on the curse demanding honesty; E03 forces the confession mid-flight and ends on Harry choosing to go in "honest. All of it." The through-line (warning -> demand -> confession -> chosen honesty) holds across all three; each episode ends on a cliffhanger inside 95-105s, within the 60-180s bounds, no padding.
- Emotional direction: E01 plays thrill and wit with fear landing only on the final line; E02 adds suspicion, family shame and the first real fear-for-him (E02 lines 9, 12, 13 are its floor); E03 breaks the deflection entirely and lands the season's first quiet Harry line as the angriest. Escalation is monotone; no repeated beat.
- E01 gap now CLOSED: E01-script-v2-detailing-addendum.md (uploaded alongside) adds per-line detailing for all 17 E01 lines in the same format as E02/E03, lexicon-validated.
- Voice quality still pending human listening review: tags and stability settings are direction, not proof of emotional delivery. That review is owed on any new voice pass before video.
