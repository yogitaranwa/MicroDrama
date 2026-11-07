# Code-first checkpoint

2026-11-06, local personal research scope. Production is held by the user's latest
instruction. Existing caps do not override that instruction. All previous code
and flows remain; the new hold can stop execution without changing their budget.

## New enforcement

`forge.guard.generation_hold.require_generation_open` reads a persisted hold.
Ledger reservations and gated render execution consult it before further work.
FORGE_GATES=0 cannot bypass it. Missing hold files preserve legacy behavior;
unreadable or malformed existing files fail closed. No automatic resume helper
exists. A newer user instruction must be verified before an operator clears it.
The live production and project hold records are active. Read-only status checks,
code tests and batch preparation remain allowed.

## Additional FaceID route

Full upstream IP-Adapter code is pinned with its original license. The separate
FaceID SDXL route uses cached models only; it is not the hosted image route.
`prepare_faceid_batch` accepts up to24 named angle prompts for ONE identity, pins
the source image SHA256 and holds seed/settings fixed across prompts.
`execute_faceid_batch` checks the current reference lock, research scope, local
model layout, CUDA and output collisions. Its real driver detects exactly one
face and calls the upstream IPAdapterFaceIDXL constructor and generate method.
Every output remains unreviewed until actual pixel inspection. Embeddings are not
exported or stored. Multi-character placement still needs the existing
shot/reverse-shot pipeline, not an unsupported multi-ID claim for this driver.

## Acceptance still missing

- MultiTalk and InfiniteTalk: actual GPU load, audio-conditioned generation,
  identity binding and lip-sync review.
- PuLID: compatible isolated dependency stack, cached weights and actual inference.
- FaceID: compatible isolated dependency stack, cached weights and actual inference.
- VACE: one upstream stylized17-frame GPU output exists; no v9/dialogue/photoreal
  production acceptance, and the production executor has not run end-to-end.
- Seed advice: visual-only seed comparison exists. Voice pitch/beat causal claim
  has not been tested. Separate tests must keep every non-seed variable constant.
- Full E01: no animation/lip-sync output, connected proof or finished episode.

Code tests cannot fill these acceptance rows. The current hold forbids new
model generation too until the user clarifies code-validation test scope or
changes the sequence. No generation is started by this document or batch builder.

## Further wiring audit

The successful VACE trial's dual-T4 fix previously lived only in the notebook.
`prepare_vace_job(runtime_profile='t4_dual_staged')` now selects a general driver
from the gated executor. It checks cached weight layout, uses GPU1 for T5, offloads
diffusion before source VAE encoding, and writes hashed inference receipts. It
requires two Turing GPUs and VACE1.3B. This generalized route has not run yet.
The default upstream profile remains available and unchanged in behavior, but its
CPU-half T5 choice is not recommended for the tested two-T4 environment.

Actual model executors now call `runner.run_streamed`, preserving incremental
private logs and killing the process group on timeout. The older `runner.run`
remains for compatibility. Audio-driven execution now consults the real loader
weight-layout checker rather than only testing for a nonempty folder.

FaceID and PuLID actual upstream module imports and real inference signatures were
checked in separate validation environments. They succeed without constructing
models or downloading weights. Their requirements files document the imports
that were tested, not a promise of GPU compatibility or output quality.

A separate `forge.experiments.voice_seed_ab` now prepares and executes matched
ElevenLabs seed experiments through the actual guarded TTS client. Text, voice,
model and settings remain fixed; only2-4 explicit seeds vary. Preparation makes
no requests. Execution checks the user hold and total remaining character budget,
records pending requests before sending, and refuses partial reruns/overwrites.
No experiment was generated. Existing visual seed tests cannot establish a voice
pitch/beat cause. Raw output listening, speech transcription and timing/pitch
comparison are still required before drawing even a narrow result.
