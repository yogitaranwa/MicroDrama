"""Additive pre-render planning upgrades for forge."""

from .routes import ModelRoute, ROUTES, available_models, route, route_summary, validate_plan
from .continuity import ContinuityError, infer_characters, initial_state, apply_transition, validate_plan_continuity
from .blocking import validate_layout, visible_from, validate_shot_blocking, validate_plan_blocking, layout_svg
from .director import DEFAULT_MAX_PROMPT_CHARS, build_visual_bible, director_prompt, prompt_callable, enrich_plan
from .design_prep import (asset_sheet, location_sheet, build_design_bible,
                          validate_design_coverage, attach_motion_anchor,
                          plate_cut_times, shots_from_plate)

__all__ = [
    "ModelRoute", "ROUTES", "available_models", "route", "route_summary", "validate_plan",
    "ContinuityError", "infer_characters", "initial_state", "apply_transition", "validate_plan_continuity",
    "validate_layout", "visible_from", "validate_shot_blocking", "validate_plan_blocking", "layout_svg",
    "DEFAULT_MAX_PROMPT_CHARS", "build_visual_bible", "director_prompt", "prompt_callable", "enrich_plan",
    "asset_sheet", "location_sheet", "build_design_bible", "validate_design_coverage",
    "attach_motion_anchor", "plate_cut_times", "shots_from_plate",
]
