from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODEL_RATES_CREDITS_PER_IMAGE = {
    "z-image-turbo": 5,
    "flux-schnell": 5,
    "flux-2-klein": 5,
    "qwen-image-2.1": 10,
    "krea-2": 10,
    "seedream-v4": 40,
    "gpt-image-2": 50,
    "nano-banana": 50,
    "nano-banana-2-lite": 50,
    "nano-banana-2.1": 50,
    "seedream-v4.5-edit": 50,
    "seedream-v5-pro": 75,
    "nano-banana-2": 100,
    "gpt-image-2.5-flare": 100,
    "nano-banana-pro": 150,
}
STYLE_LOCK = (
    "cinematic photorealistic vertical frame, candlelit Yule Ball, cool blue shadows, "
    "restrained expressions, shallow depth of field, no anime, no illustration"
)

HARD_NEGATIVE = "sword, rapier, blade, knife, metal cuffs, ice skates, skate blades, tiara, crown, headpiece, long loose side braid, tuxedo jacket, extra fingers, distorted face, readable text"


def load_shot_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def candidate_prompt(shot: dict[str, Any], beat: str, candidate_index: int) -> str:
    dialogue = " ".join(shot.get("dialogue", []))
    return (
        f"{STYLE_LOCK}. Shot {shot['shot']} beat {beat}: {shot['action']} "
        f"Camera: {shot['camera']}. Required props: {', '.join(shot['props'])}. "
        f"Expression: {shot['expression']}. Dialogue context: {dialogue or 'no dialogue'}. "
        "Harry has messy black hair, round glasses, a white dress shirt, plain black long tie, a black buttoned waistcoat, dark trousers, "
        "polished black formal shoes and a plain black formal robe with a thin red inner lining. "
        "Draconia has platinum blonde hair in a braided updo made only of hair, with no headpiece, "
        "and wears the emerald embroidered sleeveless Yule gown with sheer dark green shoulder drapes "
        "and emerald formal dress shoes. Harry's wand is a slim wooden wand, never a weapon. "
        f"Variation {candidate_index} explores pose and framing only; identity and wardrobe stay fixed. "
        f"Negative prompt: {HARD_NEGATIVE}."
    )


def build_candidate_plan(shot_plan_path: str | Path, target: int = 1000) -> dict[str, Any]:
    plan = load_shot_plan(shot_plan_path)
    beats = plan["key_beats_per_shot"]
    required_states = [
        {"shot": shot["shot"], "beat": beat, "shot_data": shot}
        for shot in plan["shots"]
        for beat in beats
    ]
    per_state = max(1, target // len(required_states))
    candidates = []
    for state in required_states:
        shot = state["shot_data"]
        for i in range(1, per_state + 1):
            candidates.append({
                "candidate_id": f"E01-S{shot['shot']:02d}-{state['beat']}-C{i:02d}",
                "shot": shot["shot"],
                "beat": state["beat"],
                "candidate_index": i,
                "duration_seconds": shot["duration"],
                "action": shot["action"],
                "camera": shot["camera"],
                "props": shot["props"],
                "expression": shot["expression"],
                "prompt": candidate_prompt(shot, state["beat"], i),
                "negative_prompt": HARD_NEGATIVE,
                "selection_status": "unreviewed",
                "qa": {
                    "face_consistency": None,
                    "wardrobe_continuity": None,
                    "prop_correctness": None,
                    "expression_match": None,
                    "manual_review": None,
                    "footwear_match": None,
                    "hair_ornament_match": None,
                    "scene_action_match": None,
                    "anchor_set": "unassigned"
                }
            })
            if len(candidates) >= target:
                break
        if len(candidates) >= target:
            break
    return {
        "target": target,
        "required_states": len(required_states),
        "candidates_per_state_planned": per_state,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def estimate_cost(target: int, model: str) -> dict[str, Any]:
    if model not in MODEL_RATES_CREDITS_PER_IMAGE:
        raise ValueError(f"Unknown model rate: {model}")
    rate = MODEL_RATES_CREDITS_PER_IMAGE[model]
    return {
        "target": target,
        "model": model,
        "docs_floor_credits_per_image": rate,
        "estimated_floor_credits": target * rate,
        "note": "Estimate from the docs 'from' rate. Magic Hour warns actual cost can vary by model, resolution and image count; verify the first priced API response before scaling."
    }
