"""Prompt construction for 2-stage microdrama screenplay generation with DramaBench narrative intelligence."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..models import Character, GenreTemplate, Shot, Screenplay
from ..config import VERTICAL_FRAMING_INSTRUCTION


SYSTEM_MICRODRAMA_SCREENWRITER = f"""You are an elite showrunner and screenwriter for viral mobile microdramas (such as ReelShort, DramaBox, ShortMax).
Your screenplays are not slow movies; they are fast-paced, addictive, emotionally explosive vertical drama episodes.

CORE PRINCIPLES OF VIRAL MICRODRAMAS:
1. THE 3-SECOND HOOK (Shot 1):
   Never start with establishing scenery or slow exposition. Start IN MEDIA RES with an instant shock: a glass of wine thrown, divorce papers slammed down, a gunshot, a thunderous bang on a deadbolt, or an impossible letter read aloud.
2. CONTINUOUS ESCALATION & JUICINESS:
   Every shot must shift power or raise stakes. Incorporate intense interpersonal friction, scandalous revelations, arrogant mockery, or heart-stopping suspense.
3. ULTRA-LEAN DIALOGUE (MAX 12 WORDS):
   Spoken lines must be razor-sharp, vicious, or urgent. Never write long monologues. Sentences must be short enough to speak in 2-3 seconds.
4. SPECIFIC PHYSICAL ACTION:
   Every shot must describe clear, filmable physical motion: gripping a wrist, slamming down a card, tearing an envelope, backing away in terror, pointing a trembling finger.
5. VERTICAL 9:16 FRAMING IN EVERY CAMERA INSTRUCTION:
   {VERTICAL_FRAMING_INSTRUCTION}
   Every camera field MUST specify phone-native framing: tight close-up, dramatic low-angle push-in, over-the-shoulder vertical composition.
6. THE CLIFFHANGER ENDING (Final Shot):
   End on a massive dilemma, an unexpected face reveal, an identity unmasking, or a weapon raised right before black. Never resolve the conflict neatly. Leave the audience begging to swipe to the next episode.
7. RIGID CONTINUITY:
   Keep characters' clothes, hair, jewelry, scars, and room features strictly identical from shot to shot.

