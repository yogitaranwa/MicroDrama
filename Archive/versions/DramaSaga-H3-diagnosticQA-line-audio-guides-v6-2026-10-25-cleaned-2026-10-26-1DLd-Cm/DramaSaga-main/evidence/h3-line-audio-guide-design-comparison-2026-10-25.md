# H3 whole-line control comparison and bounded corrective plan

Date: 2026-10-25
Scope: offline design, read-only account verification and QA only. No render, GPU job, paid API call or new spend was attempted.

## Live Modal state

Read-only CLI and signed-in dashboard API checks at about 11:41 IST:

- Profile: `h3-corrective-test`.
- App `ap-2nAJ1Q4qwOF5bk8RtTyy1t`: stopped, 0 tasks, stopped at 2026-10-25 11:10:03 IST, no servers.
- All six listed `h3-render` apps are stopped.
- This month's CLI billing summary: metered `$1.07077625`, billed `$0`, credits adjustment `-$1.03`, network egress allowance `-$0.04077625`.
- Dashboard billing overview: usage `$0.99`, credits applied `$0.99`, charges `$0`. This subtotal excludes the separately itemized egress adjustment and reconciles with the CLI's `$1.07077625` metered total.
- Workspace plan: Starter, current-cycle credits `$30.00`, credits applied `$0.99`, credits remaining `$29.01`.
- Net spend limit: `$0`; effective net spend limit: `$0`; maximum allowed net spend limit: `$20`.
- Workspace cycle spend limit field: `$42.50`; max budget field: `$42.50`; next threshold invoice: `$10`; automatic card collection is configured.
- Interpretation: `$0` net spend blocks net card charges after credits/allowances, but it is not a zero-usage or zero-credit-consumption cap. It would not have prevented the observed `$1.03` credit metering. Do not describe it as a provider-enforced hard usage cap.
- The current API token warns that it expires in about 10 hours. A delayed future test requires a token refresh first.

## Actual failed-output QA after correction

Input: `/tmp/Harry_Draconia_E01_original_H3_Modal_trimmed_13.12s.mp4`

- SHA-256: `04f75facad67db5dda846f2f1b7475ec65f567955f47a6e3e559260d25cde69f`
- Decoded video: 24 fps, 315 frames, 13.125 seconds. The H3 generation grid was padded to 328 frames, but 328 is not the decoded frame count.
- Dense track samples: 25 Hz observations mapped to nearest decoded frames, with source frame and timing error recorded per observation.
- Current identity screening threshold: 0.40. Detector score, SFace similarity/margin and raw MediaPipe mouth aperture are separate fields. `identity_verified` remains false because a screen is not identity proof.

The raw aperture/envelope correlation is no longer an accept/reject gate. It is diagnostic only until calibrated against more labeled real clips. Fail-closed gates are active-speaker visibility, missing face, occlusion, duplicate/ambiguous identity and identity screen failure.

| Line | Speaker | Visible mouth samples | Visibility result | Diagnostic correlation |
| --- | --- | ---: | --- | ---: |
| L1 | Draconia | 40/42 | pass | 0.1157 |
| L2 | Draconia | 62/64 | pass | 0.3591 |
| L3 | Harry | 16/63 | fail | n/a |
| L4 | Draconia | 50/52 | pass | 0.3335 |
| L5 | Harry | 55/57 | pass | 0.3987 |
| L6 | Draconia | 29/48 | fail | 0.2135 |

Current verdict: the output remains rejected for L3 and L6 active-speaker mouth visibility/framing. The visibility pass on L1/L2/L4/L5 is not a lip-sync pass. Lip sync still requires real audiovisual review or a calibrated model.

## Known-good calibration result

Public-domain FEMA clip:

- Commons page: `https://commons.wikimedia.org/wiki/File:Brock_Baton_Rouge_cut_1.webm`
- Used derivative: `https://upload.wikimedia.org/wikipedia/commons/transcoded/f/fd/Brock_Baton_Rouge_cut_1.webm/Brock_Baton_Rouge_cut_1.webm.480p.vp9.webm`
- Local file SHA-256: `a3e6b3bfe695aca6a7417490c7ea734fb73668d8f9a419389e94d8e949ad9cba`
- Result: 223/242 visible mouth samples, 92.15 percent coverage, so the visibility screen passes.
- Raw aperture/envelope correlation: 0.1344 at -0.120 s. This proved that the former 0.70 hard rejection was a false rejection and invalid as an accept/reject threshold.

One known-good clip is enough to invalidate the old threshold, not enough to pick a new one. The bounded correction is to leave the value diagnostic and require real audiovisual lip-sync review, not to keep expanding QA indefinitely.

## Source-grounded H3 guide-audio semantics

Owning sources inspected:

- `/tmp/comfy-v0.36-src/comfy_extras/nodes_minimax_h3.py`
- `/tmp/comfy-v0.36-src/comfy/ldm/minimax/model.py`
- `/tmp/comfy-v0.36-src/comfy/model_base.py`

Relevant behavior:

1. `MiniMaxH3AddGuide` has no strength parameter.
2. Its audio input is documented as a soundtrack anchored at the same frame index and cropped to the video's remaining duration.
3. The node encodes the supplied audio, computes `max_rt = floor(target_audio_length - FRAME_RESCALE * resolved_frame_index)`, and crops only past the remaining video duration. It does not know dialogue line boundaries.
4. The model places each keyframe's audio latent as `cond_audio` rows at `cursor + FRAME_RESCALE * resolved_frame_index`.
5. The existing full soundtrack still enters through the exact audio VAE, zero-noise mask and AV latent concatenation.
6. Denser image-only guides may improve identity/framing at anchors but do not provide mouth dynamics and can freeze a mouth pose.
7. Per-line clips/joins, talking reference videos, H3 Fun ControlNet or a separate talking-head route are larger changes or outside the verified four-asset/original-H3 route.

## Bounded V4 corrective plan

The least speculative next original-H3 test is one E01 render using 12 active-speaker image+audio guides: one at each line start and one at each line midpoint.

The guide audio is now split into non-overlapping half-lines:

- Start guide: line start to midpoint.
- Midpoint guide: midpoint to line end.
- Each spoken line is covered once. No full-line WAV is repeated at both anchors.
- The midpoint WAV ends at the nominal line end. The owning node will crop audio only if it exceeds the remaining video duration.

Quantized timing tolerance:

- `frame_idx` is an integer at 24 fps, so requested line boundaries shift by up to 13.333 ms in this plan.
- The audio VAE timeline is about 40 Hz, about 25 ms per latent step.
- Therefore the line-half cuts are boundary-consistent at WAV duration level, but the actual conditioning anchors and tail are approximate. Do not claim sample-exact line-end synchronization solely from WAV duration.
- The largest start-anchor error is 13.333 ms; midpoint errors are within 6.667 ms; the final nominal line end is 13.12 s inside a 13.6667 s padded generation window.

Compiled plan: `/tmp/harry-original-h3-plan-v4.json`

- Workflow SHA-256: `aeb81529d3b6e35cf8c454646eef56fce72c5c1ee26b7224a8e03c2a28b033ea`
- Plan file SHA-256: `6af92a9ff4c796653ff60fbb4c9b9c8f9edae4900a7e5a315d0f89e0f0316a22`
- Staged input manifest SHA-256: `c03f51b2de2783de0c2069a6c8801600f10c8d0f05c6623ca4ed8aca56990750`
- Status: planned and compile-tested only, not runtime validated.

If separately approved later, the bounded test is one job only: verify the `$0` effective net card limit and `$29.01` credit state immediately before launch, verify staged input hashes, launch the V4 workflow, stop the app, reconcile billing, then reject unless L1-L6 pass active-speaker visibility/identity screens and a real audiovisual review accepts mouth timing. There is no perfection promise and no provider-enforced zero-usage cap.
