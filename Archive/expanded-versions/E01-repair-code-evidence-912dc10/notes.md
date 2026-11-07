# Measured local results
Environment: 1 CPU, no nvidia-smi/CUDA device, no torch. Free neural action/lip/identity inference not runnable here at a useful verified speed. No remote private-media upload made to public demo services.

pyloudnorm 0.2.0 + soundfile installed in isolated environment from official PyPI. CPU audio repair executed on original 49.39755s dry source plus full original music. Voice line-source boundaries from existing timed-plan JSON; destination windows from delivered assembly-plan. Audio candidate retains all 15 old destination windows until replacement shots exist.

Music onset selected using sustained normalized RMS rather than first nonzero sample. Removed 1.65s pre-roll. 6dB duck under speech with100ms attack/250ms release; -29LUFS bed target before duck, -18LUFS full mix target constrained by -2dBFS sample peak. Actual final WAV -18.47LUFS pyloudnorm/-18.28LUFS FFmpeg and -2.00dBTP FFmpeg. Meter difference0.19LU documented. Emotion/phone audibility UNVERIFIED. Actual whole MP3 machine transcript all15 exact lines. Six behavior tests pass.

No visual reshoot yet. Nine minimum replacement beats from prior audit are not a sufficient final scope because actual original script maps string/heel/trolley actions differently than the earlier gate config. New v44 prep manifest recovers every original script action. Shot1 and9 also have possible required replacement; shot10 requires readable faces and causal grid/table movement, not simply a band-free crop.
