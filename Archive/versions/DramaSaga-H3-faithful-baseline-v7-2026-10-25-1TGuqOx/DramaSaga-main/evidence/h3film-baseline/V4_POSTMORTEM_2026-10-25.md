# H3 V4 postmortem and faithful H3Film baseline

Date: 2026-10-25, Asia/Kolkata. Scope: offline source and graph audit only. No paid render, GPU call or batch was run for this postmortem.

## Direct answer

We used MiniMax H3 and the preserved H3Film R2V base graph, but the rejected V4 test was not the original H3Film workflow as-is. V4 added a custom timed-guide overlay that the preserved production runner does not emit for this standalone dialogue clip. That is the verified reason it was wrong to describe V4 as full H3Film parity.

The exact visual cause is not proven. The source-supported leading hypothesis is that repeated one-frame still anchors, especially Draconia's same speaking-profile image at 8 of 12 anchors, acted as persistent fixed visual conditioning and may have suppressed mouth motion. This is compatible with the ComfyUI source and with the observed output, but it is not isolated causality. Harry also had repeated still anchors and his mouth moved, so the still-anchor count alone does not prove the cause.

## Source authority and provenance

The source now restored under `vendor/h3-film-reference` is byte-exact to the user-supplied source-review ZIP. Original comments and attribution are preserved. Fidelity is to the supplied archive, not to a verified upstream HEAD.

Recovered origin:

- User supplied `h3-film-main.zip` on 2026-10-20 at 1:56:28 AM IST and wrote that project-owner shared the GitHub repo:
  - [private-project-source]
  - 2,373,719,592 bytes
  - message ID `[private-record-reference]`
- User clarified at 2:30:03 AM IST that this is project-owner's approach and project-owner forked the repo:
  - message ID `[private-record-reference]`
- Curated source-review ZIP:
  - [private-project-source]
  - 2,875,652 bytes
  - SHA256 `70b15f46f545744e96d235631f46f0450f74800a58806908fa64d75775794ebc`
  - 879 files, no `.git` directory in the curated copy

Source-identified upstream and version labels:

- Original README identifies `[private-project-source] as the private repo to build from.
- Original `docs/history.md` says the repo was cut from the lab at `5c20bcc`.
- Original `docs/lab/notes.md` labels the clean repo status `5755047`.
- Original README says changes from `df63897` and `5755047` were deliberately left out of some approved-film behavior and remain in repo history.
- These are internal source labels, not proof of archive HEAD. Upstream HEAD and root source license remain unverified.
- Signed-out GitHub browser check: project-owner's public profile exists, the private repo URL returns 404 signed out, and public repository search has no `h3` match. This is consistent with a private repo but does not verify it.
- Treat the restored files as private reference material, not as public redistribution.

Restored source hashes:

- `vendor/h3-film-reference/research/h3/runpod/comfy_r2v.py`
  - SHA256 `3587ca8a94d95f0e7c9a06045518d93130b77a202e1bacd9c784ef244bfd537e`
- `vendor/h3-film-reference/research/h3/runpod/r2v_v1.json`
  - SHA256 `1d927b51d05405fa0d2683593822882c7cf8a6d5f9742817863338e7efe069a3`
- `vendor/h3-film-reference/agent/h3film/render-all.mjs`
  - SHA256 `2a55fe1b77192530a90683b03b21aa013946b17e99a90ae7c50367d1bf1c4d67`
- `vendor/h3-film-reference/research/h3/modal_h3.py`
  - original wrapper SHA256 `842ecc59ce09f6fedf2aebf67f0876b0411c15f63942761084fc2f5aa71792c1`
- Corrective wrapper preserved separately as `magicdrama/audiofirst/modal_h3_corrective.py`
  - SHA256 `d8f33de8b267980b1b680ab4ee51bd4ebe81c5ba29cfd3cd3a793fdaf5a35486`

ComfyUI source used for node/model semantics:

- Local tag `v0.36.0`, commit `ee71d5c4993f29086b27fde1629a945ae48425bf`
- `comfy_extras/nodes_minimax_h3.py` SHA256 `62ec72d4f3b879640dbd41b959a6c1112a82b77478509323094f49dae17fffdb`
- `comfy/ldm/minimax/model.py` SHA256 `0d5edcf32b4b98d704eaa51de60ed71f507d0c7d9845947f566647dc76fb8dfe`
- `comfy/model_base.py` SHA256 `6280712f8315f00f19a1ada53e48bf243c818b017fa751b3412092fa0f381e68`
- Public source roots checked by fetch:
  - `https://raw.githubusercontent.com/comfyanonymous/ComfyUI/v0.36.0/comfy_extras/nodes_minimax_h3.py`
  - `https://raw.githubusercontent.com/comfyanonymous/ComfyUI/v0.36.0/comfy/ldm/minimax/model.py`
  - `https://raw.githubusercontent.com/comfyanonymous/ComfyUI/v0.36.0/comfy/model_base.py`
  - `https://docs.comfy.org/tutorials/video/minimax/minimax-h3`

