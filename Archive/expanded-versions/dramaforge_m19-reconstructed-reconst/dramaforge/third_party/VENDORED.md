# Vendored open-source repositories (m19)

Full source copies integrated for the MagicDrama/Malfoid pipeline. Code only -
no model weights are vendored; weights download on the GPU host at run time.
Original LICENSE files are preserved inside each directory. Personal/local
R&D use; each upstream license still applies to its own code and weights.

| Directory | Upstream | Commit | Code license | Weights (not vendored) | Capability |
|---|---|---|---|---|---|
| multitalk/ | https://github.com/MeiGen-AI/MultiTalk | c1ad84009b99ed36c97ab18e4517ca5f98692438 | Apache-2.0 (LICENSE.txt) | MeiGen-MultiTalk + Wan2.1-I2V-14B-480P (Apache-2.0 cards) + wav2vec2 | Multi-person audio-driven talking video (Label RoPE binds each audio stream to a person) |
| infinitetalk/ | https://github.com/MeiGen-AI/InfiniteTalk | 50aa0a94184315407a991ae804d9b58d6d311ba8 | Apache-2.0 (LICENSE.txt) | MeiGen-InfiniteTalk + Wan2.1 base (Apache-2.0 cards) | Audio-driven dubbing/lip-sync video, long-form streaming mode |
| vace/ | https://github.com/ali-vilab/VACE | 48eb44f1c4be87cc65a98bff985a26976841e9f3 | Apache-2.0 (LICENSE.txt) | Wan2.1-VACE-1.3B/14B (Apache-2.0); VACE-LTX-Video-0.9 is RAIL-M - avoid that variant | Reference-guided video generation/editing (depth/pose/flow controls, ref images) |
| pulid/ | https://github.com/ToTheBeginning/PuLID | 1aa2fc7df4bf51080df39f355f9abdc1cbfefbaa | Apache-2.0 (LICENSE) | FLUX.1-dev base (non-commercial license) + PuLID weights - stills only, flag before any use | Identity-preserved portrait stills |

NOT vendored: h94/IP-Adapter-FaceID (model card marks InsightFace face models
research-only / non-commercial; incompatible with hosted API route anyway).

## Import smoke results (2026-11-06, torch 2.14.1 CPU, test_vendored_import_smoke_real_torch)
- MultiTalk: BLOCKED on CPU - wan/__init__ -> xfuser -> fail-closed "No Accelerators available" (GPU-only). Task names verified statically ('multitalk-14B' etc.).
- InfiniteTalk: BLOCKED on CPU - same xfuser GPU gate. Task names verified statically ('infinitetalk-14B', 'vace-1.3B/14B').
- VACE: needs upstream Wan2.1 package (pip install wan@git+https://github.com/Wan-Video/Wan2.1) + weights in models/ (only .gitkeep present).
- PuLID: blocked at insightface (its face models are non-commercial - see license caveat).
- Conclusion: all four repos are GPU-host work. Kaggle/free-GPU validation is the next step for real inference; CLI contracts and config task names are verified here.