OUTPUT FORMAT:
Return strictly valid JSON conforming exactly to the requested schema. No code explanations or markdown fluff."""


def get_dramabench_patterns(genre: str = "contract_marriage") -> Dict[str, Any]:
    """Retrieve mined structural patterns from the DramaBench 500 corpus."""
    patterns_dir = Path("dataset/patterns")
    result: Dict[str, Any] = {
        "hook_formulas": [],
        "cliffhanger_formulas": [],
        "dialogue_norm": "Keep spoken lines under 12 words per line with emotional punch.",
    }

    hook_file = patterns_dir / "hook_taxonomy.json"
    if hook_file.exists():
        try:
            with open(hook_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                cats = data.get("categories", {})
                for cat_name, info in cats.items():
                    result["hook_formulas"].append({
                        "category": cat_name,
                        "formula": info.get("structural_formula", ""),
                    })
        except Exception:
            pass

    cliff_file = patterns_dir / "cliffhanger_library.json"
    if cliff_file.exists():
        try:
            with open(cliff_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                forms = data.get("formulas", {})
                for form_name, info in forms.items():
                    result["cliffhanger_formulas"].append({
                        "formula_name": form_name,
                        "tempo": info.get("ending_tempo", ""),
                    })
        except Exception:
            pass

    return result


def build_sequential_shot_prompt(
    shot: Shot,
    prev_shot: Optional[Shot] = None,
    screenplay: Optional[Screenplay] = None,
    cast: Optional[List[Character]] = None,
    last_frame_path: Optional[str] = None,
) -> str:
    """Build context-chained prompt for sequential video rendering via Magic Hour.

    Injects the previous shot's visual ending state, wardrobe locks,
    and camera transition instructions to guarantee continuity.
    """
    parts = []

    # 1. Mode & Framing Foundation
    aspect = "9:16 vertical orientation, mobile cinematic framing"
    parts.append(f"Cinematic vertical video ({aspect}).")

    # 2. Sequential Continuity Anchor (from preceding shot)
    if prev_shot:
        parts.append(
            f"[CONTINUITY FROM PREVIOUS SHOT {prev_shot.id}]: "
            f"Preceding action ended with: {prev_shot.visual}. "
            f"Transition: Action continues seamlessly 0.5s later. "
            f"Preserve exact wardrobe, hair, props, room lighting: {shot.continuity or prev_shot.continuity}."
        )
        if last_frame_path:
            parts.append(
                f"[IMAGE-TO-VIDEO MODE]: Initiated from last frame of {prev_shot.id}. "
                f"Animate forward into the specified physical action."
            )
    else:
        parts.append(f"[SHOT 1 HOOK]: In-media-res explosive opening. {shot.continuity}")

    # 3. Strict Cast Locking & Crowd Suppression (Prevents random people appearing)
    active_chars = []
    if cast:
        for c in cast:
            if c.name.lower() in shot.visual.lower() or c.name.lower() in shot.action.lower() or (shot.speaker and c.name.lower() == shot.speaker.lower()):
                active_chars.append(f"@{c.name} ({c.look})")
    
    if active_chars:
        parts.append(f"[STRICT CAST IN SCENE]: {', '.join(active_chars)}.")
        parts.append("STRICT NEGATIVE CONSTRAINT: Strictly NO random extra people, no bystanders, no crowd in background. Keep focus exclusively on the designated characters.")
    else:
        parts.append("STRICT NEGATIVE CONSTRAINT: Solo portrait framing. No bystanders, no extra background people.")

    # 4. Core Visual & Environment
    parts.append(f"Visual: {shot.visual}")

    # 5. Immediate Physical Action
    parts.append(f"Action: {shot.action}")

    # 6. Camera Motion (Vertical 9:16 specific)
    parts.append(f"Camera: {shot.camera}")

    # 7. Spoken Dialogue / Emotional Expression
    if shot.dialogue and shot.speaker:
        parts.append(f"Dialogue: {shot.speaker} speaks fiercely: \"{shot.dialogue}\"")
    elif shot.dialogue:
        parts.append(f"Dialogue: Spoken with intense emotion: \"{shot.dialogue}\"")

    # 8. Lighting and Atmosphere
    parts.append("Photorealistic, 8k vertical cinema, dramatic lighting, high contrast, sharp facial focus, color graded.")

    return " ".join(parts)


def build_beat_sheet_prompt(
    story_idea: str,
    template: Optional[GenreTemplate] = None,
    shot_count: int = 8,
    specific_scenes: Optional[List[str]] = None,
    episode_number: int = 1,
    previous_cliffhanger: Optional[str] = None,
    series_canon: Optional[List[str]] = None,
    bible_context: Optional[str] = None,
    arc_objective: Optional[str] = None,
) -> str:
    """Build prompt for Stage 1: Beat Sheet outline with Series Bible intelligence."""
    dramabench_patterns = get_dramabench_patterns(template.id if template else "contract_marriage")

    prompt_dict = {
        "task": f"Create a high-octane microdrama beat sheet for Episode {episode_number}",
        "episode_number": episode_number,
        "target_shots": shot_count,
        "story_prompt": story_idea.strip(),
        "arc_objective_for_this_episode": arc_objective or "Escalate tension and deepen character conflict.",
        "previous_episode_cliffhanger_to_resolve": previous_cliffhanger or "N/A (Episode 1)",
        "bible_context_pack": bible_context or "No persistent bible context.",
        "series_canon_context": series_canon or [],
        "dramabench_structural_patterns": dramabench_patterns,
        "template_details": (
            {
                "name": template.name,
                "genre": template.genre,
                "vibe": template.vibe,
                "signature_hook": template.signature_hook,
                "cliffhanger_formulas": template.cliffhanger_formulas,
                "pacing_rules": template.pacing_rules,
            }
            if template
            else "None specified. Infer optimal microdrama tropes from prompt."
        ),
        "must_include_specific_scenes": specific_scenes or [],
        "output_format_schema": {
            "episode_number": episode_number,
            "title": f"Episode {episode_number} Title",
            "genre": template.genre if template else "Drama",
            "logline": "One-sentence logline",
            "hook_promise": "Opening hook promise (resolves prior cliffhanger)",
            "cliffhanger_promise": f"New unresolved ending cliffhanger for Episode {episode_number}",
            "beats": [
                {
                    "id": 1,
                    "beat_type": "hook",
                    "summary": "Brief beat action summary",
                    "emotional_stakes": "Emotional state shift",
                    "duration_seconds": 8,
                }
            ],
            "previous_cliffhanger": previous_cliffhanger or "",
        },
        "instructions": (
            f"This is Episode {episode_number}. "
            + (
                f"Shot 1 MUST immediately pick up from Episode {episode_number-1} cliffhanger: '{previous_cliffhanger}'. "
                if previous_cliffhanger
                else "Shot 1 MUST be an explosive in-media-res hook. "
            )
            + f"Develop intense escalation, scandalous confrontation, and finish on a NEW cliffhanger for Episode {episode_number+1}. Return ONLY valid JSON."
        ),
    }
    return json.dumps(prompt_dict, indent=2)


def build_screenplay_prompt(
    story_idea: str,
    cast: List[Character],
    template: Optional[GenreTemplate] = None,
    shot_count: int = 8,
    seconds_per_shot: int = 8,
    aspect_ratio: str = "9:16",
    specific_scenes: Optional[List[str]] = None,
    beat_sheet_summary: Optional[str] = None,
    episode_number: int = 1,
    previous_cliffhanger: Optional[str] = None,
    series_canon: Optional[List[str]] = None,
    bible_context: Optional[str] = None,
) -> str:
    """Build prompt for Stage 2: Shot-by-shot filmable screenplay."""
    cast_data = [
        {
            "name": c.name,
            "role": c.role,
            "look": c.look,
            "voice": c.voice,
            "reference_attached": bool(c.reference_image_path or c.api_asset_path),
        }
        for c in cast
    ]

    prompt_dict = {
        "task": f"Generate full filmable microdrama screenplay for Episode {episode_number}",
        "episode_number": episode_number,
        "story_prompt": story_idea.strip(),
        "previous_episode_cliffhanger_to_resolve": previous_cliffhanger or "N/A",
        "bible_context_pack": bible_context or "",
        "series_canon_context": series_canon or [],
        "beat_plan": beat_sheet_summary or "Follow standard high-tension microdrama pacing.",
        "cast_bible": cast_data,
        "shots_required": shot_count,
        "seconds_per_shot": seconds_per_shot,
        "aspect_ratio": aspect_ratio,
        "template": (
            {
                "name": template.name,
                "vibe": template.vibe,
                "climax_tropes": template.climax_tropes,
                "cliffhanger_formulas": template.cliffhanger_formulas,
            }
            if template
            else {}
        ),
        "user_specified_scenes": specific_scenes or [],
        "output_format_schema": {
            "episode_number": episode_number,
            "title": f"Episode {episode_number} Title",
            "genre": template.genre if template else "Drama",
            "vibe": template.vibe if template else "Tense, thrilling",
            "language": "English",
            "logline": "One-sentence logline",
            "hook": "Opening 0-3s hook description (resolves prior cliffhanger)",
            "cliffhanger": f"Episode {episode_number} cliffhanger description",
            "previous_cliffhanger": previous_cliffhanger or "",
            "cast": [
                {"name": c.name, "role": c.role, "look": c.look, "voice": c.voice}
                for c in cast
            ],
            "shots": [
                {
                    "id": "s01",
                    "mode": "t2v",
                    "duration": seconds_per_shot,
                    "visual": "Filmic environment, subject position, lighting",
                    "action": "Immediate physical action",
                    "camera": "Vertical 9:16 portrait: close-up / push-in",
                    "speaker": cast[0].name if cast else "",
                    "dialogue": "Short line under 12 words",
                    "audio": "Acoustic sting, tension music",
                    "beat": "01-Hook",
                    "continuity": "Fixed wardrobe, lighting, props",
                    "image_path": "",
                }
            ],
            "aspect_ratio": aspect_ratio,
        },
        "rules": [
            f"Generate exactly {shot_count} shots from s01 to s{shot_count:02}.",
            (
                f"Shot s01 MUST resolve previous cliffhanger within 3 seconds."
                if previous_cliffhanger
                else "Shot s01 MUST be a 3-second hook that jolts the viewer."
            ),
            f"Shot s{shot_count:02} MUST be a dramatic new cliffhanger leading into Episode {episode_number+1}.",
            "Dialogue must be punchy (strictly under 12 words) and speaker must match a cast member name or be empty.",
            "Each camera field must specify vertical 9:16 phone composition.",
            "Maintain strict continuity of clothing, lighting, props, and wounds. Return ONLY valid JSON.",
        ],
    }
    return json.dumps(prompt_dict, indent=2)