## What the preserved H3Film runner does in the local reference

The preserved reference runner, not a rewritten copy, was executed offline with only its final Modal transport captured. This proves the emitted graph came from the preserved `comfy_r2v.py` code path.

For the 13.12-second Harry/Draconia clip with 9 reference images and `--audio=inpaint`, the preserved runner emits:

- 35 nodes total
- 9 `LoadImage` nodes attached to `MiniMaxH3ReferenceToVideo`
- 1 `LoadAudio` node
- full soundtrack trimmed or padded to exactly 13.12 seconds before upload
- the same soundtrack connected as `ref_audios.ref_audio_0` on `MiniMaxH3ReferenceToVideo`
- the same soundtrack also encoded and kept as the exact target audio through `VAEEncodeAudio -> SetLatentNoiseMask(0) -> LTXVConcatAVLatent`
- 0 `MiniMaxH3AddGuide` nodes for this standalone clip
- `ref_image_size: match`
- 576x1024 through the runner's supported `--rows=576 --ratio=9:16`
- 25 steps, `res_multistep`, `simple`, denoise 1
- T8 block-cache settings unchanged

Preserved emitted artifacts:

- `evidence/h3film-baseline/harry-draconia-e01-h3film-baseline-v1.workflow.json`
- `evidence/h3film-baseline/harry-draconia-e01-h3film-baseline-v1.clip.json`
- `evidence/h3film-baseline/harry-draconia-e01-h3film-baseline-v1.prompt.txt`
- `evidence/h3film-baseline/harry-draconia-e01-h3film-baseline-v1.files-manifest.json`
- `evidence/h3film-baseline/harry-draconia-e01-h3film-baseline-v1.command.json`
- `evidence/h3film-baseline/harry-draconia-e01-h3film-baseline-v1.summary.json`

The emitted workflow SHA256 for the captured dry run is `c039fd3a846cc94f07f82c19cf9b074aec9582e625ba82e21129320a0b6eb0fd`. It includes run-specific uploaded filenames, so use the preserved graph and file manifest together rather than treating that hash as a stable semantic graph ID.

## What V4 did differently

V4 emitted 71 nodes. Its differences from the actual preserved-runner baseline are:

| Area | Original H3Film baseline | Rejected V4 |
| --- | --- | --- |
| Timed guides | 0 for this standalone clip | 12 `MiniMaxH3AddGuide` nodes |
| Guide images | none emitted by baseline | 12 single-frame pins, reusing one Draconia still 8 times and one Harry still 4 times |
| Guide audio | none | 12 half-line WAVs attached to the guides |
| Full soundtrack reference | connected to `MiniMaxH3ReferenceToVideo` as `ref_audio_0` | missing |
| Exact target audio | present | present |
| Full audio preparation | trimmed/padded to exact 13.12s by preserved runner | submitted as 13.666s and the MP4 trimmed later |
| Reference image sizing | `match` | `max` |
| Prompt | normal content instruction | explicitly told the model to draw mouth motion from line guides |
| Graph size | 35 nodes | 71 nodes |
| LoadImage / LoadAudio | 9 / 1 | 21 / 13 |
| Sampler core | 25 steps, `res_multistep`, `simple`, denoise 1 | same |
| Seed for this comparison | fixed to V4 seed `419433329744414` for graph comparison | `419433329744414` |

The detailed machine-readable comparison is `evidence/h3film-baseline/v4-vs-h3film-baseline.graph-comparison.json`.

## Source-supported guide semantics

The ComfyUI H3 source establishes these facts:

- `MiniMaxH3AddGuide` anchors image, clip frames, audio, or clip-with-soundtrack at an arbitrary pixel frame.
- A single image is a one-frame guide. Multi-frame batches are treated as clips and cropped to valid `17k + 5` lengths.
- Guide audio starts at the same frame index and is cropped to the remaining target duration.
- The model places each guide image latent as fixed `cond` rows and each guide audio latent as fixed `cond_audio` rows at `cursor + FRAME_RESCALE * frame_idx`.
- During each model forward, current target rows and fixed condition rows are assembled separately. Condition rows are not the denoised target rows.

