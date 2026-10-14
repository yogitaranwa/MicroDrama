"""AI Voice Manager for MicroDrama dialogue generation via Magic Hour API."""

import os
import time
import hashlib
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from ..config import MAGIC_HOUR_API_KEY, OUTPUT_DIR

# Default cinematic voice mapping for popular microdrama archetypes
VOICE_PERSONA_MAP: Dict[str, str] = {
    # Protagonist / Female Lead
    "seraphina": "Emma Watson",
    "maya": "Emma Watson",
    "heroine": "Emma Watson",
    # CEO / Male Lead
    "alexander": "Patrick Bateman",
    "julian": "Patrick Bateman",
    "ceo": "Patrick Bateman",
    "tycoon": "Patrick Bateman",
    # Antagonist / Heiress
    "victoria": "Cate Blanchett",
    "heiress": "Cate Blanchett",
    "rival": "Cate Blanchett",
}


class VoiceManager:
    """Generates crystal-clear character voice lines and syncs dialogue audio."""

    def __init__(self, magic_hour_client=None, cache_dir: Optional[Path] = None, mock_mode: bool = False):
        self.client = magic_hour_client
        self.mock_mode = mock_mode or not bool(self.client)
        self.cache_dir = cache_dir or (OUTPUT_DIR / "voices")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_voice_persona(self, speaker: str, voice_hint: str = "") -> str:
        """Resolve character name or hint to supported Magic Hour voice persona."""
        clean = (speaker or "").strip().lower()
        if clean in VOICE_PERSONA_MAP:
            return VOICE_PERSONA_MAP[clean]

        for k, v in VOICE_PERSONA_MAP.items():
            if k in clean:
                return v

        # Heuristic gender check from voice hint
        hint = (voice_hint or "").lower()
        if any(w in hint for w in ["deep", "baritone", "commanding", "male", "bass"]):
            return "Patrick Bateman"
        return "Emma Watson"

    def generate_shot_voice(
        self,
        speaker: str,
        dialogue: str,
        voice_hint: str = "",
        out_file: Optional[Path] = None,
        timeout: int = 60,
    ) -> Optional[Path]:
        """Generate high-quality spoken dialogue audio file for a single shot line."""
        if not dialogue or not dialogue.strip():
            return None

        clean_text = dialogue.strip().strip('"\'')
        if len(clean_text) < 2:
            return None

        voice_name = self.get_voice_persona(speaker, voice_hint)
        h = hashlib.sha256(f"{voice_name}:{clean_text}".encode("utf-8")).hexdigest()[:12]
        target_path = out_file or (self.cache_dir / f"{h}_{voice_name.replace(' ', '_')}.wav")

        if target_path.exists() and target_path.stat().st_size > 1000:
            return target_path

        if self.mock_mode or not self.client:
            return None

        # 1. Submit voice generation job to Magic Hour
        try:
            res = self.client.v1.ai_voice_generator.create(
                style={"prompt": clean_text, "voice_name": voice_name},
                name=f"voice_{speaker}_{h[:6]}",
            )
            job_id = res.id
        except Exception as e:
            print(f"[WARN] Failed to submit voice line for {speaker}: {e}")
            return None

        # 2. Poll until complete
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                proj = self.client.v1.audio_projects.get(id=job_id)
                state = proj.status
                if state == "complete":
                    downloads = proj.downloads or []
                    if downloads and downloads[0].url:
                        r = requests.get(downloads[0].url, timeout=30)
                        r.raise_for_status()
                        target_path.write_bytes(r.content)
                        return target_path
                elif state in ("error", "canceled"):
                    print(f"[WARN] Voice job {job_id} failed: {getattr(proj, 'error', 'unknown')}")
                    return None
            except Exception:
                pass
            time.sleep(2)

        return None
