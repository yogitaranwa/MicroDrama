# Third-party code used

| Component | Role | Licence (code) |
|---|---|---|
| ViMax (HKUDS) | agents, pipelines, storyboard, RenderBackend (vendored, MIT) | MIT |
| LangChain / LangGraph | LLM client, stage graph | MIT |
| Instructor | schema-validated LLM output | MIT |
| MoviePy 2.x | composition, audio mixing | MIT |
| pysubs2 | ASS caption writer | MIT |
| PySceneDetect | cut / continuity QA | BSD-3 |
| OpenTimelineIO | timeline model | Apache-2.0 |
| WhisperX | word-level alignment | BSD-2 |
| Chatterbox | draft TTS with emotion control | MIT |
| Kokoro | fast preview TTS | Apache-2.0 |
| pyloudnorm | loudness mastering | MIT |

Model weights carry their own licences. Verify each before shipping outputs.

## Added in plot/video pass
| Component | License | Used for |
|---|---|---|
| LangGraph | MIT | plot stage graph (develop, outline, judge, revise) |
| DSPy | MIT | judge signature, later prompt optimisation against reference reels |
| OpenTimelineIO | Apache-2.0 | edit decision list, export to NLE formats |
| PySceneDetect | BSD-3 | single-take QA on generated shots |
| Demucs | MIT | voice/background stem separation |
| MoviePy | MIT | render from the timeline |

| LatentSync 1.5 (ByteDance) | default lip-sync engine, chosen on the Ep1 photo-real test | licence file not yet read; weights licence unverified |
| MuseTalk 1.5 (TMElyralab) | fast draft lip-sync | code MIT; model stated usable for any purpose; sub-model licences to verify |

## Lip-sync licence audit (read 31 Oct 2026)
| Component | Licence | Source | Ship status |
| --- | --- | --- | --- |
| LatentSync code | Apache-2.0 | github.com/bytedance/LatentSync/blob/main/LICENSE | ok |
| LatentSync 1.5 weights | OpenRAIL++ (use-based restrictions, commercial use allowed within them) | huggingface.co/ByteDance/LatentSync-1.5 (card metadata) | ok with restrictions; read the use clauses before commercial release |
| InsightFace pretrained models (LatentSync's face detector, FaceAnalysis in latentsync/utils/face_detector.py, downloads to checkpoints/auxiliary) | NON-COMMERCIAL research only (InsightFace README) | github.com/deepinsight/insightface | BLOCKER for commercial release of LatentSync as is. Fix: replace the detector with a permissive one (MediaPipe is already in its requirements, Apache-2.0; not yet tested here). |
| MuseTalk code | MIT | github.com/TMElyralab/MuseTalk/blob/main/LICENSE | ok |
| MuseTalk weights | stated usable for any purpose incl. commercial | huggingface.co/TMElyralab/MuseTalk | ok |
| MuseTalk deps listed in its LICENSE: sd-vae-ft-mse (MIT), whisper (MIT), face-parsing.PyTorch (MIT), DWPose (Apache-2.0) | permissive | MuseTalk LICENSE file | ok; MIT/Apache need the notice kept (attribution) |
| face-alignment (S3FD, pulled in by MuseTalk deps) | BSD-3-Clause code; S3FD weight licence not read | github.com/1adrianb/face-alignment | code ok; weights unverified |
| MuseTalk test data | non-commercial research only | MuseTalk README | not used |
Consequence: MuseTalk is clean to ship; LatentSync (the chosen default) is only clean for non-commercial use until its face detector is swapped.
