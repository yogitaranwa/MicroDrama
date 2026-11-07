# Free GPU experiments

These scripts are tests, not approved episode generation. Do not run two
unused GPU sessions in parallel. No script provisions paid compute.

1. `wan21_visual_seed_test.py`: two visual-only Wan2.1 1.3B samples, same
   prompt/settings except seed. It has no audio and no image conditioning.
   Its result cannot diagnose voice pitch or prove identity-reference control.
2. `model_setup_preflight.py`: reads CUDA, installed modules, storage and
   official model-file metadata. It downloads no model weights and installs
   no packages. Use this before selecting any large download.

The audio-driven upstream repos expect a Python 3.10 / torch 2.4.1 stack.
The live free host was Python 3.13 / torch 2.11, so dependencies must be
isolated instead of downgrading an existing notebook's environment blindly.
T4 x2 is two separate 15-16GB devices, not one 32GB allocation.

MultiTalk/InfiniteTalk model.py directly calls FlashAttention. FlashAttention2
is not an ordinary T4-supported path. `forge.integrations.t4_attention` is
an opt-in, source-preserving chunked attention experiment, numerically tested
on CPU only. A separate Turing fp16 override is provided, not enabled by
default. GPU memory/performance and model-output quality remain unverified.
Do not call successful imports or subprocess exit zero a successful video.

Select model files deliberately. Full official repositories contain multiple
alternative quantizations and can exceed free working storage. Use a single
model variant, allow for cache/install duplication, record hashes and retain
licenses. No blind snapshot download of every variant.

## Actual evidence update, November6

The portable attention comparison has now run on an actual Tesla T4, with
maximum absolute difference0.0. This supersedes the earlier CPU-only note
above. It is still a numerical test, not a model-quality result.

`vace_official_runtime_trial.py` and its notebook use a separate Python3.10 /
PyTorch2.5.1 environment in temporary storage. They attempt the official CLI
and the actual pinned VACE library with selected official1.3B weights, then
17 frames at8 steps using the upstream example image. The fp16/attention
fallback is experimental. The trial was launched privately, but success was
not yet established when this note was written. Never use the trial as an
approved episode asset or report a model pass before recovering its result.

## Pending run diagnosis,02:57 IST

The first VACE runtime successfully built its isolated environment and
installed Wan. Its CLI import failed at eager pose-annotator imports:
`matplotlib` was absent. Source inspection shows `dwpose.wholebody` also
imports `onnxruntime` unconditionally. A retry preparation adds those two
packages, but it is not yet launched and is not proven to cover every CLI
import. It does not download unrelated annotator models.

The actual core-library inference subprocess continued after the help
failure. At02:56 it was still Running, with no visible model-result evidence.
The first script captures subprocess output until exit, obscuring progress.
`streaming_process.py` now writes logs as bytes arrive, emits them to the
notebook console, records per-step running/terminal state, and terminates the
process group on timeout. Real tiny subprocess tests verify streaming,
nonzero exit handling and timeout cleanup. This does not change the in-flight
run or prove model inference. Recover its result before retrying.

## Mixed-dtype audit correction,03:04 IST

Wan's real rotary function returns float32 queries/keys even with fp16
values. The first portable numerical check used uniform fp16 tensors and did
not cover that path. The fallback now follows upstream's final value-dtype
conversion before SDPA. A direct CPU mixed-dtype test passes; a matching GPU
check is added to `portable_attention_check.py` and to the prepared streamed
retry. Neither new check has run on the remote GPU yet. The original in-flight
VACE trial still contains the previous fallback. Do not infer a model pass
from the original numerical difference0.0.
