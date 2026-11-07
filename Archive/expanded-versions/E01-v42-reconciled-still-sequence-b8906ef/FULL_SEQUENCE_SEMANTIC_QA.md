# E01 full-sequence semantic QA, 15:48 IST

This pass checks each still against the script action, visible props, wardrobe continuity, identity continuity, footwear, hair ornaments, readable text, and cinematic photorealistic style. It replaces the earlier over-broad "accepted working anchors" label.

Canonical wardrobe: Harry wears white shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and a plain black formal robe with a thin red inner lining. Draconia wears the emerald embroidered sleeveless Yule gown with sheer dark green shoulder drapes, emerald formal shoes, and a platinum braided updo made only of hair with at most one small jeweled side pin.

| Shot | Selected source | QA result |
|---|---|---|
| 1 | v38 `shot01-entry-spark` | PASS. Harry identity and canonical robe/waistcoat/shoes read; black spark appears in the window reflection. |
| 2 | accepted `ref-two-shot-action`, lower crop | PASS. Accepted identity source; Harry robe and red lining visible; Draconia pull/dance action reads. No garment change introduced. |
| 3 | v32 `shot03-dialogue-close-r2`, derived lower crop | PASS as an insert. Frozen guest and glowing floor warning ring are explicit; crop removes the rejected Harry white-shirt/robe-off-shoulder region. |
| 4 | v42 targeted edit from v38 shot04 | PASS. Masked figure is now faint, blue and semi-transparent inside the window panes, reading as a reflection; couple and canonical wardrobe preserved. |
| 5 | accepted `ref-two-shot-action`, upper crop | PASS. Arrow volley and accepted identities read; distinct crop from shot2. |
| 6 | v39 `shot06-ward-mark-repair` | PASS. Abstract green ward mark, ice-arrow holes, no readable words; Harry robe/waistcoat and Draconia canonical gown/updo read. |
| 7 | v38 `shot07-strings-wand` | PASS. Wooden wand and silver strings read; Harry robe/waistcoat and Draconia canonical gown/updo read. |
| 8 | v39 `shot08-armor-trolley-repair`, derived lower crop | PASS as an action insert. Trolley, armor, Harry's black robe tail, formal shoes and Draconia's gown/shoes read; crop removes the rejected white-sleeve/no-robe upper-body contradiction. |
| 9 | v38 `shot09-trolley-armor-mask` | PASS. Harry's black robe is visible; trolley and masked figure read. Armor is established by shot8. |
| 10 | v38 `shot10-floor-grid-red-table` | PASS. Floor grid, red table, Harry robe/waistcoat and Draconia canonical gown/updo read. |
| 11 | v34 `shot12-over-shoulder` | PASS. Harry black robe and green/silver marks read; masked figure is present. This replaces v40 because v40 showed Harry without the robe and included a background blade-like prop. |
| 12a | v34 `shot12-over-shoulder`, tighter derived crop | PASS. Harry-facing marks closeup preserves actual pixels from shot11 and keeps hand/mark continuity through the cut. |
| 12b | accepted `ref-draconia-front-close` | PASS. Accepted Draconia face, hair-only braided updo and gown; no hands required after 12a establishes the marks. |

Rejected or superseded in this reconciliation:

- v38 shot02: black tailored jacket/no visible red lining and weaker Harry identity; replaced by accepted two-shot action reference crop.
- v39 shot03 full frame: giant vertical magic circle did not satisfy the floor-warning action; replaced by v32 floor-warning crop.
- v38 shot04 original: masked figure could read as levitating outside the window; replaced by v42 true-reflection edit.
- v39 shot08 full frame: Harry white shirt sleeves/waistcoat without the black robe; replaced by lower action insert crop.
- v40 shot11: Harry without the robe and background blade-like prop; rejected.
- v31 shot08: Draconia tiara/crown drift; rejected.

No video generation jobs have been launched. The reconciled still sequence is the required pre-video gate.
