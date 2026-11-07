# E01 full-sequence semantic QA, v4.3 updated, 16:01 IST

This pass checks each still against the script action, visible props, wardrobe continuity, identity continuity, footwear, hair ornaments, readable text, and cinematic photorealistic style. It corrects the earlier overclaim that armor was established by the first shot8 crop.

Canonical wardrobe: Harry wears white shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and a plain black formal robe with a thin red inner lining. Draconia wears the emerald embroidered sleeveless Yule gown with sheer dark green shoulder drapes, emerald formal shoes, and a platinum braided updo made only of hair with at most one small jeweled side pin.

| Beat | Selected source | QA result |
|---|---|---|
| 1 | v38 `shot01-entry-spark` | PASS as a still. Harry identity and canonical robe/waistcoat/shoes read; black spark appears in the window reflection. |
| 2 | accepted `ref-two-shot-action`, lower crop | PASS as a still. Accepted identity source; Harry robe and red lining visible; Draconia pull/dance action reads. |
| 3 | v32 `shot03-dialogue-close-r2`, derived lower crop | PASS as an insert. Frozen guest and glowing floor warning ring are explicit; crop removes the rejected Harry white-shirt/robe-off-shoulder region. |
| 4 | v42 targeted edit from v38 shot04 | PASS as a still and bounded motion candidate. Masked figure is faint, blue and semi-transparent inside the window panes; couple and canonical wardrobe preserved. |
| 5 | accepted `ref-two-shot-action`, upper crop | PASS as a still. Arrow volley and accepted identities read; distinct crop from beat 2. Motion plan must continue the dancers, not reset them. |
| 6 | v39 `shot06-ward-mark-repair` | PASS. Abstract green ward mark, ice-arrow holes, no readable words; Harry robe/waistcoat and Draconia canonical gown/updo read. |
| 7 | v38 `shot07-strings-wand` | PASS as a still. Wooden wand and silver strings read; Harry robe/waistcoat and Draconia canonical gown/updo read. |
| 8 | v39 `shot08-armor-trolley-repair`, 312x554 vertical lower crop | PASS as a lower-body/action insert. Armor is visible with the trolley, Harry's black robe tail and polished formal shoes; the 9:16 source has no black padding and excludes the rejected white-sleeve/no-robe upper body. |
| 9 | v38 `shot09-trolley-armor-mask` | PASS. Harry's black robe is visible; trolley and masked figure read. Armor continuity comes from beat 8. |
| 10 | v38 `shot10-floor-grid-red-table` | PASS. Floor grid, red table, Harry robe/waistcoat and Draconia canonical gown/updo read. |
| 11a | v43 targeted action edit plus robe and chandelier continuity edits | PASS as a still. Draconia flips the red table as a shield, the chandelier is visibly mid-fall with a snapped chain and scattering crystals, ice/floor grid read, marks begin around joined hands, and Harry's black robe with red lining is restored. This fills the previous missing causality/action coverage. |
| 11b | v34 `shot12-over-shoulder` | PASS. Harry black robe and green/silver marks read; masked figure is present. |
| 12a | v34 `shot12-over-shoulder`, tighter derived crop | PASS. Harry-facing marks closeup preserves actual pixels from 11b and keeps hand/mark continuity through the cut; treat as a cut-in, not a time reset. |
| 12b | accepted `ref-draconia-front-close` | PASS. Accepted Draconia face, hair-only braided updo and gown; no hands required after 12a establishes the marks. |

## Bounded motion validation, 480p MiniMax H3, 4 seconds each

- Beat 1 entry test, 96 credits: PARTIAL/FAIL. Early frames preserve Harry and the window spark, but later frames introduce Draconia even though the source still is Harry alone. Not accepted as final coverage; usable only as a diagnostic or a tightly trimmed early section after review.
- Beat 4 reflection test, 96 credits: PASS for the bounded test. The dance motion remains coherent in sampled frames and the masked figure stays in the window reflection rather than entering the physical ballroom. Low-resolution validation only; final still needs a higher-resolution render.
- Beat 7 strings/wand test, 96 credits: PARTIAL/FAIL. Wand and strings read, but later frames drift Draconia toward loose hair. Not accepted as final coverage; rerender or trim only after a stronger continuity plan.

## Recovery motion validation, 480p MiniMax H3

- Shot1 entry recovery, 3 seconds with the same start/end anchor, 72 credits: PASS. Harry remains alone, canonical wardrobe holds, and the spark stays in the window reflection.
- Shot4 reflection recovery, 3 seconds with the same start/end anchor, 72 credits: PASS. One consistent masked silhouette remains inside the window glass across sampled frames while the couple dances.
- Shot7 strings/wand recovery, 3 seconds with the same start/end anchor, 72 credits: PARTIAL. Draconia keeps the braided updo, Harry keeps the wooden wand, and the strings remain readable, but treble-clef-like musical symbols appear. A later 2-second no-symbol attempt still retained those symbols, so do not claim they were removed. Decision: accept them as coherent magical music-staff visualization tied to the line "The music is carrying the curse"; no more blind spend on this point.
- Shot11 action transition, 4 seconds from shot10 setup to shot11a action anchor, 96 credits: PASS at 480p. The table rises as a shield, the chandelier tilts/drops, marks ignite, and Harry's robe remains on.

## 720p production QA on cleared shots

- Shot1 entry production, 7 seconds, 336 credits: PASS after dense 16-sample review of the actual 720p clip. Harry stays alone, wardrobe holds, the spark remains in the reflection, and the push-in progresses without the midpoint reset seen in the earlier 480p test. The earlier 480p same-sequence test is recorded as a fail for monotonicity, not a pass.
- Shot4 reflection production, 8 seconds, 384 credits: PASS after dense 12-sample review. One masked silhouette stays inside the window glass; the couple's turn is more pronounced than the still but remains coherent and wardrobe holds.
- Shot11 action production, 4 seconds, 192 credits: PASS after dense 10-sample review. The table rises as a shield, the chandelier drops, marks ignite, and Harry's shoes remain black formal shoes with no blade/runner.

## Tool constraints recorded honestly

- Magic Hour `/v1/image-to-video` requires one start image and accepts one optional end image. It does not hard-pin intermediate stills.
- The still sequence is therefore a start/end anchor and QA gate, not a guarantee of every generated mid-frame.
- MiniMax H3 supports 480p, 720p and 1080p, integer durations 1-30 seconds. At 480p it costs 24 credits/second; at 720p it costs 48 credits/second. The three 4-second tests charged 96 credits each as expected.
- Seedream v4.5 image editing returned one 9:16 image per job and charged 50 credits per job.

## Rejected or superseded

- v38 shot02: black tailored jacket/no visible red lining and weaker Harry identity; replaced by accepted two-shot action reference crop.
- v39 shot03 full frame: giant vertical magic circle did not satisfy the floor-warning action; replaced by v32 floor-warning crop.
- v38 shot04 original: masked figure could read as levitating outside the window; replaced by v42 true-reflection edit.
- v39 shot08 full frame: Harry white shirt sleeves/waistcoat without the black robe; replaced by wider lower-body action insert crop.
- First v43 shot11 action edit: table/chandelier action was correct but Harry's robe was missing; replaced by v43 robe continuity edit.
- First v43 robe-continuity action still: chandelier still read as hanging; replaced by v43 chandelier mid-fall edit.
- v40 shot11: Harry without the robe and background blade-like prop; rejected.
- v31 shot08: Draconia tiara/crown drift; rejected.

No full-episode video render has been launched. Only the three bounded 4-second motion tests above have run.
