Chatterbox needs more than 2 GB RAM. Run it on a free Kaggle GPU notebook:
    pip install chatterbox-tts soundfile
    from forge.audio.tts import ChatterboxDraft
    ChatterboxDraft(device="cuda").say("line", "out.wav", exaggeration=0.7)
