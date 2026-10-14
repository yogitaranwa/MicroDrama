"""Series directory and file organizer for AI MicroDrama Series Generator.

Manages Netflix/Kuku FM style hierarchical output structure:
outputs/{series_slug}/
    series_bible.json
    series_metadata.json
    episode_01/
        clips/
        master/
        subtitles/
        storyboard/
        screenplay/
        verification/
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class SeriesOrganizer:
    """Manages the filesystem hierarchy for a microdrama series."""

    def __init__(self, series_name: str, base_dir: Optional[Path] = None):
        """Initialize the organizer with a series name and base output directory."""
        self.series_name = series_name
        self.base_dir = Path(base_dir) if base_dir else Path("outputs")
        self.series_slug = self._sanitize_slug(series_name)
        self.series_dir = self.base_dir / self.series_slug

    @staticmethod
    def _sanitize_slug(name: str) -> str:
        """Convert a series name into a safe filesystem folder name."""
        cleaned = re.sub(r"[^\w\s-]", "", name).strip()
        slug = re.sub(r"[-\s]+", "_", cleaned)
        return slug or "untitled_series"

    def ensure_series_structure(self, episodes_count: int = 10) -> Path:
        """Create the entire directory skeleton for the series and all episodes."""
        self.series_dir.mkdir(parents=True, exist_ok=True)

        for ep_num in range(1, episodes_count + 1):
            ep_dir = self.get_episode_dir(ep_num)
            for sub in ["clips", "master", "subtitles", "storyboard", "screenplay", "verification", "voices"]:
                (ep_dir / sub).mkdir(parents=True, exist_ok=True)

        return self.series_dir

    def get_voices_dir(self, ep_num: int) -> Path:
        """Get the voices folder for a given episode."""
        voices_dir = self.get_episode_dir(ep_num) / "voices"
        voices_dir.mkdir(parents=True, exist_ok=True)
        return voices_dir

    def get_shot_voice_path(self, ep_num: int, shot_id: str) -> Path:
        """Get path for a shot dialogue voice audio file (e.g. s01_voice.wav)."""
        return self.get_voices_dir(ep_num) / f"{shot_id}_voice.wav"

    def get_episode_dir(self, ep_num: int) -> Path:
        """Get the root directory for a given episode."""
        return self.series_dir / f"episode_{ep_num:02d}"

    def get_clips_dir(self, ep_num: int) -> Path:
        """Get the clips folder for a given episode."""
        clips_dir = self.get_episode_dir(ep_num) / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        return clips_dir

    def get_shot_clip_path(self, ep_num: int, shot_id: str, beat_slug: str = "") -> Path:
        """Get the path for an individual shot clip (e.g. s01_hook.mp4)."""
        suffix = f"_{beat_slug}" if beat_slug else ""
        filename = f"{shot_id}{suffix}.mp4"
        return self.get_clips_dir(ep_num) / filename

    def get_last_frame_path(self, ep_num: int, shot_id: str) -> Path:
        """Get path for extracted last-frame transition image (e.g. s01_lastframe.png)."""
        return self.get_clips_dir(ep_num) / f"{shot_id}_lastframe.png"

    def get_master_dir(self, ep_num: int) -> Path:
        """Get the master directory for a given episode."""
        master_dir = self.get_episode_dir(ep_num) / "master"
        master_dir.mkdir(parents=True, exist_ok=True)
        return master_dir

    def get_master_path(self, ep_num: int) -> Path:
        """Get path for the final stitched master video."""
        return self.get_master_dir(ep_num) / f"episode_{ep_num:02d}_master.mp4"

    def get_subtitles_dir(self, ep_num: int) -> Path:
        """Get the subtitles directory for a given episode."""
        sub_dir = self.get_episode_dir(ep_num) / "subtitles"
        sub_dir.mkdir(parents=True, exist_ok=True)
        return sub_dir

    def get_subtitles_path(self, ep_num: int, ext: str = "ass") -> Path:
        """Get path for episode subtitle file (.ass or .srt)."""
        clean_ext = ext.lstrip(".")
        return self.get_subtitles_dir(ep_num) / f"episode_{ep_num:02d}.{clean_ext}"

    def get_storyboard_dir(self, ep_num: int) -> Path:
        """Get the storyboard directory for a given episode."""
        sb_dir = self.get_episode_dir(ep_num) / "storyboard"
        sb_dir.mkdir(parents=True, exist_ok=True)
        return sb_dir

    def get_storyboard_card_path(self, ep_num: int, shot_id: str) -> Path:
        """Get path for a specific shot storyboard image card."""
        return self.get_storyboard_dir(ep_num) / f"{shot_id}_storyboard.png"

    def get_screenplay_dir(self, ep_num: int) -> Path:
        """Get the screenplay directory for a given episode."""
        sc_dir = self.get_episode_dir(ep_num) / "screenplay"
        sc_dir.mkdir(parents=True, exist_ok=True)
        return sc_dir

    def get_screenplay_path(self, ep_num: int) -> Path:
        """Get path for episode screenplay JSON."""
        return self.get_screenplay_dir(ep_num) / f"episode_{ep_num:02d}_screenplay.json"

    def get_verification_dir(self, ep_num: int) -> Path:
        """Get the verification directory for a given episode."""
        v_dir = self.get_episode_dir(ep_num) / "verification"
        v_dir.mkdir(parents=True, exist_ok=True)
        return v_dir

    def get_continuity_report_path(self, ep_num: int) -> Path:
        """Get path for rule-based continuity audit JSON."""
        return self.get_verification_dir(ep_num) / "continuity_report.json"

    def get_semantic_test_path(self, ep_num: int) -> Path:
        """Get path for LLM semantic continuity test result JSON."""
        return self.get_verification_dir(ep_num) / "semantic_test.json"

    def get_quality_scores_path(self, ep_num: int) -> Path:
        """Get path for DramaBench quality evaluation JSON."""
        return self.get_verification_dir(ep_num) / "quality_scores.json"

    def get_bible_path(self) -> Path:
        """Get path for series_bible.json at the series root."""
        return self.series_dir / "series_bible.json"

    def get_metadata_path(self) -> Path:
        """Get path for series_metadata.json at the series root."""
        return self.series_dir / "series_metadata.json"

    def save_metadata(self, data: Dict[str, Any]) -> None:
        """Save series-level Netflix/Kuku FM metadata to disk."""
        self.series_dir.mkdir(parents=True, exist_ok=True)
        path = self.get_metadata_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_metadata(self) -> Optional[Dict[str, Any]]:
        """Load series-level metadata if it exists."""
        path = self.get_metadata_path()
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_existing_episodes(self) -> List[int]:
        """List episode numbers that currently exist on disk."""
        if not self.series_dir.exists():
            return []
        ep_nums = []
        for item in self.series_dir.iterdir():
            if item.is_dir() and item.name.startswith("episode_"):
                match = re.search(r"episode_(\d+)", item.name)
                if match:
                    ep_nums.append(int(match.group(1)))
        return sorted(ep_nums)
