"""Voice engines. Drafts: Chatterbox (emotion) / Kokoro (fast). Finals: ElevenLabs within a char budget."""
import os, re
from pathlib import Path
from forge.guard.ledger import Ledger

def _save(wav, sr, path):
    import soundfile as sf
    sf.write(str(path), wav, sr)
    return str(path)

class ChatterboxDraft:
    """MIT. exaggeration 0.3 calm .. 0.9 intense; cfg_weight lower = slower pacing."""
    def __init__(self, device="cpu"):
        from chatterbox.tts import ChatterboxTTS
        self.m = ChatterboxTTS.from_pretrained(device=device)
    def say(self, text, out, voice_ref=None, exaggeration=0.6, cfg_weight=0.4):
        wav = self.m.generate(text, audio_prompt_path=voice_ref, exaggeration=exaggeration, cfg_weight=cfg_weight)
        return _save(wav.squeeze().cpu().numpy(), self.m.sr, out)

class KokoroPreview:
    """Apache-2.0, 82M, CPU-fast scratch tracks."""
    def __init__(self, lang="a", voice="af_heart"):
        from kokoro import KPipeline
        self.p, self.voice = KPipeline(lang_code=lang), voice
    def say(self, text, out, speed=1.0):
        import numpy as np
        chunks = [a for _, _, a in self.p(text, voice=self.voice, speed=speed)]
        return _save(np.concatenate(chunks), 24000, out)

class ElevenLabsFinal:
    """Finals only. Counts characters against an approved budget; refuses beyond it. Never enables top-up."""
    def __init__(self, api_key, voice_id, char_ledger=None, model="eleven_multilingual_v2"):
        self.key, self.voice_id, self.model = api_key, voice_id, model
        self.ledger = char_ledger or Ledger(os.environ.get("FORGE_CHAR_LEDGER", ".forge/chars.json"), unit="characters")
    # Content sniffing for the paid response: an error page or JSON body must
    # never be written out as a .wav after characters were charged.
    _MAGIC = (b"RIFF", b"ID3", b"fLaC", b"OggS", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")

    def say(self, text, out, voice_settings=None, seed=None):
        import requests
        import math
        payload = {"text": text, "model_id": self.model}
        if voice_settings is not None:
            if not isinstance(voice_settings, dict):
                raise ValueError("voice_settings must be a mapping")
            allowed = {"stability": (0, 1), "similarity_boost": (0, 1),
                       "style": (0, 1), "speed": (0.7, 1.2)}
            for key, value in voice_settings.items():
                if key == "use_speaker_boost":
                    if not isinstance(value, bool):
                        raise ValueError("use_speaker_boost must be boolean")
                    continue
                if key not in allowed or isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"unsupported voice setting: {key}")
                lo, hi = allowed[key]
                if not math.isfinite(value) or not lo <= value <= hi:
                    raise ValueError(f"voice setting {key} outside {lo}-{hi}")
            payload["voice_settings"] = dict(voice_settings)
        if seed is not None:
            if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 4294967295:
                raise ValueError("seed must be an unsigned 32-bit integer")
            payload["seed"] = seed
        if not text or not text.strip():
            raise ValueError("refusing paid TTS for empty text")
        self.ledger.reserve(len(text), "elevenlabs")
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
            headers={"xi-api-key": self.key}, timeout=120,
            json=payload)
        r.raise_for_status()
        body = r.content
        ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
        looks_audio = ctype.startswith("audio/") or any(body.startswith(m) for m in self._MAGIC)
        if not body or not looks_audio:
            raise RuntimeError(
                f"elevenlabs returned non-audio content ({ctype or 'unknown content-type'}, "
                f"{len(body)} bytes) after characters were charged: {body[:160]!r}")
        Path(out).write_bytes(body)
        return str(out)

def split_lines(script_text):
    """'NAME: line' -> [(name, line)] for per-character voice routing."""
    return [(m.group(1).strip(), m.group(2).strip())
            for m in re.finditer(r"^([A-Z][A-Za-z .'-]{0,30}):\s*(.+)$", script_text, re.M)]
