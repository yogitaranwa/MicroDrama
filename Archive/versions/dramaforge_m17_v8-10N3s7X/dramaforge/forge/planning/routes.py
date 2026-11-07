"""Model route capabilities and credit quotes for pre-render planning.

Free, local validation only. The registry is a snapshot of Magic Hour's
official model/cost documentation read on 2026-11-02; refresh it before
relying on prices later. No route here is submitted by this module.
"""
from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

SOURCE_URL = "https://docs.magichour.ai/api-reference/models"
RETRIEVED_ON = "2026-11-02"


@dataclass(frozen=True)
class ModelRoute:
    name: str
    credits_per_second: Mapping[str, int]
    durations: Optional[Tuple[int, ...]] = None
    min_seconds: Optional[int] = None
    max_seconds: Optional[int] = None
    audio: str = "none"  # none, included, extra
    audio_credits_per_second: Mapping[str, int] = None

    def duration_for(self, seconds: float) -> int:
        try:
            value = float(seconds)
        except (TypeError, ValueError):
            raise ValueError("shot seconds must be a positive number")
        if not math.isfinite(value) or value <= 0:
            raise ValueError("shot seconds must be a positive number")
        if self.durations:
            for allowed in sorted(self.durations):
                if allowed + 1e-9 >= value:
                    return allowed
            raise ValueError(
                f"{self.name} supports only {', '.join(map(str, sorted(self.durations)))}s; "
                f"requested {value:g}s")
        need = int(math.ceil(value - 1e-9))
        if self.min_seconds is not None and need < self.min_seconds:
            raise ValueError(f"{self.name} needs at least {self.min_seconds}s")
        if self.max_seconds is not None and need > self.max_seconds:
            raise ValueError(f"{self.name} supports at most {self.max_seconds}s; requested {value:g}s")
        return need

    def credits_for(self, seconds: float, resolution: str, audio: bool = False) -> Tuple[int, int]:
        if resolution not in self.credits_per_second:
            raise ValueError(f"{self.name} does not list {resolution}; choose {sorted(self.credits_per_second)}")
        if audio and self.audio == "none":
            raise ValueError(f"{self.name} does not support native audio")
        snapped = self.duration_for(seconds)
        rate = int(self.credits_per_second[resolution])
        if audio and self.audio == "extra":
            extra = (self.audio_credits_per_second or {}).get(resolution)
            if extra is None:
                raise ValueError(f"{self.name} has no published audio rate for {resolution}")
            rate += int(extra)
        return snapped, snapped * rate


