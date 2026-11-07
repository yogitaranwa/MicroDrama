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
