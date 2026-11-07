"""Magic Hour image backend for the ViMax RenderBackend (image only, spend-guarded)."""
import asyncio, base64
from typing import List
import requests
from interfaces.image_output import ImageOutput
from forge.guard.ledger import Ledger

BASE = "https://api.magichour.ai"

class ImageGeneratorMagicHourAPI:
    def __init__(self, api_key: str, model: str = "flux-schnell", orientation: str = "portrait",
                 credits_per_image: int = 5, ledger_path: str | None = None, rate_limiter=None):
        self.key, self.model, self.orientation = api_key, model, orientation
        self.credits_per_image = credits_per_image
        self.ledger = Ledger(ledger_path)
        self.rate_limiter = rate_limiter

    def _call(self, prompt):
        h = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        r = requests.post(f"{BASE}/v1/ai-image-generator", headers=h, timeout=60, json={
            "image_count": 1, "orientation": self.orientation, "model": self.model,
            "style": {"prompt": prompt}})
        r.raise_for_status()
        job = r.json()
        import time
        for _ in range(120):
            s = requests.get(f"{BASE}/v1/image-projects/{job['id']}", headers=h, timeout=30).json()
            if s.get("status") == "complete":
                return s["downloads"][0]["url"]
            if s.get("status") in ("error", "canceled"):
                raise RuntimeError(f"magichour image job {s.get('status')}")
            time.sleep(3)
        raise TimeoutError(job["id"])

    async def generate_single_image(self, prompt: str, reference_image_paths: List[str], **kwargs) -> ImageOutput:
        self.ledger.reserve(self.credits_per_image, "image")
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        url = await asyncio.to_thread(self._call, prompt)
        return ImageOutput(fmt="url", ext="png", data=url)
