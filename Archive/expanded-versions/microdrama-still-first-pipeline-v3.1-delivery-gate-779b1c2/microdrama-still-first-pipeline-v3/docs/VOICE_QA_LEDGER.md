# E01 v3 voice QA ledger

Subjective naturalness still requires human listening. This ledger tracks submitted characters and transcript/segment QA only; it does not claim final emotional quality.

| Render | Segments | Submitted chars | Disposition |
|---|---:|---:|---|
| Initial v3 dialogue render | 19 | 1,005 | Discarded: generated before editorial correction; wrong script. |
| v3.2 full 15-line render | 15 | 709 | Preserved as emotional-performance reference; not final because it contains the old armor wording. |
| Duplicate full v3.2 render | 15 | 709 | Discarded: started before segment-only instruction and did not apply the line change. |
| Line 10, "armor is moving" | 1 | 52 | Discarded: readback heard "army". |
| Line 10, "suits of armor" | 1 | 62 | Preserved clean source clip; readback exact. |
| Lines 9-10 splice diagnostic | 2 | 122 | Discarded after splice boundary artifacts. |
| Lines 8-10 splice diagnostic | 3 | 179 | Discarded after splice boundary artifacts. |
| Lines 7-11 clean block | 5 | 262 | Preserved clean source clip for assembly diagnosis. |
| Total | - | 3,100 | Submitted characters, not a Magic Hour credit charge. |

Assembly note: quick MP3 splices at API segment boundaries produced transcript artifacts around neighboring lines. Do not use those previews. Preserve the clean source clips and assemble later from timestamps in PCM with short crossfades, or do one full render only after the script is fully locked.


ElevenLabs account meter checked at 15:19 IST: 2,524 characters used in the current monthly period out of 131,000. The request ledger totals 3,100 submitted characters, so the meter does not map one-to-one to submitted text across every render; no pre-run baseline was recorded, so the table above is the exact request-level ledger.

## PCM preview assembly, 15:24 IST

A rough 51.39 second PCM preview was assembled without another paid voice render by replacing the old line-10 region with the clean corrected source clip. The preview is not production-final: automated readback still reports splice/boundary artifacts around the replaced block, so it needs human listening and likely one final clean full render only after the text is fully locked. Two CC-BY music preview mixes were made locally with Grand Dark Waltz Moderato and Dark Dance at low volume with fades; no generation credits were used.

## Join-artifact root cause, 15:27 IST

The API's reported segment boundaries do not always match audible speech tails after accumulated pauses. Example: normalized alignment placed line 9's end at 27.92s, while waveform silence inspection showed speech continuing to about 28.98s. Hard cuts at API timestamps therefore clipped the previous line or retained the old line's tail, which produced the missing/duplicate transcript artifacts. Recovery rule: derive joins from waveform-detected silence with padding, or render final audio once after text lock. Do not keep retrying full renders for one segment.

## Clean block render, 15:33 IST

- Lines 6-12 clean block: 7 segments, 359 submitted characters.
- Automated readback is coherent for the block itself. Full-preview splicing still clips neighboring tails because the original full render's audible boundaries differ from API timestamps. Keep the clean block as source; do not show rough splice previews as user-ready.
- Request-level ElevenLabs ledger is now 3,459 submitted characters.

## Final full text-locked render, 15:35 IST

- Final E01 v3.2 voice render: 15 segments, 721 submitted characters, 49.4 seconds.
- Automated readback matches all 15 locked lines exactly, including line 10: "The suits of armor are moving. We need that trolley."
- This final full render replaces all splice/preview attempts. The earlier clean blocks remain diagnostic sources only and are not used in the final assembly.
- Request-level ElevenLabs ledger is now 4,180 submitted characters.
- Low-volume CC-BY 4.0 music preview mixes were made against the final render with Grand Dark Waltz Moderato and Dark Dance. Attribution remains mandatory.
