# MicroDrama still-first pipeline v3

Purpose: rebuild the Harry + Draconia Yule Ball E01 around the user's corrected process: script first, voice second, still continuity third, motion last.

Current status: planning and validation package. This code does not submit paid jobs unless `ALLOW_PAID_GENERATION=1` is set and a credit budget is passed explicitly.

## What changed from the rejected first cut

1. Script is no longer made of one-to-five word fragments. Every spoken beat is a complete, natural sentence with a reason to exist.
2. Stills come before motion. Each shot has named key beats for face, wardrobe, prop, hand position, expression and camera framing.
3. Video jobs consume selected stills and the locked audio. They do not invent the scene from a text prompt alone.
4. Every generated asset gets a manifest, hash, job id, credit charge, QA status and Drive milestone.
5. Stitching checks happen before delivery: shot-boundary continuity, prop continuity, speaker visibility, audio timing and black-frame detection.

## Hard rules

- Existing API balance only. No top-up, subscription, card charge or unrelated spend.
- Preserve accepted voice identities:
  - Draconia / Amelia: `ZF6FPAbjXT4488VcRRnw`
  - Harry / Peter Harwood: `4dZr8J4CBeokyRkTRpoN`
- Cinematic photorealistic only.
- Do not call output final until actual frames have been inspected for action, prop, expression and continuity, not only transcript alignment.
- Do not batch ten episodes. E01 must pass first.


## Delivery gate (2026-10-25 FAILURE.TXT revision)

Owner-confirmed rules after the rejected v3 delivery:

1. A shot missing its scripted action is rejected. No still, crop, retime or
   slow-motion patch is substituted by the gate.
2. When automatic checks cannot establish action quality or emotional audio,
   the pipeline pauses for named human review instead of assembling.
3. Review receipts are bound to the reviewed bytes by sha256; changed bytes
   invalidate the receipt.

What is mechanical (measured, `microdrama/detectors.py`): freeze windows
(`freezedetect`), silence windows (`silencedetect`), integrated LUFS and
mean/max levels, music-bed level in dialogue-free gaps versus the full-file
mean, black frames. These establish signal facts only.

What is never mechanical: that a scripted action happened, that a
performance is emotional, that lip sync is right. Those come only from a
named human review receipt (`microdrama/reviewgate.py`); the gate enforces
the presence and currency of receipts, not their truth.

Validated against the rejected v3 file: the detectors independently
reproduce FAILURE.TXT's measurements - the 9.0s freeze at 13.58-22.58s,
the 1.7s opening silence, dialogue-free gaps 17-35 dB below the full-file
mean, -17.69 LUFS integrated.

Commands:

```bash
# Full mechanical QA on any video; exits 1 when a defect is measured
python3 run_pipeline.py qa-video --video EP.mp4 --out qa.json     [--dialogue-windows windows.json]

# Per-beat gate: assets keyed by beat id plus human receipts
python3 run_pipeline.py gate-check     --requirements config/E01_v43_gate_requirements.json     --assets assets.json --receipts-dir receipts/

# Scaffold a hash-bound receipt for a reviewer to fill after watching
python3 run_pipeline.py review-receipt --asset shot.mp4 --beat 3     --out receipts/shot03.receipt.json
```

Test suite covers the detectors on synthetic frozen/moving/silent clips and
the gate's approve/reject/pause/stale-receipt behavior:

```bash
python3 -m unittest discover -s tests -v
```

## Commands

Validate the script:

```bash
python3 run_pipeline.py validate-script --script docs/E01_script_v3.md
```

Create the 1000-candidate still plan without spending credits:

```bash
python3 run_pipeline.py plan-stills --shot-plan config/E01_shot_plan_v3.json --target 252 --out artifacts/still_candidates_252.json
```

Estimate cost from the current docs-based rate table:

```bash
python3 run_pipeline.py estimate-still-cost --target 252 --model nano-banana-2.1
```

Build a review sheet after stills exist locally:

```bash
python3 run_pipeline.py make-contact-sheet --input-dir artifacts/stills --out artifacts/still-contact.jpg
```

Stitch approved clips and run basic assembly checks:

```bash
python3 run_pipeline.py stitch --timeline artifacts/timeline_v3.json --out artifacts/E01_v3.mp4
```

## Right-sized still interpretation

The user first asked for "1000 still frames," then clarified: "1000 is just a number. You decide that number how many are required for consistency."

This pipeline uses coverage, not a vanity count:

- 12 shots x 7 locked key beats = 84 required still states.
- 3 candidates per required state = 252 candidate stills.
- Selection keeps 84 canonical stills, plus alternates.
- Stage 1 is a priced small batch to verify model, resolution and charge behavior.
- Stage 2 fills the 252-candidate pool only after script, voices, reference images and model choice are stable.

This preserves the still-first instruction without spending high-end image credits on a broken story.

## Drive milestone layout

Recommended Drive structure under the existing E01 folder:

```text
E01_v3/
  00_status/
  01_script/
  02_voice/
  03_reference_bank/
  04_still_candidates/
  05_selected_stills/
  06_video_jobs/
  07_assembly/
  08_qa/
  09_delivery/
```

Each milestone gets a `MANIFEST.json`, a human-readable report and a contact sheet where visual output exists.
