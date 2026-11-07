"""Magic Hour image-to-video backend for the ViMax RenderBackend (spend-guarded)."""
import asyncio, time
from typing import List
import requests
from interfaces.video_output import VideoOutput
from forge.guard.ledger import Ledger

BASE = "https://api.magichour.ai"

class VideoGeneratorMagicHourAPI:
    def __init__(self, api_key: str, model: str = "wan-3.0", resolution: str = "720p",
                 seconds: int = 5, credits_per_second: int = 24, ledger_path: str | None = None,
                 rate_limiter=None):
        self.key, self.model, self.resolution, self.seconds = api_key, model, resolution, seconds
        self.cps = credits_per_second
        self.ledger = Ledger(ledger_path)
        self.rate_limiter = rate_limiter

    def estimate(self, seconds=None):
        return int((seconds or self.seconds) * self.cps)

    def _call(self, prompt, image_url, seconds):
        h = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        body = {"model": self.model, "resolution": self.resolution, "aspect_ratio": "9:16",
                "end_seconds": seconds, "name": "forge", "style": {"prompt": prompt}}
        if image_url:
            body["assets"] = {"image_file_path": image_url}
        r = requests.post(f"{BASE}/v1/image-to-video", headers=h, json=body, timeout=60)
        r.raise_for_status()
        job = r.json()
        for _ in range(240):
            s = requests.get(f"{BASE}/v1/video-projects/{job['id']}", headers=h, timeout=30).json()
            if s.get("status") == "complete":
                return s["downloads"][0]["url"]
            if s.get("status") in ("error", "canceled"):
                raise RuntimeError(f"magichour video job {s.get('status')}")
            time.sleep(5)
        raise TimeoutError(job["id"])

    async def generate_single_video(self, prompt: str, reference_image_paths: List[str], **kwargs) -> VideoOutput:
        seconds = kwargs.get("seconds", self.seconds)
        self.ledger.reserve(self.estimate(seconds), "video")  # raises SpendLocked unless approved
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        ref = reference_image_paths[0] if reference_image_paths else None
        url = await asyncio.to_thread(self._call, prompt, ref, seconds)
        return VideoOutput(fmt="url", ext="mp4", data=url)
