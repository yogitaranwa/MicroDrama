"""Form-based intake (FR1/FR2): genre, number of characters, a description
with its length limit, and the image upload-or-generation step, bound to the
planning layer.

Before this module the story premise was a hardcoded brief string in
forge/script_run.py. The form makes the intake explicit and validated, then
binds it to the existing planning layer: it produces the outline prompt the
script stage already consumes and a visual bible in the shape
forge.planning.director.build_visual_bible returns.

Validation is strict and local; nothing here calls a paid service. Image
generation is recorded as an intent ("generate") for the still-generation
step - this module never generates images itself.
"""
import json
from pathlib import Path

from forge.gates.common import state_dir, write_json, now_iso

MAX_DESCRIPTION_CHARS = 1000      # FR1: "about one thousand characters"
MAX_CHARACTERS = 8
MAX_GENRE_CHARS = 60
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
INTAKE_NAME = "intake.json"


class IntakeError(ValueError):
    """The form as submitted cannot produce a valid planning brief."""


def _clean_str(value, field, max_chars):
    if not isinstance(value, str) or not value.strip():
        raise IntakeError(f"{field} is required")
    value = value.strip()
    if len(value) > max_chars:
        raise IntakeError(f"{field} is {len(value)} characters; the limit is {max_chars}")
    return value


def _validate_reference(ref, character_name):
    if not isinstance(ref, dict):
        raise IntakeError(f"character {character_name!r} needs a reference image entry")
    mode = ref.get("mode")
    if mode not in ("upload", "generate"):
        raise IntakeError(
            f"character {character_name!r}: reference mode must be 'upload' or 'generate'")
    out = {"mode": mode}
    if mode == "upload":
        path = ref.get("path")
        if not isinstance(path, str) or not path.strip():
            raise IntakeError(f"character {character_name!r}: upload mode needs an image path")
        p = Path(path.strip())
        if p.suffix.lower() not in IMAGE_SUFFIXES:
            raise IntakeError(
                f"character {character_name!r}: {p.name} is not an image "
                f"({sorted(IMAGE_SUFFIXES)})")
        if not p.is_file() or p.stat().st_size == 0:
            raise IntakeError(f"character {character_name!r}: image missing or empty: {p}")
        out["path"] = str(p)
    else:
        prompt = ref.get("prompt", "")
        if not isinstance(prompt, str):
            raise IntakeError(f"character {character_name!r}: generate prompt must be text")
        out["prompt"] = prompt.strip()
    return out


def validate_form(form: dict) -> dict:
    """Validate and normalize one intake form. Returns a clean copy; raises
    IntakeError on the first problem found."""
    if not isinstance(form, dict):
        raise IntakeError("intake form must be an object")
    genre = _clean_str(form.get("genre"), "genre", MAX_GENRE_CHARS)
    n = form.get("num_characters")
    if isinstance(n, bool) or not isinstance(n, int):
        raise IntakeError("num_characters must be a whole number")
    if not 1 <= n <= MAX_CHARACTERS:
        raise IntakeError(f"num_characters must be 1..{MAX_CHARACTERS}, got {n}")
    description = _clean_str(form.get("description"), "description", MAX_DESCRIPTION_CHARS)

    characters = []
    raw_chars = form.get("characters") or []
    if not isinstance(raw_chars, list):
        raise IntakeError("characters must be a list")
    if raw_chars and len(raw_chars) != n:
        raise IntakeError(
            f"{len(raw_chars)} character entries for num_characters={n}")
    seen = set()
    for i, c in enumerate(raw_chars):
        if not isinstance(c, dict):
            raise IntakeError(f"character entry {i + 1} must be an object")
        name = _clean_str(c.get("name"), f"character {i + 1} name", 60)
        if name.lower() in seen:
            raise IntakeError(f"duplicate character name {name!r}")
        seen.add(name.lower())
        characters.append({
            "name": name,
            "description": str(c.get("description") or "").strip(),
            "reference": _validate_reference(c.get("reference"), name),
        })
    return {"genre": genre,
            "num_characters": n,
            "description": description,
            "characters": characters}


def brief_text(form: dict) -> str:
    """The planning-layer prompt for a validated form: the same structured
    brief shape the script stage already consumes, now built from the form
    instead of hardcoded."""
    form = validate_form(form)
    names = [c["name"] for c in form["characters"]] or [
        f"character {i + 1}" for i in range(form["num_characters"])]
    lines = [
        f"Genre: {form['genre']}.",
        f"Cast: {form['num_characters']} character(s): {', '.join(names)}.",
        f"Story: {form['description']}",
    ]
    descs = [f"- {c['name']}: {c['description']}" for c in form["characters"] if c["description"]]
    if descs:
        lines.append("Character notes:\n" + "\n".join(descs))
    lines.append(
        "Write a photorealistic vertical microdrama episode (9:16), total runtime "
        "90 to 120 seconds. DIALOGUE RULES (strict): every spoken line is two or "
        "three COMPLETE grammatical English sentences in natural spoken English, "
        "with a clear thought, a feeling and a reason in it. Never write clipped "
        "two or three word replies, never use filler words, ellipses or dashes. "
        "Characters answer each other's actual point, reveal motive and emotion, "
        "and escalate. Open on a hook in the first 3 seconds. End on a cliffhanger.")
    return "\n".join(lines)


def visual_bible(form: dict) -> dict:
    """The form's characters as a visual bible, in the exact shape
    forge.planning.director expects."""
    from forge.planning.director import build_visual_bible
    form = validate_form(form)
    return build_visual_bible(
        style="photorealistic vertical microdrama (9:16)",
        characters={c["name"]: c["description"] for c in form["characters"]})


def reference_image_plan(form: dict) -> list:
    """One still-dependency per character, for the still-lock gate: uploads
    name their file, generations name their prompt. The still_first gate owns
    locking the bytes before any render."""
    form = validate_form(form)
    plan = []
    for c in form["characters"]:
        ref = c["reference"]
        entry = {"character": c["name"], "mode": ref["mode"]}
        if ref["mode"] == "upload":
            entry["path"] = ref["path"]
        else:
            entry["prompt"] = ref.get("prompt", "")
        plan.append(entry)
    return plan


def bind_to_planning(form: dict, project_dir) -> dict:
    """Validate the form, persist it under the project's state dir, and
    return everything the planning layer needs: the outline prompt, the
    visual bible and the per-character reference-image plan."""
    clean = validate_form(form)
    binding = {"form": clean,
               "outline_prompt": brief_text(clean),
               "visual_bible": visual_bible(clean),
               "reference_images": reference_image_plan(clean),
               "bound_at": now_iso()}
    write_json(state_dir(project_dir) / INTAKE_NAME, binding)
    return binding
