"""Matched-control seed A/B experiment builder (m19).

Tests the claim that seed variation causes voice pitch shifts / skipped
beats / visual inconsistency. Controls: same route, same shot, same
resolution, same duration, same audio settings - ONLY the seed varies.
The verdict is scoped: it speaks to seed sensitivity of the chosen route
on this shot class, not to other models or a causal proof from one run."""
from __future__ import annotations

from forge.planning.routes import route
from forge.integrations.registry import IntegrationError


def build_seed_ab(route_name: str, shot_id: str, seconds: float,
                  resolution: str, seeds=(42, 43), audio: bool = True) -> dict:
    """Return an executable plan: two generations differing only in seed."""
    r = route(route_name)
    if len(set(seeds)) != len(seeds) or len(seeds) < 2:
        raise IntegrationError("seed A/B needs at least two distinct seeds")
    snapped, credits_each = r.credits_for(seconds, resolution, audio=audio)
    runs = []
    for s in seeds:
        runs.append({"shot": shot_id, "route": route_name,
                     "resolution": resolution, "seconds": snapped,
                     "audio": audio, "seed": int(s),
                     "credits": credits_each})
    return {"hypothesis": "seed variation alone changes voice pitch / beat "
                          "timing / visual identity on this route",
            "controls": {"route": route_name, "resolution": resolution,
                         "seconds": snapped, "audio": audio,
                         "varied": "seed only"},
            "runs": runs, "total_credits": credits_each * len(runs),
            "verdict_scope": f"seed sensitivity of {route_name} at "
                             f"{resolution} on shots like {shot_id}; not a "
                             "claim about other models, voices or routes",
            "compare": ["voice pitch contour vs reference take",
                        "skipped/merged beats vs script line timing",
                        "face/outfit identity vs approved stills"]}
