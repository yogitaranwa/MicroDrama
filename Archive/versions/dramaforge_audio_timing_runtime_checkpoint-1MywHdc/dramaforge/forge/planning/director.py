"""Director-style prompt planning and optional pre-render validators.

The functions here enrich an existing m13 plan. They do not replace the
existing shot/reverse-shot planner, still locks, proof gates or render ledger.
"""
from copy import deepcopy
from typing import Callable, Dict, Iterable, Mapping, Optional

from .blocking import validate_plan_blocking
from .continuity import validate_plan_continuity
from .routes import validate_plan as validate_route_plan

DEFAULT_MAX_PROMPT_CHARS = 2500


def build_visual_bible(style: str = "", locations: Optional[Mapping] = None,
                       characters: Optional[Mapping] = None,
                       lighting: Optional[Mapping] = None,
                       camera_rules: Optional[Mapping] = None) -> Dict:
    """Normalize a small, explicit visual bible.

    locations/characters/lighting map names to short descriptions. Missing
    entries are allowed; prompts then use conservative consistency language.
    """
    return {"style": str(style or "").strip(),
            "locations": dict(locations or {}),
            "characters": dict(characters or {}),
            "lighting": dict(lighting or {}),
            "camera_rules": dict(camera_rules or {})}


def _line_text(shot: Mapping) -> str:
    line = shot.get("line") or {}
    return str(line.get("text", "")).strip()


def _speaker(shot: Mapping) -> str:
    return str(shot.get("speaker") or (shot.get("line") or {}).get("speaker") or "").strip()


def _fit_sections(sections, max_chars: int) -> str:
    optional_titles = ["CAMERA RULE", "LIGHTING", "CONTINUITY", "CHARACTER LOCK"]
    current = [s for s in sections if s[2]]
    optional = [s for s in sections if not s[2]]
    text = "\n".join(f"{title}: {body}" for title, body, _ in current + optional)
    if len(text) <= max_chars:
        return text
    kept = current + optional
    for title in list(optional_titles):
        kept = [s for s in kept if s[0] != title]
        text = "\n".join(f"{t}: {b}" for t, b, _ in kept)
        if len(text) <= max_chars:
            return text
    raise ValueError(f"director prompt exceeds {max_chars} characters after optional detail is removed")


def director_prompt(shot: Mapping, visual_bible: Optional[Mapping] = None,
                    previous_end_state: Optional[str] = None,
                    max_chars: int = DEFAULT_MAX_PROMPT_CHARS) -> str:
    """Build one deterministic prompt for a planned clip.

    The prompt is explicit but bounded. It never invents story facts; optional
    details come only from the supplied visual bible and shot fields.
    """
    bible = build_visual_bible(**dict(visual_bible or {})) if not isinstance(visual_bible, Mapping) else visual_bible
    location = str(shot.get("location", "")).strip()
    camera = str(shot.get("camera", "")).strip()
    action = str(shot.get("action", "")).strip()
    speaker = _speaker(shot)
    dialogue = _line_text(shot)
    kind = shot.get("kind", "speaker" if dialogue else "visual")
    locations = bible.get("locations", {})
    characters = bible.get("characters", {})
    lighting = bible.get("lighting", {})

    if kind == "reaction":
        core = f"Silent close-up of {speaker} in {location}, reacting without speaking. Hold the pose; subtle facial change only."
    elif kind == "visual" or not speaker:
        core = f"{camera} of {location}: {action}".strip(": ")
    else:
        core = (f"{camera}: {speaker} speaks in {location}. Only visible action: {action}. "
                f"Exact dialogue: \"{dialogue}\"")

    loc_lock = locations.get(location) or (f"Keep the same {location} set, layout, props and background details. "
                                           "Do not redesign the room between shots." if location else "")
    char_lock = characters.get(speaker) or (f"Keep {speaker}'s face, hair, wardrobe and body consistent with the locked angle still."
                                            if speaker else "")
    light = lighting.get(location, bible.get("default_lighting", ""))
    camera_rule = bible.get("camera_rules", {}).get(camera, bible.get("camera_rules", {}).get("default", ""))
    continuity = str(previous_end_state or shot.get("continuity_note") or "").strip()
    end_state = str(shot.get("end_state") or "").strip()

    sections = [
        ("SHOT", core, True),
        ("SET LOCK", loc_lock, bool(loc_lock)),
        ("CHARACTER LOCK", char_lock, bool(char_lock)),
        ("CAMERA", "One clear setup; no unmotivated camera change." if camera else "", bool(camera)),
        ("CAMERA RULE", camera_rule, bool(camera_rule)),
        ("LIGHTING", light, bool(light)),
        ("CONTINUITY", continuity, bool(continuity)),
        ("END STATE", end_state, bool(end_state)),
        ("MOTION ANCHOR", ("Match the camera movement and cut timing of the "
                           "supplied reference plate: " +
                           str(shot["motion_source"].get("path", "")))
         if isinstance(shot.get("motion_source"), Mapping) else "",
         isinstance(shot.get("motion_source"), Mapping)),
    ]
    if bible.get("style"):
        sections.insert(0, ("STYLE", bible["style"], True))
    return _fit_sections(sections, int(max_chars))


def prompt_callable(visual_bible: Optional[Mapping] = None,
                    max_chars: int = DEFAULT_MAX_PROMPT_CHARS) -> Callable[[Mapping], str]:
    def prompt(shot: Mapping) -> str:
        return director_prompt(shot, visual_bible=visual_bible, max_chars=max_chars)
    return prompt


def enrich_plan(shots: Iterable[Mapping], visual_bible: Optional[Mapping] = None,
                layout: Optional[Mapping] = None, model: Optional[str] = None,
                resolution: str = "720p", audio: bool = False,
                credit_cap: Optional[int] = None,
                max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS) -> Dict:
    """Return an enriched copy of a plan plus validation reports.

    Original shots are not mutated. Every output shot keeps its existing keys
    and adds ``director_prompt``/``prompt_chars``. Optional layout and route
    checks are reported without making network calls.
    """
    original = [dict(s) for s in shots]
    continuity = validate_plan_continuity(original)
    blocking = validate_plan_blocking(layout, original) if layout is not None else None
    route = validate_route_plan(original, model, resolution=resolution,
                                audio=audio, credit_cap=credit_cap) if model else None

    enriched = []
    previous_end = None
    route_by_n = {j["plan_n"]: j for j in route["jobs"]} if route else {}
    for i, shot in enumerate(original, 1):
        out = deepcopy(shot)
        plan_n = out.get("plan_n", out.get("n", i))
        out["director_prompt"] = director_prompt(
            out, visual_bible=visual_bible,
            previous_end_state=previous_end if out.get("continues_previous") else None,
            max_chars=max_prompt_chars)
        out["prompt_chars"] = len(out["director_prompt"])
        if route and plan_n in route_by_n:
            q = route_by_n[plan_n]
            out["requested_seconds"] = q.get("requested_seconds")
            if "seconds" in q:
                out["route_seconds"] = q["seconds"]
                out["credits"] = q["credits"]
            if "error" in q:
                out["route_error"] = q["error"]
        enriched.append(out)
        previous_end = out.get("end_state") or previous_end

    reports = {"continuity": continuity, "blocking": blocking, "route": route}
    ok = continuity["ok"] and (blocking is None or blocking["ok"]) and (route is None or route["ok"])
    return {"ok": ok, "shots": enriched, "reports": reports,
            "prompt_budget_chars": int(max_prompt_chars)}
