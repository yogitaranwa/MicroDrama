# v9 REVIEW DRAFT - proposed changes, NOT approved production timing (2026-10-26)

This export carries reversible code/plan proposals for review. Nothing here is
approved production timing, approved wardrobe change, or spend authorization.
v7 remains the current delivered artifact.

Proposed (editable, reversible):
1. s16 restructure: 2 beats/7s -> 3 beats/9s. New 2.0s wordless opening insert
   covers the canonical chandelier crash EVENT (fall -> crash -> ice swallow)
   and the masked figure applauding without sound; the CU line beat and hands
   insert are unchanged. audio_offset_s=2.0 starts the approved voice take
   after the wordless opening; the accepted audio is never cut or retimed
   (proven by a real-ffmpeg test: merged video exactly 9.00s, take starts at
   exactly 2.00s, intact).
2. Harry wardrobe wording pinned (black red-lined robes, white shirt, dark
   necktie) in 6 prompts. PROVISIONAL: one reference image (front close-up)
   shows a bow tie, two others show a necktie; the pin follows the 2-of-3
   majority and remains reversible. The inconsistent reference image itself is
   unchanged.
3. Honest billing totals: the manifest now shows both the legacy whole-shot
   total (28,896 cr) and the staged per-unit total (29,568 cr) that the video
   stage would actually charge. Neither is a budget approval.

Known unproven risks (no 100% claims):
- The 2.0s crash+applause insert is a staging judgment, not proven visual
  feasibility; the applause may under-register at wide. Not yet frame-tested.
- The tie pin mitigates wording-level drift only; the contradictory reference
  image can still pull generations toward a bow tie.

Suite: 52/52 local tests green at commit 3a82f28.
