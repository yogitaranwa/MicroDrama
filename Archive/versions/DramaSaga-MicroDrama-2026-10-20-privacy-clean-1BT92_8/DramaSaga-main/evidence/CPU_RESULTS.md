# Measured CPU smoke tests, 20 October 2026

Linux, 2 CPUs, approximately 2 GB RAM, no CUDA GPU. These are tiny public-fixture smoke checks, not accuracy benchmarks or drama acceptance.

- faster-whisper 1.2.1, official Systran tiny.en: 22 expected normalized words, 0 word errors (0% fixture WER). Initial transcription including load took about 1.1 seconds. Lowest word probability was about .181. Strict .65 alignment gate rejected. Exact recognized text did not establish reliable timestamp alignment.
- Official HuggingFaceTB SmolVLM-256M: real CPU inference described white shirt, blue blazer and glasses on the official MediaPipe portrait. These broad objects were visually checked against the actual image. Model also assigned a hand side; that detail is not treated as verified. Model description is uncalibrated, not accepted QA evidence. Combined load and short response took about 7.7 seconds in the repeat smoke check.
- MediaPipe: default-threshold still-image detection returned 1 face and 478 landmarks. Strict .95 video tracking on repeated static portrait frames rejected a missing/ambiguous face. No moving-mouth fixture, identity accuracy or lip-sync accuracy was measured. Raw tracking never supplies invented confidence scores.
- 227 unit/integration tests passed. H3 graph binding, padding, local submission failure handling and final remux are code-tested. No real H3 inference ran.
- Explicit release downloader itself fetched/rechecked the pinned ASR weights and versioned face model successfully. PyTorch CPU, Transformers, faster-whisper, MediaPipe and supporting packages installed from official indexes.

Full raw smoke output is in `cpu_smoke.json`. Installed official model commits/file hashes are in `installed_model_sources.json`. Original fixture URLs and hashes are in the raw smoke result. Fixtures, model weights and the installed environment are not bundled.

The portable H3 selection is about 75.9 GB decimal (70.7 GiB) before runtime/dependency overhead, including the full bf16 text encoder. This selection avoids an unapproved third-party-origin quant. A future owner may select a smaller official-publisher encoder if verified. No such download/inference or paid GPU was started here. Windows/Kaggle/Colab/RunPod execution remains untested on those hosts.
