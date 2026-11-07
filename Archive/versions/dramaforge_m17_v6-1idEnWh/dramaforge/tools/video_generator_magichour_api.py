"""Magic Hour image-to-video backend for the ViMax RenderBackend (spend-guarded)."""
import asyncio, os, time
from pathlib import Path
from typing import List
import requests
from interfaces.video_output import VideoOutput
from forge.guard.ledger import Ledger
from forge.gates import enforce_render_allowed

BASE = "https://api.magichour.ai"

class RenderJobError(RuntimeError):
    """A paid render failed after submission may have begun.

    Carries job_id when the provider gave us one. Callers must NOT resubmit
    blindly: use recover_job(job_id) to poll the existing job, or reconcile
    with the provider dashboard first. job_id=None means the submit response
    never produced an id - a job may still exist provider-side.
    """

    def __init__(self, message, job_id=None):
        super().__init__(message)
        self.job_id = job_id


class VideoGeneratorMagicHourAPI:
    def __init__(self, api_key: str, model: str = "wan-3.0", resolution: str = "720p",
                 seconds: int = 5, credits_per_second: int = 24,
                 audio: bool = False, audio_credits_per_second: int = 0,
                 ledger_path: str | None = None,
                 rate_limiter=None, render_mode: str = "episode", project_dir: str | None = None,
                 enforce_gates: bool = True):
        self.key, self.model, self.resolution, self.seconds = api_key, model, resolution, seconds
        self.cps = credits_per_second
        self.audio = audio
        self.audio_cps = audio_credits_per_second
        self.supports_audio_request = True
        self.ledger = Ledger(ledger_path)
        self.rate_limiter = rate_limiter
        # Process gates (forge.gates): stills locked first, and a signed-off
        # proof scene, before episode-scale paid renders. render_mode='proof'
        # marks the one small proof scene itself. project_dir defaults to the
        # ledger's project (ledger at <project>/.forge/ledger.json).
        # FORGE_RENDER_MODE=proof lets a config-driven run mark itself as the
        # proof-scene run without code edits.
        self.render_mode = os.environ.get("FORGE_RENDER_MODE", render_mode)
        if project_dir is None and ledger_path:
            lp = Path(ledger_path)
            project_dir = str(lp.parent.parent) if lp.parent.name == ".forge" else str(lp.parent)
        self.project_dir = project_dir
        self.enforce_gates = enforce_gates

    def estimate(self, seconds=None, audio=None):
        use_audio = self.audio if audio is None else bool(audio)
        cps = self.cps + (self.audio_cps if use_audio else 0)
        return int((seconds or self.seconds) * cps)

    # Polling tolerates transient failures (network blips, 5xx, malformed
    # status payloads): credits are already reserved by then, so one flaky
    # GET must not kill a paid job. A bounded consecutive-error budget still
    # fails loudly, naming the job id for reconciliation.
    POLL_ATTEMPTS = 240
    POLL_INTERVAL_S = 5
    MAX_CONSECUTIVE_POLL_ERRORS = 6
    TERMINAL_STATUSES = ("error", "canceled")

    def _submit(self, prompt, image_url, seconds, audio=False):
        h = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        body = {"model": self.model, "resolution": self.resolution, "aspect_ratio": "9:16",
                "end_seconds": seconds, "name": "forge", "style": {"prompt": prompt}}
        if audio:
            body["audio"] = True
        if image_url:
            body["assets"] = {"image_file_path": image_url}
        r = requests.post(f"{BASE}/v1/image-to-video", headers=h, json=body, timeout=60)
        r.raise_for_status()
        try:
            job = r.json()
        except ValueError as e:
            raise RuntimeError(f"magichour submit returned non-JSON after credits were reserved: {e}")
        job_id = job.get("id") if isinstance(job, dict) else None
        if not job_id:
            raise RuntimeError(f"magichour submit response has no job id: {str(job)[:200]}")
        return job_id, h

    def _poll(self, job_id, headers):
        errors = 0
        for _ in range(self.POLL_ATTEMPTS):
            try:
                resp = requests.get(f"{BASE}/v1/video-projects/{job_id}", headers=headers, timeout=30)
                resp.raise_for_status()
                s = resp.json()
                if not isinstance(s, dict):
                    raise ValueError("status payload is not an object")
                status = s.get("status")
                if status is not None and not isinstance(status, str):
                    raise ValueError(f"unexpected status value {status!r}")
            except (requests.RequestException, ValueError) as e:
                errors += 1
                if errors >= self.MAX_CONSECUTIVE_POLL_ERRORS:
                    raise RuntimeError(
                        f"magichour poll failed {errors} times in a row for job {job_id}: {e}")
                time.sleep(self.POLL_INTERVAL_S)
                continue
            errors = 0
            if status == "complete":
                downloads = s.get("downloads")
                first = downloads[0] if isinstance(downloads, list) and downloads else None
                url = first.get("url") if isinstance(first, dict) else None
                if not url:
                    raise RuntimeError(
                        f"magichour job {job_id} is complete but has no download URL: {str(s)[:200]}")
                return url
            if status in self.TERMINAL_STATUSES:
                raise RuntimeError(f"magichour video job {job_id} {status}")
            time.sleep(self.POLL_INTERVAL_S)
        raise TimeoutError(
            f"magichour job {job_id} not complete after "
            f"{self.POLL_ATTEMPTS * self.POLL_INTERVAL_S}s of polling")

    def _call(self, prompt, image_url, seconds, audio=False):
        job_id = None
        try:
            job_id, headers = self._submit(prompt, image_url, seconds, audio)
            return self._poll(job_id, headers)
        except RenderJobError:
            raise
        except Exception as e:
            raise RenderJobError(
                f"clip render failed ({e}); do NOT resubmit blindly - "
                f"recover or reconcile job id: "
                f"{job_id or 'unknown (submit returned no id; a job may still exist provider-side)'}",
                job_id=job_id) from e

    async def generate_single_video(self, prompt: str, reference_image_paths: List[str], **kwargs) -> VideoOutput:
        seconds = kwargs.get("seconds", self.seconds)
        audio = bool(kwargs.get("audio", self.audio))
        if self.enforce_gates and os.environ.get("FORGE_GATES", "1") != "0":
            enforce_render_allowed(self.project_dir or ".", self.render_mode)
        self.ledger.reserve(self.estimate(seconds, audio=audio), "video")  # raises SpendLocked unless approved
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        ref = reference_image_paths[0] if reference_image_paths else None
        url = await asyncio.to_thread(self._call, prompt, ref, seconds, audio)
        return VideoOutput(fmt="url", ext="mp4", data=url)

    def recover_job(self, job_id: str) -> str:
        """Poll an already-submitted job to its download URL. Never
        resubmits; spends nothing new."""
        if not job_id:
            raise ValueError("recover_job needs the provider job id recorded at submit time")
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        return self._poll(job_id, headers)
