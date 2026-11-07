# COLD CYCLE — Director's script (v2, about 60 s, 15 shots × 4 s)

Status: DRAFT FOR APPROVAL. Nothing in here has been rendered or spent. The coordinates are hand-calculated and still have to pass `check_blocking` before any credit is used.

Logline: At 2 a.m. in an empty laundromat, a stranger comes in to wash a single red scarf. The woman folding clothes understands, shot by shot, that it is the last thing he has of someone.

Hook title (0:00–0:03, top of frame): "At 2 a.m., he washed one scarf…"
End card (0:57–1:00, top of frame): "Some things aren't ready to be washed."

---

## 0. Why the earlier films went wrong, and the rule that stops each one

| Mistake you found | Cause | Rule in this script |
|---|---|---|
| Objects beside her near the walls vanish in later shots | Every first frame was generated separately, so each invented its own wall | Each side of the room has ONE master first frame. Every shot on that side starts from that same image. The wall objects are painted into the master and listed per shot as MUST SHOW |
| The woman seems to move position each shot | Distance and position were re-invented per frame | Fixed floor-plan coordinates and a fixed camera per side. Each person's mark is the same in every shot of that side. The checker fails the script if anyone moves more than 0.4 m between consecutive shots, unless the shot shows the move |
| A seated or standing person looks different | Posture was never fixed | Dev always stands at machine 7 until S14. Nora always stands at the table until S14. Postures are listed per shot |
| Background changes at a reverse shot | The model has no idea what is behind the camera | Every shot lists what is behind the person and what must NOT be in frame |
| Colour jumps at cuts | Each frame had its own look | The masters share one light recipe; the grade is measured against S1 and applied in assembly |
| Stray words added | Veo fills pauses with speech | Lines are short, with no ellipses or pauses inside them. Every shot is transcribed after rendering. Silent shots must stay silent. Fail means re-render |

---

## 1. The set (metres; x runs west to east 0–8, y runs south to north 0–5, ceiling 2.8)

A cramped 24-hour laundromat on a rainy night. No set element ever moves or changes between shots.

SOUTH WALL (y = 0)
- Glass front door, x 1.0–2.0, z 0–2.1, push bar, brass bell on a spring above it at z 2.2.
- Large shop window, x 3.0–7.0, z 0.9–2.2, rain streaking, a red neon sign outside (reads "OPEN", mirrored from inside) so red light lands on the floor and on the table's near edge.

NORTH WALL (y = 5)
- Five front-loading washers numbered 3, 4, 5, 6, 7, each 0.7 m wide, 0.7 m deep (occupying y 4.3–5.0), drum doors centred at z 0.95:
  - 3: x 2.0–2.7, 4: x 2.8–3.5, 5: x 3.6–4.3, 6: x 4.4–5.1, 7: x 5.2–5.9.
- Faded notice board on the wall above washers 3–4, x 2.3–3.5, z 1.7–2.2: a yellow "LOST CAT" flyer, two business cards, a curled timetable.
- Vending machine, x 6.4–7.2, y 4.4–5.0, height 1.8 m, glowing blue.
- Green wall clock above the vending machine at x 6.8, z 2.2. It reads 2:04 throughout.

EAST WALL (x = 8)
- Three stacked-pair dryers (steel, round glass doors), front faces at x = 7.3, y 1.2–4.2.

WEST WALL (x = 0)
- Laminated price sign "WASH & FOLD", y 0.4–1.4, z 1.6–2.1.
- Two orange plastic chairs against the wall, centred at (0.4, 1.2) and (0.4, 1.9), facing east.

CENTRE
- Steel folding table, x 3.0–5.0, y 1.8–2.6, height 0.9. On it: Nora's grey plastic basket (x 3.4–3.9), a stack of folded towels.
- Floor: pale grey vinyl with scuffs. Wet footprints near the door from S3 onward.

