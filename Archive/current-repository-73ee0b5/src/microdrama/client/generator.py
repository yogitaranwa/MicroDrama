"""Magic Hour video generation pipeline with sequential clip generation and frame extraction."""

import os
import re
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from magic_hour import Client
from ..config import MAGIC_HOUR_API_KEY, OUTPUT_DIR, VERTICAL_FRAMING_INSTRUCTION
from ..models import Screenplay, Shot, Character
from ..narrative.prompt_builder import build_sequential_shot_prompt
from ..postprod.assembler import EpisodeAssembler
from ..series.organizer import SeriesOrganizer
from .journal import JobJournal
from .asset_manager import AssetManager


def slugify(text: str) -> str:
    """Convert beat string into safe slug."""
    cleaned = re.sub(r"[^\w\s-]", "", text).strip()
    return re.sub(r"[-\s]+", "_", cleaned).lower() or "shot"


class MagicHourGenerator:
    """Manages video shot generation using Magic Hour API with sequential frame extraction."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        journal: Optional[JobJournal] = None,
        mock_mode: bool = False,
    ):
        self.api_key = api_key or MAGIC_HOUR_API_KEY
        self.mock_mode = mock_mode or not bool(self.api_key)
        self.client = Client(token=self.api_key) if not self.mock_mode else None
        self.journal = journal or JobJournal()
        self.asset_manager = AssetManager(magic_hour_client=self.client)
        self.clips_dir = OUTPUT_DIR / "clips"
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.assembler = EpisodeAssembler()

    def generate_episode_sequentially(
        self,
        screenplay: Screenplay,
        organizer: SeriesOrganizer,
        model: str = "ltx-2.5",
        resolution: str = "480p",
        audio: bool = True,
        use_frame_extraction: bool = True,
    ) -> List[Path]:
        """Generate all 8 shots of an episode in strict sequence with last-frame continuity."""
        ep_num = screenplay.episode_number
        organizer.ensure_series_structure(episodes_count=max(10, ep_num))
        
        # Ensure character reference images are registered
        if not self.mock_mode:
            self.asset_manager.prepare_cast_references(screenplay.cast)

        generated_clips: List[Path] = []
        prev_shot: Optional[Shot] = None
        last_frame_path: Optional[Path] = None

        print(f"[SERIES] Beginning sequential generation for Episode {ep_num} ({len(screenplay.shots)} shots)...")

        for idx, shot in enumerate(screenplay.shots):
            beat_slug = slugify(shot.beat or f"beat_{idx+1}")
            out_clip_path = organizer.get_shot_clip_path(ep_num, shot.id, beat_slug)
            frame_path = organizer.get_last_frame_path(ep_num, shot.id)

            # If clip already exists on disk and is a valid render (> 200KB for live API, > 1KB for mock)
            min_clip_size = 200_000 if not self.mock_mode else 1000
            if out_clip_path.exists() and out_clip_path.stat().st_size > min_clip_size:
                print(f"[REUSE] Shot {shot.id} ({beat_slug}) already exists: {out_clip_path.name}")
                generated_clips.append(out_clip_path)
                if not frame_path.exists() and not self.mock_mode:
                    self.assembler.extract_last_frame(out_clip_path, frame_path)
                prev_shot = shot
                last_frame_path = frame_path
                continue

            # Build context-aware prompt from previous shot
            chained_prompt = build_sequential_shot_prompt(
                shot=shot,
                prev_shot=prev_shot,
                screenplay=screenplay,
                cast=screenplay.cast,
                last_frame_path=str(last_frame_path) if (last_frame_path and last_frame_path.exists()) else None,
            )

            # Find primary speaker or leading character for reference anchoring
            primary_char = None
            if shot.speaker:
                for c in screenplay.cast:
                    if c.name.lower() == shot.speaker.lower():
                        primary_char = c
                        break
            if not primary_char and screenplay.cast:
                primary_char = screenplay.cast[0]

            # Determine endpoint & start asset:
            # - Shots 2-8: continue from extracted last frame of previous shot
            # - Shot 1: seed from speaker/character reference image if available
            is_i2v = False
            start_asset = None
            start_img_file = None

            if not self.mock_mode:
                if use_frame_extraction and idx > 0 and last_frame_path and last_frame_path.exists():
                    is_i2v = True
                    start_img_file = last_frame_path
                    start_asset = self.asset_manager.upload_reference(last_frame_path)
                elif primary_char and (primary_char.api_asset_path or primary_char.reference_image_path):
                    is_i2v = True
                    start_img_file = Path(primary_char.reference_image_path) if primary_char.reference_image_path else None
                    start_asset = primary_char.api_asset_path or (self.asset_manager.upload_reference(primary_char.reference_image_path) if primary_char.reference_image_path else None)

            endpoint = "image_to_video" if is_i2v and start_asset else "text_to_video"
            payload: Dict[str, Any] = {
                "name": f"{organizer.series_slug}_ep{ep_num:02d}_{shot.id}",
                "style": {"prompt": chained_prompt},
                "end_seconds": float(shot.duration),
                "resolution": resolution,
                "model": model,
                "audio": audio,
            }

            if endpoint == "image_to_video" and start_asset:
                payload["assets"] = {"image_file_path": start_asset}
            else:
                payload["aspect_ratio"] = screenplay.aspect_ratio
                # Pass references if supported and available
                ref_list = [
                    {"name": c.name, "file_path": c.api_asset_path}
                    for c in screenplay.cast
                    if c.api_asset_path
                ]
                if ref_list and model in ("kling-3.0", "minimax-h3", "seedance-2.0", "wan-3.0"):
                    payload["references"] = ref_list[:10]

            manifest_item = {
                "shot_id": shot.id,
                "mode": "i2v" if endpoint == "image_to_video" else "t2v",
                "endpoint": endpoint,
                "payload": payload,
                "start_image_path": str(start_img_file) if start_img_file and Path(start_img_file).exists() else None,
            }

            print(f"[SHOT] Rendering {shot.id} ({beat_slug}) via {endpoint.upper()}...")
            clip_file = self.run_shot(manifest_item, target_path=out_clip_path)
            generated_clips.append(clip_file)

            # Extract last frame for subsequent shot continuity
            if not self.mock_mode and clip_file.exists():
                try:
                    self.assembler.extract_last_frame(clip_file, frame_path)
                except Exception as e:
                    print(f"[WARN] Frame extraction failed for {shot.id}: {e}")

            prev_shot = shot
            last_frame_path = frame_path

        return generated_clips

    def run_shot(
        self,
        manifest_item: Dict[str, Any],
        target_path: Optional[Path] = None,
        timeout: int = 1200,
    ) -> Path:
        """Submit and poll a single shot, downloading to specified target_path."""
        shot_id = manifest_item["shot_id"]
        payload = manifest_item["payload"]
        endpoint = manifest_item["endpoint"]
        tag = self.journal.compute_tag(payload)
        out_clip = target_path or (self.clips_dir / f"{shot_id}_{tag[:10]}.mp4")
        out_clip.parent.mkdir(parents=True, exist_ok=True)

        if out_clip.exists() and out_clip.stat().st_size > 1000:
            return out_clip

        if self.mock_mode:
            # Generate valid lightweight mock video using FFmpeg
            start_img = manifest_item.get("start_image_path")
            self._generate_mock_clip(out_clip, duration=int(payload.get("end_seconds", 8)), image_path=start_img)
            return out_clip

        job_record = self.journal.get_job(tag)

        # 1. Submit if not already submitted
        if not job_record or job_record.get("state") not in ("submitted", "complete"):
            self.journal.set_job(tag, {"state": "submitting", "shot_id": shot_id})
            try:
                api_target = getattr(self.client.v1, endpoint)
                response = api_target.create(**payload)
                job_id = response.id
                credits_charged = getattr(response, "credits_charged", None)
                job_record = {
                    "state": "submitted",
                    "id": job_id,
                    "shot_id": shot_id,
                    "credits_charged": credits_charged,
                }
                self.journal.set_job(tag, job_record)
            except Exception as e:
                self.journal.set_job(tag, {"state": "error", "error": str(e), "shot_id": shot_id})
                raise RuntimeError(f"Failed to submit {shot_id} to Magic Hour: {e}") from e

        # 2. Poll until complete
        job_id = job_record["id"]
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            status_res = self.client.v1.video_projects.get(id=job_id)
            state = status_res.status

            if state == "complete":
                downloads = status_res.downloads or []
                if not downloads:
                    raise RuntimeError(f"Shot {shot_id} marked complete but returned no download URLs.")
                download_url = downloads[0].url
                self._download_file(download_url, out_clip)
                job_record.update({
                    "state": "complete",
                    "url": download_url,
                    "final_credits": getattr(status_res, "credits_charged", None),
                })
                self.journal.set_job(tag, job_record)
                return out_clip

            if state in ("error", "canceled"):
                job_record["state"] = state
                self.journal.set_job(tag, job_record)
                raise RuntimeError(f"Shot {shot_id} processing {state} on Magic Hour.")

            time.sleep(4)

        raise TimeoutError(f"Shot {shot_id} timed out after {timeout} seconds.")

    def _generate_mock_clip(self, target_path: Path, duration: int = 8, image_path: Optional[str] = None) -> Path:
        """Create a vertical 9:16 MP4 using local FFmpeg. If image_path exists, animates character image; else uses elegant test pattern."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin = self.assembler.ffmpeg_bin
        if ffmpeg_bin:
            img = Path(image_path) if image_path else None
            if img and img.is_file():
                cmd = [
                    "-loop", "1",
                    "-i", str(img.resolve()),
                    "-f", "lavfi",
                    "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", str(duration),
                    "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    str(target_path.resolve()),
                ]
            else:
                cmd = [
                    "-f", "lavfi",
                    "-i", f"color=c=0x14141e:s=720x1280:d={duration}",
                    "-f", "lavfi",
                    "-i", f"anullsrc=r=48000:cl=stereo",
                    "-t", str(duration),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    str(target_path.resolve()),
                ]
            self.assembler.run_ffmpeg(cmd)
        else:
            target_path.write_bytes(b"MOCK_VIDEO_DATA")
        return target_path

    def _download_file(self, url: str, target_path: Path) -> None:
        """Stream download to temporary file and atomically rename."""
        temp_path = target_path.with_suffix(".part")
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(temp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
        temp_path.replace(target_path)
