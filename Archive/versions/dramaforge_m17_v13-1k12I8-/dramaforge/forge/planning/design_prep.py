"""Pre-production design discipline: design the recurring world BEFORE
generation, and let real footage anchor motion where available.

Lesson applied (creator breakdown of a shoot-then-transform workflow):
- every recurring asset (character, prop, creature, vehicle, set piece)
  gets a blueprint-style design sheet up front, not a per-shot reinvention;
- every scene gets a location sheet describing the place;
- a real-footage plate can anchor a shot's camera movement and cuts - the
  plate drives timing/motion, generation fills the world.

Everything here is local and free: sheets are validated data, coverage is a
fail-closed gate, and plate analysis uses ffmpeg scene detection. Nothing
in this module generates media, calls a paid service, or fabricates a
design - a missing sheet blocks the plan instead of inventing one.
"""
import os
import subprocess
from typing import Dict, Iterable, List, Mapping, Optional

from forge.gates.common import GateLocked, state_dir

DESIGN_BIBLE_NAME = "design_bible.json"

ASSET_KINDS = ("character", "prop", "creature", "vehicle", "set_piece", "other")
MAX_DESC_CHARS = 600
MAX_FEATURES = 12
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


class DesignError(ValueError):
    """A design or location sheet is malformed; nothing is invented."""


def _req_str(value, field, max_chars=MAX_DESC_CHARS):
    if not isinstance(value, str) or not value.strip():
        raise DesignError(f"{field} is required")
    value = value.strip()
    if len(value) > max_chars:
        raise DesignError(f"{field} is {len(value)} characters; the limit is {max_chars}")
    return value


def asset_sheet(name, kind, description, notes="") -> Dict:
    """One blueprint-style design sheet for a recurring asset. The
    description is the design lock: appearance, materials, silhouette -
    specific enough that two shots of the asset cannot drift apart."""
    name = _req_str(name, "asset name", 80)
    if kind not in ASSET_KINDS:
        raise DesignError(f"asset {name!r}: kind must be one of {ASSET_KINDS}")
    return {"name": name, "kind": kind,
            "description": _req_str(description, f"asset {name!r} design description"),
            "notes": str(notes or "").strip()}


def location_sheet(name, description, key_features=None, time_of_day="",
                   lighting="") -> Dict:
    """One sheet per scene location: what the place is, its fixed features,
    and its light - the per-scene reference generation must respect."""
    name = _req_str(name, "location name", 80)
    features = [str(f).strip() for f in (key_features or []) if str(f).strip()]
    if len(features) > MAX_FEATURES:
        raise DesignError(f"location {name!r}: at most {MAX_FEATURES} key features")
    return {"name": name,
            "description": _req_str(description, f"location {name!r} description"),
            "key_features": features,
            "time_of_day": str(time_of_day or "").strip(),
            "lighting": str(lighting or "").strip()}


def build_design_bible(style="", assets=None, locations=None) -> Dict:
    """The pre-production bible: validated sheets keyed by name. Duplicate
    names are rejected - two sheets for one asset is drift by definition."""
    out = {"style": str(style or "").strip(), "assets": {}, "locations": {}}
    for sheet in (assets or []):
        if sheet["name"] in out["assets"]:
            raise DesignError(f"duplicate asset sheet: {sheet['name']!r}")
        out["assets"][sheet["name"]] = dict(sheet)
    for sheet in (locations or []):
        if sheet["name"] in out["locations"]:
            raise DesignError(f"duplicate location sheet: {sheet['name']!r}")
        out["locations"][sheet["name"]] = dict(sheet)
    return out


def validate_design_coverage(plan: Iterable[Mapping], bible: Mapping) -> Dict:
    """Fail-closed coverage gate: every location the plan uses needs a
    location sheet; every speaking character needs a character asset sheet;
    every asset a shot explicitly lists needs its sheet. A missing sheet
    blocks the plan with the full missing list - we never generate around
    an undesigned asset."""
    assets = bible.get("assets", {})
    locations = bible.get("locations", {})
    missing = []
    checked = 0
    for shot in plan:
        checked += 1
        label = shot.get("plan_n", shot.get("src_shot", checked))
        loc = str(shot.get("location", "")).strip()
        if loc and loc not in locations:
            missing.append(f"shot {label}: no location sheet for {loc!r}")
        speaker = str(shot.get("speaker") or (shot.get("line") or {}).get("speaker") or "").strip()
        if speaker and not (speaker in assets and assets[speaker].get("kind") == "character"):
            missing.append(f"shot {label}: no character design sheet for {speaker!r}")
        for name in shot.get("assets", []) or []:
            if str(name).strip() not in assets:
                missing.append(f"shot {label}: no design sheet for asset {name!r}")
    if missing:
        raise GateLocked(
            "design coverage incomplete - design sheets must exist before "
            "generation:\n" + "\n".join(missing))
    return {"checked": checked, "missing": []}


def attach_motion_anchor(shot: Mapping, plate_path) -> Dict:
    """Bind a real-footage plate to a shot: the plate's camera movement and
    cut timing are the reference the generated shot must match. The plate
    must be a real local video file - an anchor that does not exist would
    silently turn into free invention."""
    path = str(plate_path)
    if os.path.splitext(path)[1].lower() not in VIDEO_SUFFIXES:
        raise DesignError(f"motion plate is not a video file ({sorted(VIDEO_SUFFIXES)}): {path}")
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise DesignError(f"motion plate missing or empty: {path}")
    out = dict(shot)
    out["motion_source"] = {"path": os.path.abspath(path),
                            "role": "camera movement and cut timing reference"}
    return out


