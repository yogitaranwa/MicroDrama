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
