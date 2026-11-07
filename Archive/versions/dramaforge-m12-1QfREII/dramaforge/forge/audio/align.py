"""Word-level timing with WhisperX (BSD-2) -> list of {word,start,end}."""
import os
# torch>=2.6 blocks the (trusted, official) VAD checkpoint unless this is set
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

def word_times(audio_path, device="cpu", model="small", lang="en"):
    import whisperx
    audio = whisperx.load_audio(audio_path)
    m = whisperx.load_model(model, device, compute_type="int8", language=lang)
    r = m.transcribe(audio, batch_size=4)
    am, meta = whisperx.load_align_model(language_code=lang, device=device)
    r = whisperx.align(r["segments"], am, meta, audio, device)
    return [{"word": w["word"], "start": w["start"], "end": w["end"]}
            for s in r["segments"] for w in s.get("words", []) if "start" in w]
