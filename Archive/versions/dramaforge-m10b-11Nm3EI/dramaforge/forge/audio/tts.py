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
    def say(self, text, out):
        import requests
        self.ledger.reserve(len(text), "elevenlabs")
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
            headers={"xi-api-key": self.key}, timeout=120,
            json={"text": text, "model_id": self.model})
        r.raise_for_status()
        Path(out).write_bytes(r.content)
        return str(out)

def split_lines(script_text):
    """'NAME: line' -> [(name, line)] for per-character voice routing."""
    return [(m.group(1).strip(), m.group(2).strip())
            for m in re.finditer(r"^([A-Z][A-Za-z .'-]{0,30}):\s*(.+)$", script_text, re.M)]
