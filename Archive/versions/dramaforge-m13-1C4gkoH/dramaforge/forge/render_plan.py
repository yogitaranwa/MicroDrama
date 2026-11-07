"""Plan-driven rendering: the shot/reverse-shot plan actually drives what
gets rendered, clip by clip.

Before this module the render loop lived outside the repo and the plan only
fed the angle-still gate. Now the plan is the render list: every planned
clip becomes one job naming its prompt, its reference still (the locked
angle-matched still for that speaker/camera) and its seconds. Reaction clips
are marked silent so no voice/lip-sync is expected of them.

dry_run() is the default and costs nothing: it writes the manifest and a
credit estimate. execute_plan() runs the jobs through the existing
spend-guarded, gate-enforcing generator - the only paid path, unchanged in
its protections.
"""
import json
import os
from typing import Callable, Dict, List, Optional

from forge.gates.common import GateLocked, read_json, state_dir, write_json, now_iso
from forge.gates.still_first import LOCK_NAME

MANIFEST_NAME = "render_manifest.json"
DEFAULT_CREDITS_PER_SECOND = 24  # Magic Hour 720p reference rate; caller may override


def _load_plan(project_dir, plan_path=None):
    path = plan_path or os.path.join(str(project_dir), "out", "e01_plan.json")
    if not os.path.exists(path):
        raise GateLocked(f"no shot plan at {path}; run the script stage first")
    plan = json.load(open(path))
    if not isinstance(plan, list) or not plan:
        raise GateLocked(f"shot plan at {path} is empty or malformed")
    return plan


def default_prompt(planned_shot: Dict) -> str:
    """Deterministic per-clip prompt from the plan. Small and restrained on
    purpose: one visible action, one speaker (or none for reactions)."""
    loc = planned_shot.get("location", "")
    cam = planned_shot.get("camera", "")
    action = planned_shot.get("action", "")
    sp = planned_shot.get("speaker")
    if planned_shot.get("kind") == "reaction":
        return (f"Silent close-up of {sp} in {loc}, reacting without speaking; "
                f"camera {cam}; hold the pose, subtle facial change only.")
    if planned_shot.get("kind") == "visual" or not sp:
        return f"{cam} of {loc}: {action}".strip(": ")
    line = (planned_shot.get("line") or {}).get("text", "")
    return (f"{cam}: {sp} speaks in {loc}. Action (only this): {action}. "
            f"Dialogue: \"{line}\"")


def build_render_jobs(project_dir, plan_path=None, prompt_for: Optional[Callable] = None) -> List[Dict]:
    """One job per planned clip. reference_still is the still-lock label the
    job depends on; still_present reports whether the lock currently covers
    it (the render gate enforces this again at spend time)."""
    plan = _load_plan(project_dir, plan_path)
    lock = read_json(state_dir(project_dir) / LOCK_NAME) or {}
    locked = lock.get("stills", {})
    prompt_for = prompt_for or default_prompt
    jobs = []
    for p in plan:
        from forge.gates.angle_stills import angle_class
        sp = p.get("speaker")
        label = f"character:{sp}:angle:{angle_class(p.get('camera', ''))}" if sp else None
        loc = (p.get("location") or "").strip()
        jobs.append({
            "plan_n": p.get("plan_n"), "src_shot": p.get("src_shot"),
            "kind": p.get("kind"), "speaker": sp,
            "silent": p.get("kind") in ("reaction", "visual"),
            "seconds": float(p.get("seconds", 5)),
            "prompt": prompt_for(p),
            "reference_still": label,
            "reference_still_path": locked.get(label, {}).get("path"),
            "still_present": bool(label and label in locked),
            "location_still": f"location:{loc}" if loc else None,
            "location_still_present": bool(loc and f"location:{loc}" in locked),
        })
    return jobs


def dry_run(project_dir, plan_path=None, credits_per_second: int = DEFAULT_CREDITS_PER_SECOND,
            prompt_for: Optional[Callable] = None) -> Dict:
    """Write .forge/render_manifest.json: the full job list, per-job credit
    estimate, and which jobs are blocked by missing locked stills. Free."""
    jobs = build_render_jobs(project_dir, plan_path, prompt_for)
    for j in jobs:
        j["credits_est"] = int(round(j["seconds"] * credits_per_second))
    blocked = [j["plan_n"] for j in jobs if (j["reference_still"] and not j["still_present"])
               or (j["location_still"] and not j["location_still_present"])]
    manifest = {"jobs": jobs, "n_jobs": len(jobs),
                "credits_est_total": sum(j["credits_est"] for j in jobs),
                "blocked_jobs": blocked, "ready": not blocked,
                "written_at": now_iso()}
    write_json(state_dir(project_dir) / MANIFEST_NAME, manifest)
    return manifest


async def execute_plan(project_dir, generator, plan_path=None,
                       prompt_for: Optional[Callable] = None) -> List[str]:
    """Paid path: render every job through the given generator (e.g.
    VideoGeneratorMagicHourAPI), which enforces the gates and the credit
    ledger on every call. Returns the clip URLs/paths in plan order."""
    jobs = build_render_jobs(project_dir, plan_path, prompt_for)
    missing = [j["plan_n"] for j in jobs if j["reference_still"] and not j["still_present"]]
    if missing:
        raise GateLocked(f"render jobs lack locked stills for clips: {missing}")
    urls = []
    for j in jobs:
        refs = [j["reference_still_path"]] if j["reference_still_path"] else []
        out = await generator.generate_single_video(j["prompt"], refs, seconds=j["seconds"])
        urls.append(getattr(out, "data", out))
    return urls