LIGHT (identical in every shot): cold overhead fluorescent strips, 5000 K, a very faint hum with an occasional micro-flicker (S1 only). Warm red neon wash from the south window, strongest on the floor and the table's near edge. Blue glow from the vending machine on anything near x > 6. No light ever switches on or off.

SOUND BED (continuous in every shot): rain on glass, the fluorescent hum, a distant machine rumble. Nothing else unless a cue is listed.

---

## 2. People and props

NORA (early 30s, 1.65 m): dark hair tied back in a loose bun with one strand loose at the left of her face, mustard raincoat worn open over a cream knit sweater, dark jeans, white trainers. Calm, alert, tired. Small gestures. Never theatrical.

DEV (late 30s, 1.80 m): short dark hair damp, two-day stubble, grey zip hoodie (hood DOWN after S3), dark jeans, wet black trainers. Slow movements, shoulders slightly forward. Eyes wet but he does not cry.

PROPS (fixed)
- The scarf: deep red wool, about 1.5 m long, folded in quarters, one frayed end. Dev has it in a clear plastic bag from S3, takes it out in S7, puts it in the drum in S7, and it stays in the drum to the end. After S7 it never appears outside the drum.
- Tokens: three brass laundromat tokens. Nora gives them in S6.
- Nora's towel: pale blue. In her hands in S2–S11, set down on the table on the line in S11.
- Orange chair: Nora pulls one from the west wall to the dryer side in S14 (the only moved object in the film).

---

## 3. Master first frames (the anti-drift system) — about 250 credits

Each is generated once, checked by eye, edited until correct, then reused as the first frame of every shot listed.