This means repeated identical stills can act as fixed visual conditioning at their timeline anchors on every model forward. The source does not quantify how far the influence spreads or prove that this alone froze Draconia's mouth.

## Output evidence recap

The V4 render was rejected after actual MP4/frame review:

- Draconia's mouth was visible but mostly frozen through L1, L2, L4 and L6 while the accepted speech audio changed.
- Harry's mouth visibly moved in L3's first half and L5.
- L3 still failed active-speaker visibility: Harry was visible in 33 of 63 sampled points, 52.4%, because action/camera framing hid him for much of the second half.
- Rendered audio waveform aligned to the accepted track: global envelope offset 0.0s, speech onset -0.02s, correlation 0.9765. This is waveform alignment, not lip-sync proof.
- Identity and wardrobe were consistent, and the cinematic look was closer to the user's visual reference.

## Modal wrapper deviations

The corrective Modal wrapper is deliberately separate from the restored original wrapper. It now lives at `magicdrama/audiofirst/modal_h3_corrective.py`; the vendor copy is byte-exact to the supplied source. The deliberate differences are recorded in `evidence/h3film-baseline/modal-wrapper-original-vs-corrective.diff`:

- one max container instead of 40
- 1800s timeout instead of 3600s
- RTX PRO 6000 first instead of the original ordering
- BF16 weight omitted from download/storage
- weight size and SHA256 verification added
- SageAttention disabled on all GPUs instead of only compute-capability 10
- original SageAttention build omitted

These are transport, safety and reliability controls, not graph-builder semantic changes. They have not been proven to affect quality, but they remain unvalidated runtime differences until a baseline render proves otherwise.

## Billing reconciliation

Latest Modal billing summary read at 13:18 IST:

- monthly metered: `$2.11084757`
- billed to card: `$0`
- credits adjustment: `-$2.07`
- network egress allowance: `-$0.04084757`
- prelaunch monthly metered: `$1.03077625`
- reconciled test delta: `$1.08007132`
- at-stop provisional delta was `$1.13007132`, so Modal reconciled the monthly summary down by `$0.05`
- app `ap-Kk2VGBp1FOB8C3H05D0II4` itemized cost in the current hourly report: `$1.01629881`
- estimated cycle credits remaining from `$30`: `$27.93`, based on `$2.07` total credits applied
- app state at 13:18 IST: stopped, 0 tasks

Billing snapshots are preserved as:

- `evidence/h3film-baseline/modal-billing-summary-2026-10-25-1318IST.json`
- `evidence/h3film-baseline/modal-billing-report-2026-10-25-1318IST.json`

## Code validation

New faithful baseline code:

- `magicdrama/audiofirst/h3film_baseline.py`
- `tests/test_h3film_baseline.py`

Validation result: 257 local tests passed. The tests pin the byte-exact user-supplied runner and graph hashes, build the original runner clip schema, compile through the actual original runner with only Modal transport captured, verify the 9-reference 35-node baseline shape, verify the absence of timed guides, verify the exact-audio chain, and check that the preserved runner file is unchanged by dry-run compilation.

After byte restoration, a fresh offline dry run through `3587ca8a94d95f0e7c9a06045518d93130b77a202e1bacd9c784ef244bfd537e` produced the same semantic graph after normalizing run-specific upload names and output suffix. This is recorded in `evidence/h3film-baseline/source-restore-validation-2026-10-25.json`.

This proves source and graph behavior only. It does not prove generated video quality.

## Precise remaining limitation

There is still no rendered output from the faithful H3Film baseline. Therefore there is no evidence yet that the original runner's baseline will produce acceptable mouth performance for this Harry/Draconia clip. The rejected V4 output proves only that our custom V4 overlay failed user-ready quality review.

## Best-supported next decision

The smallest defensible next test, if the user explicitly approves new spend, is one preserved-runner baseline render:

- byte-exact user-supplied `comfy_r2v.py` unmodified
- `--audio=inpaint`
- 9 existing reference images
- the accepted soundtrack trimmed/padded by the original runner to exactly 13.12s
- 576x1024, 25 steps, `res_multistep`, `simple`
- 0 timed `MiniMaxH3AddGuide` nodes
- `ref_image_size: match`
- same seed only if a controlled comparison is desired; otherwise the original runner's default random seed
- one job only, with hard timeout, stop-after-run and post-render actual AV review

That test would establish whether the original H3Film route itself can perform this clip. It would not by itself prove which V4 addition caused the freeze. Isolating causality would require later one-variable changes, each separately approved. Without fresh approval, the correct decision is no more H3 spend.
