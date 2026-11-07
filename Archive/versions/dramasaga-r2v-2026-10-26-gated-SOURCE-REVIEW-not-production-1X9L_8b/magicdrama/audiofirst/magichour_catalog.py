"""Magic Hour model catalog, verified against live docs on 2026-10-26 (Asia/Kolkata).

Sources:
- https://docs.magichour.ai/api-reference/models
- https://docs.magichour.ai/api-reference/video-projects/text-to-video
- https://docs.magichour.ai/api-reference/video-projects/image-to-video
- magic-hour Python SDK request types (registry install, 2026-10-26)

These are vendor-published constraints and credit rates at VERIFIED_ON.
They are a quote basis, not a charge: actual billing is reconciled per job
by the live ledger. Availability on the project's own plan/tier is a
separate check this catalog cannot make.
"""
from __future__ import annotations

VERIFIED_ON = "2026-10-26"
SOURCES = (
    "https://docs.magichour.ai/api-reference/models",
    "https://docs.magichour.ai/api-reference/video-projects/text-to-video",
    "https://docs.magichour.ai/api-reference/video-projects/image-to-video",
)

# Video models that accept a `references` array on /v1/text-to-video.
# credits_per_second is by resolution; audio_included means the audio toggle
# adds no extra credits per the models table. reference_kinds lists the
# reference media types the docs page names for the model.
R2V_MODELS = {
    "minimax-h3": {
        "durations": tuple(range(1, 31)),
        "resolutions": ("480p", "720p", "1080p"),
        "credits_per_second": {"480p": 24, "720p": 48, "1080p": 72},
        "audio_included": True,
        "reference_kinds": ("image", "video", "audio"),
        "aspect_ratios": ("16:9", "9:16", "1:1"),
    },
    "wan-3.0": {
        "durations": (2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30),
        "resolutions": ("480p", "720p", "1080p"),
        "credits_per_second": {"480p": 48, "720p": 96, "1080p": 180},
        "audio_included": True,
        "reference_kinds": ("image", "video", "audio"),
        "aspect_ratios": ("16:9", "9:16", "1:1"),
    },
    "seedance-2.0": {
        "durations": tuple(range(4, 16)),
        "resolutions": ("480p", "720p"),
        "credits_per_second": {"480p": 144, "720p": 288},
        "audio_included": True,
        "reference_kinds": ("image", "video", "audio"),
        "aspect_ratios": ("9:16", "16:9", "1:1"),
    },
    "seedance-2.0-mini": {
        "durations": tuple(range(4, 16)),
        "resolutions": ("480p", "720p"),
        "credits_per_second": {"480p": 96, "720p": 192},
        "audio_included": True,
        "reference_kinds": ("image", "video", "audio"),
        "aspect_ratios": ("9:16", "16:9", "1:1"),
    },
    "seedance-2.0-fast": {
        "durations": tuple(range(4, 16)),
        "resolutions": ("480p", "720p"),
        # Not listed on the models table captured 2026-10-26; priced like
        # seedance-2.0-mini is an assumption we refuse to make. Quote use
        # requires a fresh verified rate before any manifest.
        "credits_per_second": {},
        "audio_included": True,
        "reference_kinds": ("image", "video", "audio"),
        "aspect_ratios": ("9:16", "16:9", "1:1"),
    },
    "seedance-2.5": {
        "durations": tuple(range(4, 31)),
        "resolutions": ("480p", "720p"),
        "credits_per_second": {"480p": 288, "720p": 576},
        "audio_included": True,
        "reference_kinds": ("image", "video", "audio"),
        "aspect_ratios": ("9:16", "16:9", "1:1"),
    },
    "kling-3.0": {
        "durations": tuple(range(3, 16)),
        "resolutions": ("720p", "1080p", "4k"),
        "credits_per_second": {"720p": 48, "1080p": 72, "4k": 240},
        "audio_included": False,  # audio adds +24 at 720p/1080p, +48 at 4k
        "reference_kinds": ("image", "video"),
        "aspect_ratios": ("9:16", "16:9", "1:1"),
    },
    "wan-3.0": {
        "durations": (2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30),
        "resolutions": ("480p", "720p", "1080p"),
        "credits_per_second": {"480p": 48, "720p": 96, "1080p": 180},
        "audio_included": True,
        "reference_kinds": ("image", "video", "audio"),
        "aspect_ratios": ("16:9", "9:16", "1:1"),
    },
}

MAX_REFERENCES = 10  # docs: required array length 1-10 elements
ENDPOINT = "/v1/text-to-video"


def model_entry(model):
    if model not in R2V_MODELS:
        raise ValueError(
            "Model %r is not a verified reference-to-video model; verified set: %s"
            % (model, sorted(R2V_MODELS))
        )
    return R2V_MODELS[model]


def validate_request_shape(model, end_seconds, resolution, aspect_ratio, reference_count, audio=False):
    """Raise unless the request shape fits the verified catalog entry."""
    entry = model_entry(model)
    if end_seconds not in entry["durations"]:
        raise ValueError(
            "Model %s supports durations %s; got %r"
            % (model, list(entry["durations"]), end_seconds)
        )
    if resolution not in entry["resolutions"]:
        raise ValueError(
            "Model %s supports resolutions %s; got %r"
            % (model, list(entry["resolutions"]), resolution)
        )
    if aspect_ratio not in entry["aspect_ratios"]:
        raise ValueError(
            "Model %s supports aspect ratios %s; got %r"
            % (model, list(entry["aspect_ratios"]), aspect_ratio)
        )
    if not 1 <= reference_count <= MAX_REFERENCES:
        raise ValueError("Reference-to-video requires 1-%d named references" % MAX_REFERENCES)
    if audio and not entry["audio_included"]:
        raise ValueError(
            "Model %s charges extra for native audio; quote must include the surcharge explicitly"
            % model
        )


def quote_credits(model, end_seconds, resolution, audio=False):
    """Exact catalog quote in integer credits; raises when no verified rate exists."""
    entry = model_entry(model)
    validate_request_shape(model, end_seconds, resolution,
                           next(iter(entry["aspect_ratios"])), 1, audio=False)
    rate = entry["credits_per_second"].get(resolution)
    if rate is None:
        raise ValueError(
            "No verified %s credit rate at %s on %s; reverify before quoting"
            % (model, resolution, VERIFIED_ON)
        )
    total = rate * end_seconds
    if audio and not entry["audio_included"]:
        surcharge = {"720p": 24, "1080p": 24, "4k": 48}.get(resolution, 0) * end_seconds
        total += surcharge
    return int(total)
