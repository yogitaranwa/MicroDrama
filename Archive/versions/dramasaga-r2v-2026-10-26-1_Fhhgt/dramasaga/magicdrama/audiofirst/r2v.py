"""Reference-to-video (R2V) shot planning for Magic Hour /v1/text-to-video.

This is the materially different control route the failure audit (F22/F23)
called for: instead of one generated start frame plus prose constraints,
each shot request carries named, hash-bound character/location reference
assets that the prompt addresses as @name.

Verified API contract (2026-10-26, see magichour_catalog.SOURCES):
- POST /v1/text-to-video with references: [{"file_path": "api-assets/...",
  "name": "..."}], 1-10 items; refer to them as @name in style.prompt.
- Planning and validation only. This module performs no network, upload or
  spend; live submission still requires the standard manifest approval in
  live.py, and route output still requires media review. A planned request
  is not evidence the generator will honor the references.

Scope honesty: this route covers shots without visible speech. Shots with
visible speakers need exact-audio conditioning (audio_to_video/performance
routes); reference-to-video native audio is not a locked-soundtrack contract
and this planner refuses to pretend otherwise.
"""
from __future__ import annotations

from .core import digest, finite, identifier
from .execution import signature
from .magichour_catalog import ENDPOINT, MAX_REFERENCES, R2V_MODELS, SOURCES, VERIFIED_ON, quote_credits, validate_request_shape
from .references import VIEWS, validate_reference_bank


def validate_reference_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Reference name must be nonempty text")
    if "@" in name or any(ch.isspace() for ch in name.strip()):
        raise ValueError("Reference names are single tokens without @; prompt mentions use @name")
    if len(name) > 64:
        raise ValueError("Reference name too long")
    return name.strip()


def _uploaded_path(uploads, asset_id, expected_hash):
    record = uploads.get(asset_id, {})
    path = record.get("file_path", "")
    if record.get("sha256") != expected_hash or not isinstance(path, str) \
            or not path.startswith("api-assets/") or any(p in ("", ".", "..") for p in path.split("/")):
        raise ValueError("Missing hash-bound provider upload for reference: " + asset_id)
    return path


def select_shot_references(shot, bank, uploads):
    """Bind a shot to named banked references. Explicit gaps raise; never substitute.

    shot: planning shot with id, visible_characters, location, framing (a view
    label from references.VIEWS). bank: reference bank per references.py.
    uploads: {asset_id: {"file_path": "api-assets/...", "sha256": ...}} for
    bank entries already uploaded this run.
    Returns [{"id", "name", "file_path", "kind"}...] capped at MAX_REFERENCES.
    """
    errors = validate_reference_bank(bank)
    if errors:
        raise ValueError("Reference bank invalid: " + "; ".join(errors))
    framing = shot.get("framing")
    if framing not in VIEWS:
        raise ValueError("%s: shot framing must be a bank view label, got %r" % (shot.get("id"), framing))
    refs = {r["id"]: r for r in bank["references"]}

    def _entry_characters(ref):
        chars = ref.get("characters")
        if chars is None:
            return [ref["id"]] if ref["kind"] == "character" else []
        return list(chars)

    def _bind(ref):
        if "sha256" not in ref:
            raise ValueError("%s: reference %s is not hash-bound" % (shot["id"], ref["id"]))
        return {"id": ref["id"], "name": validate_reference_name(ref.get("name", ref["id"])),
                "file_path": _uploaded_path(uploads, ref["id"], ref["sha256"]),
                "kind": ref["kind"]}

    selected = []
    for cid in shot.get("visible_characters", []):
        candidates = [r for r in bank["references"]
                      if r["kind"] == "character" and cid in _entry_characters(r)
                      and len(_entry_characters(r)) == 1 and framing in r.get("views", [])]
        if not candidates:
            raise ValueError(
                "%s: no banked %s view for %s; explicit gap, no substitution"
                % (shot["id"], framing, cid))
        primaries = [r for r in candidates if r.get("primary") is True]
        if len(primaries) == 1:
            chosen = primaries[0]
        elif len(candidates) == 1:
            chosen = candidates[0]
        else:
            raise ValueError(
                "%s: ambiguous %s view for %s (%d candidates); mark one primary"
                % (shot["id"], framing, cid, len(candidates)))
        selected.append(_bind(chosen))
    visible = shot.get("visible_characters", [])
    if len(visible) > 1:
        for r in bank["references"]:
            if (r["kind"] == "character" and set(_entry_characters(r)) == set(visible)
                    and len(_entry_characters(r)) > 1 and framing in r.get("views", [])
                    and r.get("primary") is True):
                selected.append(_bind(r))
                break
    location = shot.get("location")
    if location:
        loc_ref = None
        for r in bank["references"]:
            if r["kind"] == "location" and (r.get("location") == location or r["id"] in ("location-" + location, location)):
                loc_ref = r
                break
        if loc_ref is not None:
            selected.append(_bind(loc_ref))
    seen = set()
    deduped = []
    for s in selected:
        if s["id"] not in seen:
            seen.add(s["id"])
            deduped.append(s)
    selected = deduped
    names = [s["name"] for s in selected]
    if len(names) != len(set(names)):
        raise ValueError("%s: duplicate reference names after selection" % shot["id"])
    if len(selected) > MAX_REFERENCES:
        raise ValueError(
            "%s: shot needs %d references, over the %d limit; reduce visible identities, never drop silently"
            % (shot["id"], len(selected), MAX_REFERENCES))
    return selected