| Master | Used by | Camera | What must be visible in it |
|---|---|---|---|
| **W — wide from the door** | S1, S15 | (1.5, 0.35, 1.55) looking at (5.0, 3.0, 1.1), 24 mm | The whole room: table with Nora behind it, washers 3–7 along the far wall, vending machine, dryers on the right, window to the left. Nora at her mark. For S3 and S15, a separate edit of W adds Dev (S3: at the door; S15: at machine 7) |
| **A — Nora's side** | S2, S4, S8, S10, S11, S14 | (5.9, 3.9, 1.55) looking at Nora (4.0, 2.9, 1.5), 35 mm | Nora centred at 2.1 m, facing slightly toward camera. Dev's shoulder soft in the right foreground (dark, hood down). BEHIND her: the west wall with the WASH & FOLD sign and the two orange chairs, the glass front door at the left edge, red neon on the floor |
| **B — Dev's side** | S5, S9, S12 | (3.2, 2.3, 1.55) looking at Dev (5.55, 3.8, 1.5), 35 mm | Dev centred at 2.7 m, facing 211° toward camera. Nora's shoulder (mustard coat) soft in the left foreground. BEHIND him: washers 6 and 7, the vending machine glowing blue at right, the green clock. The south window and the dryers are NOT visible |
| **E — from the dryer wall** | S3 | (7.0, 1.2, 1.5) looking at (1.5, 0.9, 1.3), 24 mm | The door in the middle distance with Dev in it, the window at the left, the sign and chairs on the far wall |
| **I1 — hands and tokens** | S6 | (3.9, 3.3, 1.35) looking at the table-edge hand-off point (4.5, 3.4, 1.0), 50 mm | The two hands, the brass tokens, the steel table edge |
| **I2 — drum** | S7 (Dev's hands), S13 (the drum) | (5.55, 3.2, 1.2) looking at machine 7's door (5.55, 4.3, 0.95), 50 mm | Machine 7's round glass door, "7" in white paint, Dev's chest-level hands for S7 |

Rule: the wall objects in A (sign, chairs, front door) and in B (washers 6 and 7, vending machine, clock) are painted into the masters first, because the video model copies what the first frame contains.

---

## 4. Shot-by-shot (time-coded)

Format per shot: TIME / CAMERA / IN FRAME / NOT IN FRAME / MARKS / SECOND-BY-SECOND / SOUND / FIRST FRAME / CUT IN.
"Mouth closed" means no speech at all; in those shots the prompt also says: "No one speaks."

### ACT 1 — ARRIVAL

**S1 · 0:00–0:04 · WIDE, silent · master W**
- CAMERA: from the door (1.5, 0.35, 1.55) looking toward (5.0, 3.0, 1.1), 24 mm, very slow push in about 5%, eye level.
- IN FRAME: Nora at the table, washers 3–7 on the far wall, vending machine glow at the right, dryers at the far right, window at the left with rain.
- NOT IN FRAME: Dev, the west wall.
- MARKS: Nora at (4.0, 2.9), facing 270° (south, looking down at the table). Dev: not present.
- 0.0–1.0 Nora folds a pale blue towel in thirds, steady rhythm.
- 1.0–2.0 She smooths it flat with both palms and stops, listening to the rain.
- 2.0–2.2 The neon outside flickers once (the only flicker in the film).
- 2.2–3.2 She lifts the towel, shakes it out and starts a new fold.
- 3.2–4.0 Her head turns a few degrees toward the sound of footsteps outside. No dialogue.
- SOUND: rain, hum, distant dryer rumble. A faint bell-jingle at 3.6 s (door about to open).
- FIRST FRAME: master W.
- CUT OUT: hard cut to S2 on the head turn.

**S2 · 0:04–0:08 · NORA, medium close-up, silent · master A**
- CAMERA: master A (5.9, 3.9, 1.55) to Nora, 35 mm, slow push in about 4%.
- IN FRAME: Nora centred, sign and chairs behind her, door at the left edge.
- NOT IN FRAME: the dryers, the washers, the vending machine.
- MARKS: Nora at (4.0, 2.9) facing 28°.
- 0.0–0.8 Her hands keep folding while her eyes lift to the door.
- 0.8–1.4 The door-bell rings (sound only). Her hands stop mid-fold.
- 1.4–2.6 Her eyes follow someone entering from the left of frame toward the camera-side, tracking about 40 degrees. Her expression: mild surprise, no smile.
- 2.6–4.0 She breathes out slowly and looks back down at the towel. She resumes the fold slowly.
- SOUND: bell at 0.8, hurried wet footsteps beginning at 1.5.
- FIRST FRAME: master A.

**S3 · 0:08–0:12 · WIDE, DEV ENTERS, silent · master W-edit (Dev at the door)**
- CAMERA: master E, from the dryer wall at (7.0, 1.2, 1.5) looking west at the door (1.5, 0.9, 1.3), 24 mm, slow drift about 3%. Looking west, the south window is on the left, the door in the middle distance, the WASH & FOLD sign and orange chairs on the far wall.
- IN FRAME: Dev entering, hood up, rain dripping, plastic bag in his left hand. Nora in the distance at her table.
- NOT IN FRAME: the washers, the vending machine.
- MARKS: Dev from the door (1.5, 0.6) to (3.2, 1.8) over 4 s, facing 45°. Nora at (4.0, 2.9).
- 0.0–1.0 Dev shakes rain off his shoulders and lowers his hood. Wet footprints on the floor.
- 1.0–2.4 He looks around the room once, avoiding Nora's eyes.
- 2.4–4.0 He walks toward the washers along the table's south edge, clutching the bag.
- SOUND: door-bell settles, wet footsteps, rain louder through the open door then muffled.
- FIRST FRAME: master E with Dev at the door (an edit of the empty-room frame, Nora small and soft at the table's far side).

**S4 · 0:12–0:16 · NORA SPEAKS · master A**
- CAMERA: master A, slow push in about 4%.
- MARKS: Nora (4.0, 2.9) facing 28°. Dev's shoulder soft at the right foreground, hood already down, grey hoodie.
- 0.0–1.0 Nora watches him pass with the towel in her hands.
- 1.0–3.0 She says (low, kind, unhurried): "Cards only. I have spare tokens." Her eyes soften; she holds the towel against her chest.
- 3.0–4.0 She waits for his answer.
- LINE: "Cards only. I have spare tokens." (6 words)
- MUST SHOW: the sign, the chairs, the door at left. MUST NOT: any other background.

### ACT 2 — THE SCARF

**S5 · 0:16–0:20 · DEV SPEAKS · master B**
- CAMERA: master B (3.2, 2.3, 1.55) to Dev, 35 mm, slow push in about 4%.
- MARKS: Dev (5.55, 3.8) facing 211°. Nora's mustard shoulder soft at the left foreground.
- 0.0–0.8 Dev, at the machine, turns his head toward Nora, caught off guard.
- 0.8–3.0 He says (quiet, hoarse): "That would help. Thank you." A small nod.
- 3.0–4.0 His eyes drop to the plastic bag in his hand.
- LINE: "That would help. Thank you." (5 words)
- MUST SHOW: washers 6 and 7, the vending machine glow at right, the green clock. MUST NOT: the window, the dryers.

**S6 · 0:20–0:24 · TOKENS INSERT, silent · master I1**
- CAMERA: (3.9, 3.3, 1.35) looking at (4.5, 3.4, 1.0), 50 mm, static with a tiny drift (about 1%).
- IN FRAME: Nora's right hand holding out three brass tokens from the table's north edge; Dev's left hand enters from the right.
- 0.0–1.0 Her hand offers the tokens, palm up.
- 1.0–2.0 His hand takes them; their fingers do not touch.
- 2.0–3.2 He closes his fist around them.
- 3.2–4.0 His thumb strokes once over a token.
- SOUND: tokens clink at 1.2 and 2.0; rain.
- NOTE: this is the only shot where Nora and Dev's hands share a frame.

**S7 · 0:24–0:28 · THE SCARF, silent · master I2**
- CAMERA: (5.55, 3.2, 1.2) looking at machine 7's door (5.55, 4.3, 0.95), 50 mm, static with a drift of about 1%.
- IN FRAME: machine 7's glass door and "7" in white paint, Dev's two hands at chest level, the plastic bag.
- 0.0–1.0 He unrolls the top of the bag.
- 1.0–2.4 He draws out the red scarf and holds it, thumb on the frayed end, a beat too long.
- 2.4–3.4 He lowers it into the open drum, folded.
- 3.4–4.0 He closes the door, the latch clicks, and he leaves his hand flat on the glass.
- SOUND: plastic rustle, the latch clunk at 3.5, rain.

**S8 · 0:28–0:32 · NORA SPEAKS · master A**
- MARKS: Nora (4.0, 2.9) facing 28°. Towel in hands.
- 0.0–1.0 She watches him over the table; her expression slowly changes from polite to curious.
- 1.0–3.0 She says, gently: "Just the one scarf?" Her head tilts about 5 degrees.
- 3.0–4.0 She waits, the towel still in her hands.
- LINE: "Just the one scarf?" (4 words)

**S9 · 0:32–0:36 · DEV SPEAKS · master B**
- MARKS: Dev (5.55, 3.8), facing 211°, hand flat on the closed drum door.
- 0.0–1.0 He stares at the drum, then turns his head slightly toward the camera.
- 1.0–3.0 He says (very quiet): "It still smells like her." His jaw tightens on "her".
- 3.0–4.0 His eyes close for a moment; he opens them again.
- LINE: "It still smells like her." (5 words)

**S10 · 0:36–0:40 · NORA REACTS, silent · master A**
- MARKS: Nora (4.0, 2.9), facing 28°.
- 0.0–1.2 She has stopped folding. Her hands rest on the towel.
- 1.2–2.6 Her eyes move to the drum (off-screen, toward the camera side); her breath catches.
- 2.6–4.0 She presses her lips together, a small nod to herself.
- SOUND: rain, hum, one slow drip off Dev's sleeve (off-screen).

**S11 · 0:40–0:44 · NORA SPEAKS · master A**
- MARKS: Nora (4.0, 2.9) facing 28°.
- 0.0–1.0 She sets the pale blue towel on the stack, squaring its edge.
- 1.0–3.0 She says, warmly: "Then wash it cold and slow." A very small smile.
- 3.0–4.0 She keeps her eyes on him.
- LINE: "Then wash it cold and slow." (6 words)
- MUST SHOW: the towel is now on the stack at the table.

### ACT 3 — STAYING

**S12 · 0:44–0:48 · DEV SPEAKS · master B**
- MARKS: Dev (5.55, 3.8), facing 211°.
- 0.0–1.0 He listens, then a breath that is almost a laugh.
- 1.0–3.0 He says: "She always said that." His mouth trembles into a small, broken smile.
- 3.0–4.0 He wipes under one eye with the heel of his hand.
- LINE: "She always said that." (4 words)

**S13 · 0:48–0:52 · THE DRUM, silent · master I2**
- CAMERA: (5.55, 3.2, 1.2) looking at machine 7's door, 50 mm, push in about 5%.
- 0.0–1.2 Water starts to enter the drum; the scarf is a red shape behind the glass.
- 1.2–3.0 The drum begins to turn slowly; the scarf rolls over once and settles.
- 3.0–4.0 Red neon light slides across the glass as it turns.
- SOUND: water filling, the motor starting, a slow rhythm.
- NOTE: no people in frame.

**S14 · 0:52–0:56 · NORA SPEAKS · master A**
- MARKS: Nora begins at (4.0, 2.9) and ends at (4.0, 2.9). Her hands move to the orange chair; the chair stays at the west wall until the end (she is only reaching and pointing).
- 0.0–1.0 She glances at the orange chair in the background, beside the sign.
- 1.0–3.0 She says, softly: "I'll wait with you." and gives a small nod toward the chair.
- 3.0–4.0 She holds his eyes with a small, honest look.
- LINE: "I'll wait with you." (4 words)
- NOTE: the chair is not moved on camera; the cut to S15 hides the move.

**S15 · 0:56–1:00 · WIDE, silent · master W-edit (both seated)**
- CAMERA: master W (1.5, 0.35, 1.55), slow pull back about 5%.
- MARKS: Nora and Dev are seated on two orange chairs placed in front of machine 7 (x 5.0–6.0, y 3.2), side by side, facing north, backs to the camera, watching the drum.
- 0.0–1.5 They sit without speaking. The drum turns, red light on the glass.
- 1.5–3.0 Nora's head tilts a few degrees toward Dev. Dev doesn't look, but his shoulders drop.
- 3.0–4.0 The camera holds. End card appears at the top of the frame.
- SOUND: rain, the drum rhythm, the score swelling then fading.
- FIRST FRAME: master W-edit with both seated.

---

## 5. Sound

- BED: rain on glass, fluorescent hum, distant rumble in every shot.
- EFFECTS (exact): bell 3.6 s in S1 and 0.8 s in S2; wet footsteps S2–S3; tokens S6; plastic rustle and latch clunk S7; water and drum motor S13.
- SCORE: sparse piano and a low cello, 60 s, ducked under speech, rising slightly in S11–S14, fading after S15. About 60 credits.
- DIALOGUE: one speaker per shot, 4–6 words, no pauses inside lines.

## 6. Blocking continuity sheet (what the checker verifies)

| Shot | Nora (x, y, facing) | Dev (x, y, facing) | Camera |
|---|---|---|---|
| S1 | 4.0, 2.9, 270° | absent | W |
| S2 | 4.0, 2.9, 28° | entering (off-frame) | A |
| S3 | 4.0, 2.9, 270° | 1.5, 0.6 → 3.2, 1.8 | E |
| S4 | 4.0, 2.9, 28° | 5.55, 3.8 (foreground shoulder) | A |
| S5 | 4.0, 2.9 (shoulder) | 5.55, 3.8, 211° | B |
| S6 | 4.0, 2.9 | 5.55, 3.8 | I1 |
| S7 | 4.0, 2.9 | 5.55, 3.8 | I2 |
| S8 | 4.0, 2.9, 28° | 5.55, 3.8 | A |
| S9 | 4.0, 2.9 | 5.55, 3.8, 211° | B |
| S10 | 4.0, 2.9, 28° | 5.55, 3.8 | A |
| S11 | 4.0, 2.9, 28° | 5.55, 3.8 | A |
| S12 | 4.0, 2.9 | 5.55, 3.8, 211° | B |
| S13 | — | — | I2 |
| S14 | 4.0, 2.9, 28° | 5.55, 3.8 | A |
| S15 | seated 5.0, 3.2 | seated 5.6, 3.2 | W |

Open checks before spending:
1. S3's camera E must see the door and Dev walking in without showing the washers. Run the view report to confirm; if it fails, S3 becomes a medium shot of Dev from the table.
2. S14 to S15: Nora and Dev both move to chairs between shots. This is a 1.5 m jump hidden by the cut. The checker's 0.4 m rule will flag it, so the script marks S15 as a deliberate re-blocking and the film's last shot shows the new positions for 4 s without a cut back.
3. Master A's background (west wall, sign, chairs, door at the left edge) and master B's background (washers 6 and 7, vending machine, clock) must be confirmed visible by the floor-plan view report, not assumed.

---

## 7. The prompt template per shot (about 2,300 characters, built automatically from the script)

SHOT [size, angle, lens, camera move]. FRAMING (exact, from the floor plan): [camera position, who is in frame and where, what is behind them, NOT in frame]. LIGHT: [the fixed recipe]. WARDROBE/PROPS: [exact items and where they are]. BEATS: [0.0–x.x ... timed]. PERFORMANCE: [restrained]. SOUND: [bed + effects]. SPEECH RULES: speak only the quoted words, once, in order, nothing before or after; no interjections or sighs; face toward camera, mouth visible while speaking. (Silent shots: "No one speaks; the actors' lips stay closed.") No music, no subtitles, no text, no watermarks.

Worked example, S9:
> SHOT: medium close-up of Dev at washing machine 7, eye level, 35 mm, very slow push in about 4%. FRAMING (exact): camera at the folding table looks north-east at Dev 2.7 m away, centred, facing the camera; Nora's mustard shoulder soft in the left foreground; behind Dev: washers 6 and 7, the vending machine glowing blue at right, a green wall clock reading 2:04; NOT in frame: the south window, the dryers, the front door. LIGHT: cold overhead fluorescent, faint red neon wash from the left, blue vending-machine glow at right; unchanged from every other shot. DEV: late 30s, damp short dark hair, two-day stubble, grey zip hoodie with the hood down, dark jeans; one hand flat on the closed round glass door of machine 7. BEATS: 0.0–1.0 he stares at the drum, then turns his face toward the camera; 1.0–3.0 he speaks the line quietly, jaw tightening on "her"; 3.0–4.0 his eyes close once, then open. PERFORMANCE: restrained, no tears running, small movements. SOUND: rain on glass, fluorescent hum, distant rumble. SPEECH RULES: speak only the quoted words, once, in order, nothing before or after: "It still smells like her." Face toward camera, mouth visible while speaking.

---

## 8. Process and cost

Order (staged, nothing paid without your eye on it):
1. Run `check_blocking` on the coordinates above and fix anything it flags (free).
2. Build masters W, A, B, I1, I2 and the two W-edits, about 8 frames, 400 credits. You review each by eye before any video is paid for.
3. Render S1 to S15, one at a time, each transcribed immediately. A shot whose speech or room check fails is re-rendered once; a second fail stops and I report.
4. Assemble: measured grade against S1, ducked score, ASR-timed captions, hook and end card.

Estimated credits:
- 15 video shots × 288: 4,320
- 8 first frames: 400
- Score: 60
- Re-render reserve (two shots): 576
- **About 5,350 in total.**

Honest limits: voices, lip sync and acting can't be judged by my tools, and Veo may add speech or drift in silent shots. Camera pushes of 4–5% are used on purpose to keep the framing near-constant.
