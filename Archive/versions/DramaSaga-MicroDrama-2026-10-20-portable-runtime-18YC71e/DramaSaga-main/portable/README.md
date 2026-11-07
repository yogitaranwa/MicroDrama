# Portable MicroDrama source

Python 3.10+ is required. This folder provides setup and explicit local runtime commands, not a promise of a finished self-running film model. No keys, accounts, paid rentals or model weights are in the ZIP. Run from the repository root. Installs access only PyPI, the official PyTorch index, publisher Hugging Face repositories and official MediaPipe storage. No remote shell scripts are executed.

## Windows laptop (PowerShell)

Install Python and FFmpeg/ffprobe from their official sites first. Then:

```powershell
powershell -File portable/setup.ps1
$env:MICRODRAMA_MODELS = "$PWD/models"
.venv/Scripts/python portable/models.py asr
.venv/Scripts/python portable/models.py vision
.venv/Scripts/python portable/models.py face
.venv/Scripts/python portable/smoke.py --out output/cpu-smoke
.venv/Scripts/python -m unittest discover -s tests -v
.venv/Scripts/python audiofirst.py --help
```

`setup.ps1` is CPU-only by default. Do not disable your execution policy globally for this project. For CUDA, use the official https://pytorch.org/get-started/locally/ selector in a fresh environment, then install `requirements/local.txt`. CUDA wheel compatibility depends on your driver and GPU. These scripts were tested on Linux CPU; Windows and GPU execution are not tested here.

## Linux CPU

```sh
bash portable/setup.sh
export MICRODRAMA_MODELS="$PWD/models"
.venv/bin/python portable/models.py asr
.venv/bin/python portable/models.py vision
.venv/bin/python portable/models.py face
.venv/bin/python portable/smoke.py --out output/cpu-smoke
.venv/bin/python -m unittest discover -s tests -v
```

FFmpeg/ffprobe must already be on PATH. Linux distributions can install FFmpeg through their official package manager. Setup does not run sudo. CPU-only model smoke tests need roughly 2 GB RAM; larger models/H3 need substantially more. Run each model sequentially.

## Kaggle / free Colab / already-provisioned RunPod

Use `portable/portable_runtime.ipynb` after uploading this source ZIP. Enable Internet manually for installs. Choose a free GPU only if offered; availability/quota is not guaranteed. GPU selection and paid pod creation are never automatic. Set `MICRODRAMA_ROOT` to the extracted `DramaSaga-main` folder, and `MICRODRAMA_MODELS` to a writable models directory. The notebook preserves an already installed CUDA PyTorch; it does not replace it with CPU wheels. A normal 16 GB free GPU is not assumed sufficient for H3. No notebook cell rents hardware, connects billing, accepts a gated model agreement or calls a paid model.

## Actual local commands

```sh
python audiofirst.py align-local --wav dialogue.wav --lines dialogue-lines.json --model-path models/asr --out output/alignment.json
python portable/run.py describe --image actor.png --out output/description.json
python portable/run.py track --video shot.mp4 --audio dialogue.wav --speaker actor-id --out output/mouth.json
python portable/h3.py compile --clip portable/h3_clip.example.json --out output/h3-compiled.json
```

`describe` runs the small publisher SmolVLM on real pixels, but is uncalibrated descriptive evidence, not an acceptance evaluator. Its descriptions can be wrong. `track` runs MediaPipe video landmarks at 25 Hz with strict .95 thresholds; occluded, missing or multiple faces reject. MediaPipe supplies no per-frame calibrated confidence or speaker identity. Returned geometry therefore has `confidence:null` and `identity_verified:false`: it cannot silently pass the acceptance gate. Face tracking and energy correlation cannot prove phoneme lip sync. Action/prop/identity/emotion acceptance still needs capable independent calibrated evaluators; absence fails closed.

## H3 on an already available GPU