def compose_prompt(shot, references):
    """Shot prompt with @name mentions bound to the exact selected references.

    Carries action, camera, wardrobe and continuity start/end state when the
    story schema provides them. Prompt text conditions the generator; it is
    not a control guarantee (F22/F23).
    """
    parts = []
    action = shot.get("action")
    if isinstance(action, str) and action.strip():
        parts.append(action.strip())
    camera = shot.get("camera")
    if isinstance(camera, str) and camera.strip():
        parts.append("Camera: " + camera.strip())
    for state_key in ("start_state", "end_state"):
        state = shot.get(state_key)
        if isinstance(state, dict) and state:
            parts.append(state_key.replace("_", " ") + ": " + repr(state))
    mentions = []
    for ref in references:
        if ref["kind"] == "character":
            mentions.append("Keep @%s identical to the reference in face, hair, wardrobe and proportions." % ref["name"])
        elif ref["kind"] == "location":
            mentions.append("Use @%s for the location layout, lighting and dressing." % ref["name"])
    parts.extend(mentions)
    prompt = " ".join(parts)
    if not prompt:
        raise ValueError("%s: cannot compose a nonempty shot prompt" % shot.get("id"))
    return prompt


def build_r2v_request(shot, references, model, resolution, aspect_ratio, audio=False):
    """Materialize one validated /v1/text-to-video request plus its catalog quote."""
    seconds = finite(shot["seconds"], "shot seconds", 0.01)
    if seconds != int(seconds):
        raise ValueError("Reference-to-video durations are whole seconds; got %r" % seconds)
    seconds = int(seconds)
    validate_request_shape(model, seconds, resolution, aspect_ratio, len(references), audio=audio)
    body = {
        "name": shot["id"],
        "model": model,
        "end_seconds": seconds,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "audio": bool(audio),
        "references": [{"file_path": r["file_path"], "name": r["name"]} for r in references],
        "style": {"prompt": compose_prompt(shot, references)},
    }
    return {"method": "POST", "endpoint": ENDPOINT, "body": body,
            "quote": {"amount": quote_credits(model, seconds, resolution, audio=audio),
                      "unit": "credits", "verified_on": VERIFIED_ON, "source_url": SOURCES[0]},
            "live_enabled": False}


def reference_video_manifest(episode, bank, uploads, run_id, batch_id, model, resolution,
                             aspect_ratio="9:16", audio=False):
    """Plan an episode's non-speaking shots as reference-to-video jobs.

    Shots with visible speakers are refused: they need exact-audio routes and
    this planner will not silently reclassify them. Every job carries an exact
    catalog quote; the manifest still requires the standard approval token
    before any live adapter accepts it.
    """
    identifier(run_id, "run_id")
    identifier(batch_id, "batch_id")
    jobs = []
    for shot in episode["shots"]:
        speakers = set(shot.get("speakers", [])) & set(shot.get("visible_characters", []))
        if shot.get("line_ids") and speakers:
            raise ValueError(
                "%s: visible speech requires an exact-audio route; reference-to-video "
                "native audio is not a locked-soundtrack contract" % shot["id"])
        references = select_shot_references(shot, bank, uploads)
        request = build_r2v_request(shot, references, model, resolution, aspect_ratio, audio=audio)
        jobs.append({"id": "r2v-" + shot["id"], "episode_id": episode["id"], "provider": "magichour",
                     "kind": "video", "request": {"endpoint": request["endpoint"], "body": request["body"]},
                     "quote": request["quote"],
                     "reference_binding": {"reference_ids": [r["id"] for r in references],
                                           "request_sha256": signature(request)}})
    manifest = {"run_id": run_id, "batch_id": batch_id, "jobs": jobs,
                "uploads": [{"sha256": u["sha256"], "kind": "image"} for u in uploads.values()],
                "route": "magichour_reference_to_video", "model": model, "resolution": resolution,
                "catalog_verified_on": VERIFIED_ON,
                "status": "planned_not_submitted"}
    manifest["manifest_sha256"] = signature({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    return manifest


def compare_route_quotes(episode, bank, models=("minimax-h3", "seedance-2.0", "seedance-2.0-mini"),
                         resolution="720p", aspect_ratio="9:16"):
    """Side-by-side exact catalog quotes per model for the same shot list.

    Comparison only: no submission, no preference claim. Reference-count and
    duration feasibility are validated per model, so an infeasible model is
    reported as such rather than silently repriced.
    """
    per_model = {}
    for model in models:
        entry = R2V_MODELS.get(model)
        if entry is None:
            per_model[model] = {"status": "not_a_reference_model"}
            continue
        try:
            total = 0
            for shot in episode["shots"]:
                seconds = finite(shot["seconds"], "shot seconds", 0.01)
                if seconds != int(seconds):
                    raise ValueError("whole seconds required")
                speakers = set(shot.get("speakers", [])) & set(shot.get("visible_characters", []))
                if shot.get("line_ids") and speakers:
                    continue  # exact-audio route owns these; quoted separately
                refs_needed = len(shot.get("visible_characters", [])) + (1 if shot.get("location") else 0)
                validate_request_shape(model, int(seconds), resolution, aspect_ratio,
                                       max(1, refs_needed), audio=False)
                total += quote_credits(model, int(seconds), resolution)
            per_model[model] = {"status": "quoted", "credits": total, "resolution": resolution,
                                "note": "non-speaking shots only; speaking shots need exact-audio routes"}
        except ValueError as exc:
            per_model[model] = {"status": "infeasible", "reason": str(exc)}
    return {"episode_id": episode["id"], "verified_on": VERIFIED_ON,
            "source_url": SOURCES[0], "models": per_model,
            "status": "comparison_only_not_an_order"}
