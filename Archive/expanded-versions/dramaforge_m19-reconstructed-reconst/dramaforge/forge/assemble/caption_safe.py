"""Platform-safe caption placement.

Lesson applied (user-supplied reel reference): burned-in subtitles sat on
top of the platform's own caption area. These presets lift our captions
above that zone. margin_v values are in the same PlayResY units the
existing writers already use (their defaults are 260/180) - conservative
starting points for a 1080-wide vertical frame, not measurements: each
platform's UI chrome moves, so placement still gets a visual check.
"""
from typing import Dict

PLATFORM_MARGIN_V: Dict[str, int] = {
    "generic": 260,           # existing default (does NOT clear the zone)
    "instagram_reels": 400,   # clears a ~340px caption + bottom UI zone
    "tiktok": 420,            # caption zone + right action rail clearance
    "youtube_shorts": 380,    # title/channel overlay zone
}


class PlatformError(ValueError):
    """Unknown platform preset; guessing a margin would hide the choice."""


def platform_safe_ass_kw(platform: str = "generic", **overrides) -> Dict:
    """ASS kwargs with the platform's safe bottom margin. Explicit
    margin_v in overrides always wins over the preset."""
    key = str(platform or "generic").strip().lower()
    if key not in PLATFORM_MARGIN_V:
        raise PlatformError(
            f"unknown caption platform {platform!r}; known presets: "
            f"{sorted(PLATFORM_MARGIN_V)} (pass margin_v explicitly for others)")
    kw = {"margin_v": PLATFORM_MARGIN_V[key]}
    kw.update(overrides)
    return kw