1. Inspect `sources.lock.json` and `H3_LICENSE.txt`. Download with `python portable/models.py h3` only when you have enough disk space. It checks exact pinned official repository revisions, available storage and publisher LFS hashes. Gated/login downloads stop for the owner. The H3 downloader selects the official Comfy diffusion model and a publisher-converted full bf16 text encoder, avoiding a text-encoder quant originating from an unapproved third-party account. This means substantially more RAM/disk than the smallest quantized demo.
2. On a manually provisioned GPU environment install a CUDA-compatible PyTorch from the official selector. Run `python portable/install_comfy.py --destination ComfyUI`. This clones the pinned official ComfyUI source and installs its PyPI requirements. GPU/CUDA dependency resolution and real H3 inference remain untested here.
3. Copy the downloaded diffusion model, text encoder and VAEs to matching directories below `ComfyUI/models/`. Put exact approved shot audio and reference images in `ComfyUI/input/`. Audio should be padded/cut to the compiled frame duration; final mux uses the original supplied audio, never generated speech.
4. Start `python ComfyUI/main.py --listen 127.0.0.1 --port 8188`. Do not expose it publicly. On RunPod keep the workflow runner on the same machine; no remote paid transport is enabled.
5. Copy and edit `h3_clip.example.json`, then compile. It uses the official template's BasicGuider, conditioning output 0 and joint AV latent output 1. The audio latent has a zero noise mask. Guides pin the joint latent. The final CreateVideo uses the supplied audio directly. Graph wiring is unit-tested, not certified by real H3 inference.
6. Fill a COPY of `h3_config.example.json` with actual installed model paths/SHA256s, local runtime output root, an exact owner approval reference, license reference and compiled workflow SHA256. Set `enabled:true`; set `free_local_compute:true` only for genuinely free compute. For a paid machine already provisioned under an approved cap, use `already_provisioned_compute:true` plus `compute_approval_reference` instead. Neither flag provisions hardware or authorizes new spend. Paid pod provisioning is outside the program; approval of a rental never follows from these example files.
7. `python portable/h3.py submit --compiled output/h3-compiled.json --config my-h3-config.json --receipt output/job.json --out output/submitted.json`
8. `python portable/h3.py collect --config my-h3-config.json --receipt output/job.json --out output/h3-result`

A submission timeout writes `unknown`. Reconcile in ComfyUI history; never delete the receipt to blindly resubmit. Collected video still requires audio/pixel/full-playback QA. No automatic retry spends GPU time. Movie-level image-to-3D reconstruction is not implemented by the simple OBJ blockout helper.

## Source and license notes

- https://github.com/SYSTRAN/faster-whisper and https://huggingface.co/Systran/faster-whisper-tiny.en: MIT. Tiny English ASR is a cheap smoke baseline, not sufficient proof of all speech/timing.
- https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct: Apache 2.0; no remote model code enabled.
- https://github.com/google-ai-edge/mediapipe and https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker: Apache 2.0; exact versioned official model URL/hash in lock.
- https://github.com/comfyanonymous/ComfyUI: GPL-3.0; installed separately, not re-licensed by this project.
- https://github.com/Comfy-Org/workflow_templates: official source for the R2V template. Our minimal API graph is adapted, with source commit in lock. Template repository LICENSE is included as `COMFY_TEMPLATE_LICENSE.txt`.
- https://huggingface.co/Comfy-Org/MiniMax-H3 and https://huggingface.co/MiniMaxAI/MiniMax-H3: custom MiniMax H3 community license. See full `H3_LICENSE.txt`. It excludes US/EU/UK/Korea, including use of outputs there, and has revenue/branding/redistribution/use restrictions; commercial products above $20M yearly revenue need separate written authorization. Not an unrestricted open-source license. Hosting location/output use matter. No license purchase or gated agreement was accepted by this release.
- https://docs.comfy.org/tutorials/video/minimax/minimax-h3: hardware/workflow documentation. No real H3 hardware benchmark was obtained in this 2 GB CPU environment.

Optional downloads are explicit commands, not a side effect of inference. Model revision/file hashes go in `DOWNLOAD_LEDGER.json`. Run outputs and model caches stay outside Git. Never commit runtime secrets or model weights.

For exact padded audio and staged references after compilation:

```sh
python portable/prepare_h3_inputs.py --compiled output/h3-compiled.json --audio dialogue.wav --references actor.png --out output/h3-inputs
```

Copy staged media (not the manifest) to ComfyUI/input. `dialogue.wav` is the staged audio name. After collection, trim to `trim_to_seconds` before normal episode assembly. The graph can produce the padded grid duration. A 5 second request compiles to 124 frames/24 fps, not exactly 5 seconds. Check final assembly against the original audio again.

After collection, trim/remux with the original (unpadded) dialogue:

```sh
python portable/finalize_h3.py --video output/h3-result/render.mp4 --audio dialogue.wav --seconds 5 --out output/shot-final.mp4
```

This verifies stream presence and duration, not speech quality or acting. AAC encoding changes bytes; repeat actual-audio alignment/QA on the final assembled master. Preserve the original WAV as the alignment reference. No clip is marked accepted merely because ffmpeg succeeded.

The pinned H3 selection currently totals 75,893,003,157 bytes (about 70.7 GiB) before runtime overhead. Keep at least 100 GB disk for this baseline. The full bf16 encoder alone is about 51.5 GB; peak RAM/VRAM requirements have NOT been measured. Do not mistake the 16 GB smallest diffusion checkpoint mentioned in vendor docs for total system requirements. This CPU environment could not hold these weights, so the H3 download was not attempted.
