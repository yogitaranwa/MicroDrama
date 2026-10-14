"""JSON cleanup and schema validation for microdrama screenplays.

Adapted from Jellyfish base.py and DramaBench format checkers.
"""

import re
import json
from typing import Any, Dict
from pydantic import ValidationError
from ..models import Screenplay, BeatSheet


def sanitize_json_text(text: str) -> str:
    """Repair common LLM JSON syntax defects (markdown fences, trailing commas, unquoted keys)."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    cleaned = text.strip()
    
    # 1. Strip markdown code fences
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    # 2. Remove trailing commas before closing brackets or braces
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

    # 3. Fix unquoted keys if necessary (e.g. {action: "..."} -> {"action": "..."})
    cleaned = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', cleaned)

    return cleaned


def parse_and_validate_json(raw_text: str) -> Dict[str, Any]:
    """Parse JSON with multiple fallback repair strategies including json_repair."""
    sanitized = sanitize_json_text(raw_text)
    
    # 1. Try standard json.loads
    try:
        return json.loads(sanitized)
    except json.JSONDecodeError:
        pass

    # 2. Try json_repair library
    try:
        import json_repair
        repaired = json_repair.repair_json(sanitized, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
    except Exception:
        pass

    # 3. Fallback: extract substring between the outermost braces
    start = sanitized.find("{")
    end = sanitized.rfind("}")
    if start != -1 and end != -1 and end > start:
        inner = sanitized[start:end+1]
        inner = re.sub(r",\s*([\]}])", r"\1", inner)
        try:
            return json.loads(inner)
        except json.JSONDecodeError:
            pass
        try:
            import json_repair
            repaired = json_repair.repair_json(inner, return_objects=True)
            if isinstance(repaired, dict):
                return repaired
        except Exception:
            pass

    raise ValueError(f"Failed to parse LLM response as JSON. Content preview: {sanitized[:300]}")


def validate_beat_sheet(raw_data: Any) -> BeatSheet:
    """Validate BeatSheet against Pydantic schema."""
    if isinstance(raw_data, str):
        raw_data = parse_and_validate_json(raw_data)
    try:
        return BeatSheet.model_validate(raw_data)
    except ValidationError as e:
        raise ValueError(f"BeatSheet validation failed: {e}") from None


def validate_screenplay(raw_data: Any) -> Screenplay:
    """Validate Screenplay against Pydantic schema and microdrama filming rules."""
    if isinstance(raw_data, str):
        raw_data = parse_and_validate_json(raw_data)
    
    try:
        screenplay = Screenplay.model_validate(raw_data)
    except ValidationError as e:
        raise ValueError(f"Screenplay schema error: {e}") from None

    # Cast rules
    cast_names = {c.name.strip() for c in screenplay.cast}
    if len(cast_names) != len(screenplay.cast):
        raise ValueError("Cast contains duplicate character names.")
    
    # Shot sequence and speaker validation
    for i, shot in enumerate(screenplay.shots):
        expected_id = f"s{i+1:02}"
        if shot.id != expected_id:
            # Auto-correct shot ID if misnumbered
            shot.id = expected_id
        
        # Speaker check
        if shot.speaker:
            cleaned_speaker = shot.speaker.strip()
            if cleaned_speaker not in cast_names:
                raise ValueError(
                    f"Shot {shot.id} references speaker '{shot.speaker}' not found in cast: {list(cast_names)}"
                )
            if not shot.dialogue.strip():
                shot.speaker = ""
        else:
            if shot.dialogue.strip():
                raise ValueError(f"Shot {shot.id} contains dialogue but no speaker.")

    return screenplay
