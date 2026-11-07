# Research and upgrade paths

2026-10-25. Every route below is a research option, not authorization to
spend, install or restart production. [W] = vendor/repo documentation,
[P] = proposed path, not implemented or tested here. URLs are the exact
sources fetched during the audit; licenses and hardware numbers are as
recorded there, not re-verified today.

## Mechanisms matched to observed failures

### R7 - Planning and state (targets F22/F23 drift)
Reference-selection approaches pick camera-appropriate views and prior
scene references; action-beat records can represent before/contact/after
phases; continuity checklists cover wardrobe, prop hands/count,
position/facing/eyeline, lighting and endpoints. Applied here as the
reference bank and continuity contract (v2 additions). Limit: a text
reviewer does not prove generated physics; compare actual pixels at
boundaries.

Sources and licenses as recorded:
- ViMax (MIT): https://github.com/HKUDS/ViMax and
  https://github.com/HKUDS/ViMax/blob/main/agents/reference_image_selector.py
- Jellyfish (Apache-2.0): https://github.com/Forget-C/Jellyfish and
  https://github.com/Forget-C/Jellyfish/blob/main/backend/app/services/studio/action_beats.py
- Toonflow (MIT, with historical-license exceptions noted in the audit):
  https://github.com/HBAI-Ltd/Toonflow-app and
  https://github.com/HBAI-Ltd/Toonflow-app/blob/master/packages/teams/storyboardTeam/knowledge/continuity.md
- VideoClaw continuity prompt (license not separately established):
  https://github.com/HITsz-TMG/VideoClaw/blob/main/video-claw/video-claw/backend/prompts/storyboard/staging_continuity_zh.txt

Pin exact versions and dependencies before reuse. Not executed.

### R8 - Action control (targets missing/frozen actions, D1/D9/D11/D14)
Structure-controlled generation (references/masks/pose/depth) targets
missing action more directly than prose prompts. Path: owned blockout or
performance capture with verifiable action phases, then one bounded test
only if separately authorized. The free VACE trial already failed before
synthesis (F24), so this is not a ready free route.

Sources:
- VACE: https://github.com/ali-vilab/VACE/tree/main and
  https://github.com/ali-vilab/VACE/blob/main/UserGuide.md
- Wan2.2 Animate preprocessing:
  https://github.com/Wan-Video/Wan2.2 and
  https://github.com/Wan-Video/Wan2.2/blob/main/wan/modules/animate/preprocess/UserGuider.md

Hardware caution recorded in the audit: Wan's published 24GB figure is for
the T2V 5B model and must not be relabeled as Animate 14B hardware proof.
Model licenses differ per model; check each card before use.

### R9 - Audio-led performance (targets D7/D8 dialogue quality)
Audio-conditioned avatar models take audio streams plus references rather
than only patching mouths; potential fit for a shared dialogue timeline.
Limit: not whole-drama consistency, physical action or acting-quality
proof; multi-GPU examples and exact runtime must be budgeted first.
No model inference was run in this research.

Sources and licenses as recorded:
- LongCat-Video-Avatar-1.5 (weights MIT per model card):
  https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5 and
  https://github.com/meituan-longcat/longcat-video
- MultiTalk (Apache-2.0 source; dependencies licensed separately):
  https://github.com/MeiGen-AI/MultiTalk

### R10 - Lip-only tools (targets D7 sync on readable closeups)
Documented minimums: LatentSync 8GB VRAM (v1.5) / 18GB (v1.6); MuseTalk
runs on a 256x256 face region with documented identity-detail and jitter
issues. Usable only on readable closeups, and only after action/continuity
passes. Neither makes hidden/wide mouths readable or supplies missing
expression.

Sources:
- LatentSync: https://github.com/bytedance/latentsync
- MuseTalk: https://github.com/TMElyralab/MuseTalk/blob/main/README.md

### R11 - QA assistance
Forced alignment (WhisperX-class) can catch word-time/coverage issues, not
emotion, timbre or phoneme-to-mouth truth; dictionary gaps, overlapping
speech and diarization limits stay visible. Model licenses differ from the
repository license; one language-specific alignment model has an
unresolved licensing discussion at
https://github.com/m-bain/whisperX/issues/962 .
Restoration/upscaling cannot make absent actions real and may invent
detail. No quality score or sharper frame substitutes for acceptance.

Source: https://github.com/m-bain/whisperX

## Original H3 control path - correction

The supplied H3 graph uses reference-to-video with audio/video VAEs, timed
visual guides and a fixed-audio zero-noise mask - a materially different
control route from independent silent one-image I2V clips plus mouth
patches. This is a credible control difference, not a tested quality winner
and not a reason to rerun paid generation. The supplied default runtime
targets Blackwell-class GPUs (RTX PRO 6000 / B200) with ComfyUI v0.36.0;
an earlier H100 forecast does not apply to the unchanged setup.
Model-weight license has territorial and hosted-use terms; source-code
reuse, deployment and storage rights remain unresolved. The H3 model entry
point in this codebase refuses execution pending written clearance.

Sources:
- https://docs.comfy.org/tutorials/video/minimax/minimax-h3-native
- https://docs.comfy.org/built-in-nodes/MiniMaxH3ReferenceToVideo
- https://docs.comfy.org/built-in-nodes/MiniMaxH3AddGuide
- Model license: https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/LICENSE

## Upgrade paths, gated

| Path | Gate |
|---|---|
| Self-hosted lip-sync route (LatentSync/MuseTalk class) | GPU with 8-18GB VRAM per the cards above; readable-closeup shots only; after action/continuity acceptance |
| Audio-led dialogue performers (R9) | Multi-GPU budget; runtime verification; acting-quality review still human |
| Structure-controlled action generation (R8) | Rights-cleared model, verified environment, separately authorized bounded test; VACE needs the F24 compatibility fix tested first |
| H3 reference-to-video | Written model-weight license clearance, Blackwell-class GPU or ported runtime, budget approval; currently blocked in code |
| Paid provider routes | Provider history/billing reconciliation first (F25), exact spend cap and authority, no repeated ambiguous POST |

## What would count as progress

- A future pilot measures accepted seconds and all rejected takes,
  manual-edit time, elapsed time, transcript/speaker errors, and
  wardrobe/prop/identity/eyeline/action violations, plus full playback and
  listening.
- A partial action or a moving mouth does not pass. A short accepted test
  does not prove a ten-episode season. Unknown review fields stay unknown.
