# H3 whole-line control comparison and minimal validation plan

Date: 2026-10-25
Scope: offline design and QA only. No render, GPU call, paid API call or new spend was attempted.

## Actual failed-output QA

Input: `/tmp/Harry_Draconia_E01_original_H3_Modal_trimmed_13.12s.mp4`

- SHA-256: `04f75facad67db5dda846f2f1b7475ec65f567955f47a6e3e559260d25cde69f`
- Decoded video: 24 fps, 315 frames, 13.125 seconds. The H3 generation grid was padded to 328 frames, but 328 is not the decoded frame count.
- Dense track samples: 25 Hz observations mapped to nearest decoded frames, with source frame and timing error recorded per observation.
- Current identity screening threshold: 0.40. Detector score, SFace similarity/margin and raw MediaPipe mouth aperture are stored as separate fields. `identity_verified` remains false because a screen is not identity proof.

Whole-line result: all six lines fail.

| Line | Speaker | Visible mouth samples | Aperture/envelope correlation | Offset | Main failures |
| --- | --- | ---: | ---: | ---: | --- |
| L1 | Draconia | 40/42 | 0.1157 | -0.080 s | uncalibrated motion screen below 0.70 |
| L2 | Draconia | 62/64 | 0.3591 | -0.040 s | uncalibrated motion screen below 0.70 |
| L3 | Harry | 16/63 | n/a | n/a | 25.4 percent mouth coverage, too few samples |
| L4 | Draconia | 50/52 | 0.3335 | -0.040 s | uncalibrated motion screen below 0.70 |
| L5 | Harry | 55/57 | 0.3987 | -0.040 s | uncalibrated motion screen below 0.70 |
| L6 | Draconia | 29/48 | 0.2135 | -0.040 s | 60.4 percent mouth coverage and uncalibrated motion screen below 0.70 |

This rejects the current output. It does not prove phoneme-level lip sync, and the raw aperture/envelope correlation is not a calibrated lip-sync score.

## Known-good calibration result

A public-domain FEMA clip was used as a known-good natural-speech calibration sample:

- Commons page: `https://commons.wikimedia.org/wiki/File:Brock_Baton_Rouge_cut_1.webm`
- Used derivative: `https://upload.wikimedia.org/wikipedia/commons/transcoded/f/fd/Brock_Baton_Rouge_cut_1.webm/Brock_Baton_Rouge_cut_1.webm.480p.vp9.webm`
- Local file SHA-256: `a3e6b3bfe695aca6a7417490c7ea734fb73668d8f9a419389e94d8e949ad9cba`
- Result: 223/242 visible mouth samples, 92.15 percent coverage, aperture/envelope correlation 0.1344 at offset -0.120 s.

The known-good clip passes mouth coverage but fails the provisional 0.70 correlation screen. One natural-speech sample is enough to prove the current correlation threshold is not calibrated, not enough to establish a universal passing threshold. The QA therefore stays fail-closed and cannot certify phoneme lip sync. More labeled known-good and known-bad real clips are required before replacing this engineering screen with a calibrated score.

## Source-grounded H3 control comparison

Local owning sources inspected:

- `/tmp/comfy-v0.36-src/comfy_extras/nodes_minimax_h3.py`
- `/tmp/comfy-v0.36-src/comfy/ldm/minimax/model.py`
- `/tmp/comfy-v0.36-src/comfy/model_base.py`
- `/tmp/avfix-roundtrip/DramaSaga-main/vendor/h3-film-reference/research/h3/runpod/comfy_r2v.py`

Findings:

1. `MiniMaxH3AddGuide` has no strength parameter. A guide image is an anchor at one frame, not a controller for the rest of a line.
2. Valid single-image guide clips land on the 17k+5 frame grid. The current 13.12 second plan pads from 315 requested frames to 328 generation frames.
3. In the model, reference and keyframe condition latents are re-injected every sampling step and are not denoised. This explains why image pins can strongly preserve framing or identity near their anchors.
4. Optional guide audio becomes `cond_audio` rows at the same target timeline anchor as the guide. This is the source-supported route that can carry speech information between isolated image anchors.
5. The current graph already preserves the supplied full soundtrack through the audio VAE, a zero noise mask and AV latent concatenation. Vendor notes call this `audio=inpaint` and describe it as the best of three tested lip/beat sync modes.
6. Denser image-only guides can improve identity/framing at more anchor frames, but they do not supply mouth dynamics and can freeze a mouth pose at the anchor.
7. Per-line clips and joins are possible, but they add cut boundaries, visual discontinuity risk and more GPU work. They are not the minimal original-H3 correction.
8. H3 reference videos with soundtracks are supported, but no verified Harry/Draconia talking reference videos exist. Creating those would require more generation and is not minimal.
9. H3 Fun ControlNet or mouth inpainting exists in the broader source, but it requires an additional model patch outside the verified four-asset whitelist. It is not a minimal approved route.
10. A separate talking-head generator would violate the user's original-H3 route unless explicitly approved.

## Minimal defensible validation plan

The least speculative next original-H3 test is one E01 corrective render using per-line image+audio guides:

- Six lines, one active-speaker guide at each line start and one at each midpoint: 12 guide anchors.
- Each guide binds the active speaker's existing reference image plus a WAV segment cut from the accepted full soundtrack.
- Start guides carry the full remaining line audio. Midpoint guides carry the second half of the line.
- The full `dialogue.wav` remains the exact output soundtrack through the fixed audio VAE and zero-noise mask.
- All nine existing reference images remain in the reference set. The guide images use the active speaker's speaking profile at every line anchor.
- Size, frame rate and weights stay fixed to the audited 576x1024, 24 fps, four-asset int8/NVFP4/fp16/fp32 H3 manifest.

Compiled plan: `/tmp/harry-original-h3-plan-v4.json`

- Workflow SHA-256: `aeb81529d3b6e35cf8c454646eef56fce72c5c1ee26b7224a8e03c2a28b033ea`
- Plan file SHA-256: `89f2a7fb5913dc745d0bba2f2e7e1e306ead12657ea72f89159470cfd4387387`
- Staged input manifest SHA-256: `8afab1aecea76f6253a0ca8cb1dc0ceffad33de97e0fd8499ef48380971f0276`
- Status: planned and compile-tested only, not runtime validated.

If a future render is separately approved, it must remain a single-job test with provider-side hard usage/spend limits verified first. The output remains rejected unless dense real-video QA passes speaker identity screening, whole-line visible mouth coverage, occlusion checks and a motion metric whose calibration limits are explicitly reported. Any ambiguity, duplicate identity match, missing face or occluded mouth fails the line.

## Current blocker

There is no authorization or remaining credit for another render. The compiled image+audio guide plan is source-supported but not runtime validated. The real-video extractor works, but the raw mouth-aperture/audio-envelope correlation is not calibrated enough to claim precise lip sync or a passing score. The failed E01 output stays rejected.