ROUTES: Dict[str, ModelRoute] = {
    "gemini-omni-1.1": ModelRoute(
        "gemini-omni-1.1", {"360p": 48, "720p": 144, "1080p": 192, "4k": 384},
        durations=tuple(range(3, 11)), audio="none"),
    "ltx-2.5": ModelRoute(
        "ltx-2.5", {"480p": 24, "720p": 48, "1080p": 72},
        min_seconds=1, max_seconds=60, audio="included"),
    "minimax-h3": ModelRoute(
        "minimax-h3", {"480p": 24, "720p": 48, "1080p": 72},
        min_seconds=1, max_seconds=30, audio="included"),
    "wan-2.2": ModelRoute(
        "wan-2.2", {"480p": 24, "720p": 48, "1080p": 72},
        durations=(3, 4, 5, 6, 7, 8, 9, 10, 15), audio="none"),
    "wan-3.0": ModelRoute(
        "wan-3.0", {"480p": 48, "720p": 96, "1080p": 180},
        durations=(2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30),
        audio="included"),
    "kling-2.6": ModelRoute(
        "kling-2.6", {"720p": 36, "1080p": 72},
        durations=(5, 10), audio="none"),
    "kling-3.0": ModelRoute(
        "kling-3.0", {"720p": 48, "1080p": 72, "4k": 240},
        durations=tuple(range(3, 16)), audio="extra",
        audio_credits_per_second={"720p": 24, "1080p": 24, "4k": 48}),
    "veo3.1-lite": ModelRoute(
        "veo3.1-lite", {"720p": 48, "1080p": 72},
        durations=(4, 6, 8, 16, 24, 32, 40, 48, 56), audio="extra",
        audio_credits_per_second={"720p": 24, "1080p": 24}),
    "veo3.1": ModelRoute(
        "veo3.1", {"720p": 96, "1080p": 120},
        durations=(4, 6, 8, 16, 24, 32, 40, 48, 56), audio="extra",
        audio_credits_per_second={"720p": 24, "1080p": 24}),
    "seedance-1.5": ModelRoute(
        "seedance-1.5", {"480p": 30, "720p": 60, "1080p": 90},
        durations=tuple(range(4, 13)), audio="extra",
        audio_credits_per_second={"480p": 30, "720p": 60, "1080p": 90}),
    "seedance-2.0-mini": ModelRoute(
        "seedance-2.0-mini", {"480p": 48, "720p": 120},
        durations=tuple(range(4, 16)), audio="included"),
    "seedance-2.0-fast": ModelRoute(
        "seedance-2.0-fast", {"480p": 84, "720p": 180},
        durations=tuple(range(4, 16)), audio="included"),
    "seedance-2.0": ModelRoute(
        "seedance-2.0", {"480p": 96, "720p": 216, "1080p": 528, "4k": 1104},
        durations=tuple(range(4, 16)), audio="included"),
    "seedance-2.5": ModelRoute(
        "seedance-2.5", {"480p": 168, "720p": 336, "1080p": 840},
        durations=tuple(range(4, 31)), audio="included"),
    "sora-2": ModelRoute(
        "sora-2", {"720p": 120},
        durations=(4, 8, 12, 24, 36, 48, 60), audio="included"),
}


def route(name: str) -> ModelRoute:
    try:
        return ROUTES[name]
    except KeyError:
        raise ValueError(f"unknown model route {name!r}; available: {', '.join(sorted(ROUTES))}")


def available_models() -> List[str]:
    return sorted(ROUTES)


def validate_plan(shots: Iterable[Mapping], model: str, resolution: str = "720p",
                  audio: bool = False, credit_cap: Optional[int] = None) -> Dict:
    """Validate/snap durations and quote every planned shot without spending.

    Returns a report instead of raising so a manifest can show all blockers at
    once. Input shots are not mutated.
    """
    r = route(model)
    jobs: List[Dict] = []
    errors: List[Dict] = []
    total_seconds = 0
    total_credits = 0
    for i, shot in enumerate(shots, 1):
        plan_n = shot.get("plan_n", i)
        requested = shot.get("seconds", 0)
        entry = {"plan_n": plan_n, "requested_seconds": requested}
        try:
            snapped, credits = r.credits_for(requested, resolution, audio=audio)
            entry.update({"seconds": snapped, "credits": credits,
                          "model": model, "resolution": resolution,
                          "audio": audio})
            total_seconds += snapped
            total_credits += credits
        except ValueError as e:
            entry["error"] = str(e)
            errors.append({"plan_n": plan_n, "error": str(e)})
        jobs.append(entry)
    if credit_cap is not None and total_credits > int(credit_cap):
        errors.append({"plan_n": None,
                       "error": f"credit cap exceeded: {total_credits} > {int(credit_cap)}"})
    return {"ok": not errors, "model": model, "resolution": resolution,
            "audio": audio, "jobs": jobs, "errors": errors,
            "total_seconds": total_seconds, "total_credits": total_credits,
            "credit_cap": credit_cap, "source_url": SOURCE_URL,
            "rates_retrieved_on": RETRIEVED_ON}


def route_summary() -> Dict[str, Dict]:
    return {name: {"resolutions": sorted(r.credits_per_second),
                   "durations": sorted(r.durations) if r.durations else [r.min_seconds, r.max_seconds],
                   "audio": r.audio}
            for name, r in sorted(ROUTES.items())}
