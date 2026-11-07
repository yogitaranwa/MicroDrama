# Prepared local model execution

Current acceptance state: `out/acceptance/current_inventory.json`. The new
models are not accepted as working end-to-end yet. Local tests prove the
interfaces and guards, not generated output.

## Inputs, not arbitrary commands

`forge.integrations.plan_bridge.prepare_audio_driven_jobs` prepares selected
existing render jobs using explicit per-person WAV mappings. Its manifests
pin each reference and audio file hash. The image's left/right person mapping
must be checked by the operator, not inferred from the filename.

`forge.integrations.execute.execute_audio_job` rechecks current project gates,
still-lock membership, input hashes, weights folders and CUDA, then rebuilds
its own argv. It does not trust a manifest's argv. InfiniteTalk additionally
needs an explicit `infinitetalk_ckpt` file. Its seven base checkpoint shards
and separate audio weights are distinct inputs. MultiTalk uses a merged
checkpoint index that includes `multitalk.safetensors` alongside base shards.

`forge.integrations.visual_jobs` adds `prepare_vace_job`,
`prepare_pulid_job` and `execute_visual_job`. These pin conditioning inputs,
refuse already-existing outputs, require current still locks for image
references, and rebuild safe argv only after validation. VACE takes an
explicit checkpoint folder, frame count, steps and seed. PuLID uses the actual
vendored SDXL-Lightning four-step pipeline. It is not a FLUX adapter. Its
constructor downloads uncached model files, so host/download/license review
must precede execution. InsightFace antelopev2 has separate non-commercial
conditions, independent of the repository's Apache license.

`forge.integrations.weight_layout.check_weight_layout` is a read-only
presence inventory from pinned loader contracts. Run it before provisioning
or downloading large weights. A good layout is not authenticity or a model
pass. Actual model load, tensor compatibility and inference remain required.

All local executors require `host_reviewed=True`. That boolean is an operator
check, not user authority, license consent or spending approval. No executor
rents a GPU or grants a budget. Existing episode/still/proof gates still apply.
An output file from an exit-zero process is only `quality_status=unreviewed`.
Inspect pixels and watch/listen before accepting it. Episode delivery must
still use the existing review/signoff path.

## Isolated Python

The root application and vendored model projects have different dependency
requirements. Keep model environments separate; pass the model environment's
Python path to executors. A single global install is not supported by the
available evidence. Do not silently downgrade an existing application or
notebook environment.

The T4 attention and fp16 overrides remain explicit experiments. Their GPU
numerical check passed, but that does not establish quality or speed for any
new full model. Ordinary FlashAttention2 is not the default T4 path.
