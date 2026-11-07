# E01 still-route QA ledger

Result: no full still pool has launched. The route is still in staged validation. Images below are test anchors only.

## Credit ledger

| Batch | Jobs | Credits | Result |
|---|---:|---:|---|
| First route probe | 1 | 50 | Wooden wand passed; wardrobe/hair drift found. |
| v3.1 three-image validation | 3 | 150 | Rejected as final anchors. |
| v3.2 two-shot correction | 2 | 100 | Shot 3 improved; shot 12 rejected. |
| Shot 12 text retry | 1 | 50 | Rejected: long side braid returned. |
| Shot 12 targeted edit | 1 | 50 | Rejected: tiara removed but hair changed to a long side braid. |
| Total still-route tests | 8 | 400 | No full-pool approval yet. |

Current verified Magic Hour total including earlier episode work: 7,691 credits.

## v3.1 findings

- Shot 3 rejected: both characters appeared to wear ice skates/blades instead of formal dress shoes. The frozen-guest story action was also wrong.
- Shot 8 partial pass only: hair, faces, broad formal outfits, wand and trolley/armor read correctly, but it was not enough to prove continuity.
- Shot 12 rejected: a prominent jeweled tiara/crown appeared that is not in the accepted Draconia reference.

## v3.2 correction findings

- Shot 3 improved: formal dress shoes are visible, the separate frozen guest is now clear, and the action matches the scene. Harry's robe is draped off one shoulder, so this still needs wardrobe review before becoming an anchor.
- Shot 12 rejected again: the prominent tiara/crown remained.

## v3.3 shot 12 findings

- Text retry removed the tiara but changed Draconia to a long side braid, violating the locked updo.
- Targeted edit removed the tiara but also changed her to a long side braid.
- Decision: stop shot-12 retries for now. The next still prompts must say "braided updo made only of hair" rather than "braided crown", and shot 12 needs a different composition or a stronger edit route before it can anchor the cliffhanger.

## Shot 12 composition recovery, 15:21 IST

- Job `cmvnne5sj06thfz01oglrbesh`: 50 credits.
- Result: usable bounded recovery candidate for Harry's half of the cliffhanger. The camera is over Draconia's shoulder, so only the back of her braided updo is visible; no tiara/headpiece or long side braid appears. Harry's face, robe, joined hands, curse marks, sealed doors and masked figure read clearly.
- Remaining gap: Draconia's final-line face still needs a matching reverse-angle anchor. Do not treat this single composition as full shot-12 coverage.
- Still-route test total is now 450 credits; verified Magic Hour total is 7,741 credits.

## Input contamination and prompt-builder correction, 15:27 IST

Root cause found: the old Harry full-body reference itself contains the buttoned black waistcoat that the current bible forbids. That anchor has been excluded from safe conditioning sets until the canonical garment is decided or a clean no-waistcoat full-body anchor exists. Prompt wording also changed from "braided crown" to "braided updo made only of hair" because the model repeatedly turned crown wording into a physical tiara/crown. The candidate planner now explicitly checks footwear, hair ornament and scene action, and its hard negatives include skates/blades, tiara/crown/headpiece, long side braid, waistcoat and metal cuffs.

Shot 12 reverse-angle test `cmvnnjo0e0b39fu01jx02aetj` (50 credits) is rejected: Draconia changed to a long side braid and Harry gained a metal cuff/bracelet. No further paid still retry is running. Still-route test total: 500 credits; verified Magic Hour total: 7,791 credits.


## Canonical garment decision, 15:29 IST

Decision: Harry's canonical E01 look is the accepted full-body reference: white shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes and the plain black formal robe with thin red inner lining. The no-waistcoat rule was internally authored, not a user preference, and contradicted the accepted reference set. This resolves the earlier shot-12 waistcoat rejection: the over-shoulder composition remains useful for Harry's half of the cliffhanger. Draconia's canonical hair remains the accepted braided updo made only of hair; no tiara/headpiece or long side braid.

## Bounded recovery outcome, 15:30 IST

- Shot 12 over-shoulder `cmvnne5sj06thfz01oglrbesh` is now a usable candidate for Harry's half of the cliffhanger under the corrected canonical bible: black buttoned waistcoat, red-lined robe, no tiara/headpiece, Draconia's braided updo visible only from behind, clear marks and masked figure.
- Shot 12 reverse `cmvnnjo0e0b39fu01jx02aetj` remains rejected: long side braid and metal cuff/bracelet.
- Shot 12 tight reveal `cmvnnoi9p01gnet01ev0jzt6l` is rejected: it violates the cinematic photorealistic requirement and reads illustrated/anime, even though the hair/headpiece and canonical waistcoat are closer.
- Current status: Harry-facing cliffhanger coverage has one candidate; Draconia-facing final-reveal coverage remains unresolved. No full pool is running.
- Still-route test total: 550 credits. Verified Magic Hour total: 7,841 credits.

## Grounded source-edit test, 15:32 IST

- Job `cmvnnrc560wjzew01auo2mboc`: 50 credits.
- Source: verified photorealistic `ref-two-shot-dialogue.png` plus location reference.
- Result: rejected. The edit preserved photorealism and added marks/masked figure, but changed Draconia's accepted updo into a long side braid. This confirms that even grounded source edits can drift hair without a mask or stronger per-region control.
- Still-route test total: 600 credits. Verified Magic Hour total: 7,891 credits.

## Strategy alternatives after source-edit failure

1. Use the passing Harry-facing over-shoulder image for the mark reveal and the verified photorealistic two-shot dialogue reference for Draconia's final-line face; add simple curse-mark overlays locally or in the video pass. This preserves accepted identity and avoids more hairstyle roulette, but the two assets are different compositions.
2. Build a local composite from verified photorealistic anchors, then QA pixels. No generation credits, but manual compositing can look cut-pasted and needs visual proof.
3. Keep the cliffhanger as two shorter shots: Harry-facing marks shot, then Draconia reaction closeup from the accepted dialogue reference. This changes coverage, not story, and is the fastest coherent route.
4. Do not launch the 252-candidate pool until the 12-shot key-anchor pass proves the canonical bible across the full sequence.