def plate_cut_times(plate_path, threshold: float = 0.3) -> List[float]:
    """Cut timestamps of a real plate via ffmpeg scene detection - the
    plate's editing, recovered locally and free."""
    path = str(plate_path)
    if not os.path.isfile(path):
        raise DesignError(f"motion plate missing: {path}")
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", path,
         "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True)
    times = []
    for line in proc.stderr.splitlines():
        if "showinfo" in line and "pts_time:" in line:
            try:
                t = float(line.split("pts_time:", 1)[1].split()[0])
            except (ValueError, IndexError):
                continue
            if not times or t - times[-1] > 0.05:
                times.append(t)
    return times


def shots_from_plate(plate_path, location="", threshold: float = 0.3) -> List[Dict]:
    """Shot skeletons whose boundaries and durations come from the plate's
    cuts: the real footage anchors the edit, one skeleton per segment, each
    already carrying its motion anchor."""
    import cv2
    cap = cv2.VideoCapture(str(plate_path))
    if not cap.isOpened():
        raise DesignError(f"cannot open motion plate: {plate_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    duration = frames / fps if fps else 0.0
    cuts = plate_cut_times(plate_path, threshold)
    bounds = [0.0] + cuts + ([duration] if duration else [])
    shots = []
    for i in range(len(bounds) - 1):
        secs = round(bounds[i + 1] - bounds[i], 3)
        if secs <= 0:
            continue
        shots.append(attach_motion_anchor(
            {"kind": "visual", "location": location, "seconds": secs,
             "action": "match the reference plate for this segment"},
            plate_path))
    if not shots and duration > 0:
        shots.append(attach_motion_anchor(
            {"kind": "visual", "location": location, "seconds": round(duration, 3),
             "action": "match the reference plate for this segment"},
            plate_path))
    return shots


def _validate_bible_dict(data) -> Dict:
    """Re-validate a raw bible document; a malformed bible fails closed -
    silently ignoring it would drop the coverage guarantee."""
    if not isinstance(data, dict):
        raise GateLocked("design bible must be a JSON object")
    raw_assets = data.get("assets", [])
    raw_locations = data.get("locations", [])
    # accept both the authoring form (lists of sheets) and the stored form
    # (sheets keyed by name); every sheet is re-validated either way
    if isinstance(raw_assets, dict):
        raw_assets = list(raw_assets.values())
    if isinstance(raw_locations, dict):
        raw_locations = list(raw_locations.values())
    try:
        assets = [asset_sheet(a["name"], a["kind"], a["description"],
                              a.get("notes", "")) for a in raw_assets]
        locations = [location_sheet(l["name"], l["description"],
                                    l.get("key_features"), l.get("time_of_day", ""),
                                    l.get("lighting", ""))
                     for l in raw_locations]
        return build_design_bible(data.get("style", ""), assets, locations)
    except (KeyError, TypeError, DesignError) as exc:
        raise GateLocked(f"design bible is malformed: {exc}")


def save_bible(project_dir, bible_data) -> str:
    """Validate and install the project's design bible at
    .forge/design_bible.json; from then on the plan and render gates
    enforce it."""
    import json
    bible = _validate_bible_dict(bible_data)
    path = state_dir(project_dir) / DESIGN_BIBLE_NAME
    path.write_text(json.dumps(bible, indent=1))
    return str(path)


def load_bible(project_dir) -> Optional[Dict]:
    """The project's design bible, or None when the project never opted in
    (absent = old behavior). A present but malformed bible raises."""
    import json, os
    path = os.path.join(str(project_dir), ".forge", DESIGN_BIBLE_NAME)
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return _validate_bible_dict(json.load(fh))


def main(argv=None) -> int:
    """CLI: python -m forge.planning.design_prep
      save-bible PROJECT_DIR BIBLE_JSON   validate + install the bible
      validate PROJECT_DIR [--plan PATH]  enforce coverage on a plan (exit 3 when blocked)
      cuts PLATE [--threshold 0.3]        print the plate's cut times
      skeleton PLATE [--location L]       print shot skeletons from the plate's cuts"""
    import argparse, json, sys
    ap = argparse.ArgumentParser(prog="forge.planning.design_prep")
    sub = ap.add_subparsers(dest="op", required=True)
    sb = sub.add_parser("save-bible")
    sb.add_argument("project_dir")
    sb.add_argument("bible_json")
    va = sub.add_parser("validate")
    va.add_argument("project_dir")
    va.add_argument("--plan", default=None)
    cu = sub.add_parser("cuts")
    cu.add_argument("plate")
    cu.add_argument("--threshold", type=float, default=0.3)
    sk = sub.add_parser("skeleton")
    sk.add_argument("plate")
    sk.add_argument("--location", default="")
    sk.add_argument("--threshold", type=float, default=0.3)
    args = ap.parse_args(argv)
    try:
        if args.op == "save-bible":
            with open(args.bible_json) as fh:
                print(json.dumps({"saved": save_bible(args.project_dir, json.load(fh))}))
            return 0
        if args.op == "validate":
            bible = load_bible(args.project_dir)
            if bible is None:
                print(json.dumps({"enforced": False,
                                  "reason": "no design bible installed for this project"}))
                return 0
            plan_path = args.plan or os.path.join(str(args.project_dir), "out", "e01_plan.json")
            with open(plan_path) as fh:
                plan = json.load(fh)
            print(json.dumps({"enforced": True, **validate_design_coverage(plan, bible)}))
            return 0
        if args.op == "cuts":
            print(json.dumps(plate_cut_times(args.plate, args.threshold)))
            return 0
        print(json.dumps(shots_from_plate(args.plate, location=args.location,
                                          threshold=args.threshold)))
        return 0
    except GateLocked as exc:
        print(json.dumps({"refused": True, "reason": str(exc)}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
