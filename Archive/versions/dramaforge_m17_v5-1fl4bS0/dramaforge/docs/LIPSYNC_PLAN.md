# Lip-sync stage

Primary: MuseTalk 1.5 (MIT code, weights stated as usable for any purpose; sub-models whisper, ft-mse-vae, DWPose, S3FD carry their own licences, still to verify).
Fallback: LatentSync 1.5 (8 GB VRAM). 1.6 needs 18 GB and does not fit a 16 GB T4.

Proven run (free Kaggle T4): demo face clip + Chatterbox line audio -> 704x1216 h264, 6.9 s, about 20 s inference.

Environment recipe (Kaggle):
- uv venv, Python 3.10; torch 2.0.1+cu118; mmcv 2.0.1 from the openmmlab cu118/torch2.0.0 wheel index
- setuptools 69.5.1 (mmengine needs pkg_resources); huggingface_hub==0.25.2
- download weights with snapshot_download, not the repo script (it upgrades huggingface_hub and breaks transformers)
- MPLBACKEND=agg; audio as 16 kHz wav

Pipeline use: per shot, face clip (video stage) + per-line Chatterbox/ElevenLabs audio -> lipsync.py (m17: `python -m forge.assemble.lipsync` gates every shot on face_policy first - multi-face refused, profile/sparse flagged for review) -> scenecheck.py -> timeline.py. Kaggle job scripts (docs/kaggle_lipsync_job.sh, kaggle_lipsync_infer.sh) run this gate before inference (STEP_GATE).
Open: real episode clips (Magic Hour spend needs approval), mouth quality judged by ear/eye by the user.

## Verdict on the first MuseTalk test (user eyeball)
"In animation it is ok ok": acceptable, not impressive. MuseTalk 1.5 stays in the stack as the working default; it is not locked as final.

## Upgrade candidates (not adopted, need a test each on the free T4)
- LatentSync 1.5 (ByteDance): diffusion lip-sync, higher fidelity than MuseTalk by reputation; 8 GB VRAM, fits. 1.6 (512px) needs 18 GB, does not fit a T4. Licence file not yet read.
- EchoMimic / EchoMimic v2 (Ant Group): audio-driven portrait animation, Apache-2.0 per its GitHub page. Animates head and expression, not just the mouth, so it may suit emotional shots better. VRAM on a T4 untested.
- Excluded on licence: Wav2Lip (non-commercial weights), VideoReTalking (CC BY-NC-SA), SadTalker (OpenRAIL-M restrictions), Sonic (commercial use needs Tencent contact).
Sources: https://github.com/antgroup/echomimic , https://github.com/TMElyralab/MuseTalk , https://deepforgehub.com/lip-sync-models-report-2026/
Caveat: the model comparisons come from third-party summaries, not from my own runs.

## Correction: target look is photo-realistic
The first test used the MuseTalk repo's demo clip, which is an animation-style face. The user's "ok ok" applies to that look only. The production target is photo-realistic, so MuseTalk is NOT proven for this pipeline yet.
Gate: MuseTalk 1.5, LatentSync 1.5 and EchoMimic must each be run on the same photo-realistic face clip and audio, judged side by side by the user. Only then is one adopted.
Test input must be free: an already-generated Ep1 clip or a free photo-realistic stock clip (Kaggle gets 403 from Pexels, so fetch elsewhere and upload as a Kaggle dataset or notebook upload). No new Magic Hour spend without approval.

## Photo-realistic test 1: MuseTalk 1.5 (production Ep1 face clip)
Input: Ep1 shot 12 base clip (photo-real Draconia, Magic Hour output already paid for), 2.5 s, 512 px high, plus Draconia Chatterbox line 1. Output 6.9 s.
Observed (frames, side by side with the source): identity, hair, dress and background kept; mouth region is softer and opens less than the source clip, so speech looks calmer and less emotional. Usable, not impressive. Gate still open: LatentSync 1.5 and EchoMimic to run on the same clip.

## Photo-realistic test 2: LatentSync 1.5 (same clip, same audio)
Setup that worked on the T4: uv venv py3.10, torch 2.5.1+cu121, requirements.txt minus gradio, huggingface_hub 0.30.2, weights from ByteDance/LatentSync-1.5 (latentsync_unet.pt, whisper/tiny.pt), configs/unet/stage2.yaml, 20 steps, guidance 1.5, deepcache, MPLBACKEND=agg. The repo main branch is 1.6 and its README points to the 1.6 weights, so 1.5 needs the 1.5 repo name.
Speed: about 4 min of GPU for 7 s of video (MuseTalk: about 20 s). Output 286x512 vs MuseTalk 512 px-high input.
Observed in frames: mouth opens wider and follows the audio more visibly than MuseTalk, closer to the source acting; face identity and background kept.
Trade: much slower; needs a retake budget. Verdict pending his review of mt_real.mp4 vs ls_real.mp4.

## Decision (user verdict, side by side on the Ep1 photo-real clip)
"LatentSync feels a little better." LatentSync 1.5 is the default lip-sync engine. MuseTalk 1.5 stays as the fast draft option. EchoMimic is skipped unless he asks for more comparisons.
Batch plan: LatentSync costs about 4 min of T4 per 7 s of video, so an episode is about 1 hour of T4. Run per-shot in batches inside the free weekly quota, with MuseTalk for drafts and timing checks.

## MediaPipe detector swap (LatentSync commercial path)
InsightFace FaceAnalysis in latentsync/utils/face_detector.py was replaced with MediaPipe FaceMesh (Apache-2.0). It builds the 106-point array at the indices LatentSync uses (brow centres 43,48,49,51,50 and 101-105, nose centre 74,77,83,86), with per-region offsets calibrated against InsightFace on 13 frames of the same clip (mean offsets all under 0.11 face-units, std 0.01-0.02).
Test: same photo-real Draconia clip (2.5 s, 512 px) and v8 audio, Kaggle T4, 20 steps, guidance 1.5.
Result: SSIM 0.991 and PSNR 44.5 dB against the InsightFace baseline output. Frame strips show no visible difference in mouth shape, sync or face edges.
Caveats: one clip, one front-facing subject. S3FD weight licence still unverified. m17 update (2026-11-02): the face_policy gate now classifies every shot before inference (see docs/M17_FUTURE_WORK.md) - verified on real EP03 footage: multi-face shots refused, profile shots flagged for review. Model-level mouth quality on profile faces still untested (Kaggle T4 route prepared).
STATUS: forge/assemble/mp_detector.py re-created and RE-TESTED on Kaggle (4 s clip, v8 audio, LatentSync main code + 1.5 weights, 20 steps): SSIM 0.989, PSNR 43.2 dB vs InsightFace baseline, no visible difference (docs/mp_retest.png). Job scripts: docs/kaggle_lipsync_job.sh and docs/kaggle_lipsync_infer.sh (set MPLBACKEND=agg).

## MuseTalk status in the shipping path
MuseTalk preprocessing uses face-alignment (S3FD face detector) plus DWPose. S3FD weights have no explicit licence grant. Until the detector is swapped and re-tested, MuseTalk is DRAFTS ONLY and must not be used for final renders. LatentSync with mp_detector.py is the only shipping lip-sync path, once the Kaggle re-test of mp_detector.py passes.
