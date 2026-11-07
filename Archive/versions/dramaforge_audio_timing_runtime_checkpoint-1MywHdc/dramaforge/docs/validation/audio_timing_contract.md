# Audio-driven duration contract

The pinned MultiTalk and InfiniteTalk muxers use25fps and explicitly crop source audio to frame_count/25 before muxing. A successful video file alone is not proof that the full dialogue survived.

For dialogue use `forge.integrations.audio_timing.execute_audio_job_preserving_speech`. This probes every source with ffprobe and refuses a launch that would truncate audio. It does not speed speech. A1.2s input needs at least33frames(1.32s) under the4n+1frame rule. A17frame proof is0.68s.

The legacy execute_audio_job entry point remains intact for compatibility. It does not enforce source duration. Do not use it to accept dialogue completeness. The new wrapper must be selected for any episode dialogue route before production resumes.

Only isolated technical validation may opt into allow_test_truncation=True. Its result carries rejected_truncated_test_audio and is not dialogue acceptance.

InfiniteTalkV3 validation on2026-11-06: runtime passed1671.87s,0.680svideo/AACstreams,17frames448x832at25fps. Source1.200s WAV was prefix-cropped, discarding0.520s with nonzero audio energy. Decoded AAC has0.704s including codec padding. Outputprefix/sourceprefix correlation0.9984,zero lag: cropping, not retiming. Mouth changes and reference fidelity were visually plausible for this tiny proof, but full-speech/AV-sync/multi-speaker/episode acceptance were not established.
