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
its protections. Optional director prompts and model-route validation are
additive: when they are not requested, the old plan/manifest flow is
unchanged.
"""
import json
import os
from typing import Callable, Dict, List, Optional

from forge.gates.common import GateLocked, read_json, state_dir, write_json, now_iso
from forge.gates.still_first import LOCK_NAME

MANIFEST_NAME = "render_manifest.json"
EXECUTION_NAME = "render_execution.json"
DEFAULT_CREDITS_PER_SECOND = 24  # Legacy fallback; prefer route_name for current model-aware quotes


def _load_plan(project_dir, plan_path=None):
    path = plan_path or os.path.join(str(project_dir), "out", "e01_plan.json")
    if not os.path.exists(path):
        raise GateLocked(f"no shot plan at {path}; run the script stage first")
    with open(path) as fh:
        plan = json.load(fh)
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


def _select_prompt(prompt_for=None, director_bible=None, max_prompt_chars=2500):
    if prompt_for is not None:
        return prompt_for
    if director_bible is not None:
        from forge.planning.director import prompt_callable
        return prompt_callable(director_bible, max_chars=max_prompt_chars)
    return default_prompt


def build_render_jobs(project_dir, plan_path=None, prompt_for: Optional[Callable] = None,
                      director_bible: Optional[Dict] = None,
                      max_prompt_chars: int = 2500) -> List[Dict]:
    """One job per planned clip. reference_still is the still-lock label the
    job depends on; still_present reports whether the lock currently covers
    it (the render gate enforces this again at spend time)."""
    plan = _load_plan(project_dir, plan_path)
    lock = read_json(state_dir(project_dir) / LOCK_NAME) or {}
    locked = lock.get("stills", {})
    prompt_for = _select_prompt(prompt_for, director_bible, max_prompt_chars)
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
            "reference_still_sha256": locked.get(label, {}).get("sha256"),
            "still_present": bool(label and label in locked),
            "location_still": f"location:{loc}" if loc else None,
            "location_still_present": bool(loc and f"location:{loc}" in locked),
        })
    return jobs


def _apply_route(jobs: List[Dict], route_name: str, resolution: str,
                 audio: bool, credit_cap: Optional[int]) -> Dict:
    from forge.planning.routes import validate_plan as validate_route_plan
    report = validate_route_plan(jobs, route_name, resolution=resolution,
                                 audio=audio, credit_cap=credit_cap)
    for job, quote in zip(jobs, report["jobs"]):
        job["requested_seconds"] = quote.get("requested_seconds")
        if "seconds" in quote:
            job["seconds"] = quote["seconds"]
            job["credits_est"] = quote["credits"]
            job["route"] = {"model": route_name, "resolution": resolution,
                            "audio": audio}
        if "error" in quote:
            job["route_error"] = quote["error"]
    return report


def _verify_generator_route(generator, route_name: str, resolution: str,
                            audio: bool, jobs: List[Dict]) -> None:
    """Fail closed before any paid call if the legacy generator would charge
    or request something different from the route-aware manifest."""
    model = getattr(generator, "model", None)
    gen_resolution = getattr(generator, "resolution", None)
    if model != route_name or gen_resolution != resolution:
        raise GateLocked(
            "route-aware execution requires generator model/resolution to match the quote: "
            f"quote {route_name}/{resolution}, generator {model}/{gen_resolution}")
    if audio and not getattr(generator, "supports_audio_request", False):
        raise GateLocked("route quote includes audio, but this generator cannot send an audio request")
    estimate = getattr(generator, "estimate", None)
    if not callable(estimate):
        raise GateLocked("route-aware execution requires generator.estimate(seconds, audio=...)")
    for job in jobs:
        try:
            try:
                quoted = estimate(job["seconds"], audio=audio)
            except TypeError:
                if audio:
                    raise GateLocked("route quote includes audio, but generator.estimate has no audio parameter")
                quoted = estimate(job["seconds"])
        except GateLocked:
            raise
        except Exception as e:
            raise GateLocked(f"generator estimate failed for clip {job.get('plan_n')}: {e}")
        if int(quoted) != int(job["credits_est"]):
            raise GateLocked(
                f"generator ledger estimate mismatch for clip {job.get('plan_n')}: "
                f"route quote {job['credits_est']}, generator {quoted}")


def plan_fingerprint(project_dir, jobs: List[Dict], route_name: Optional[str],
                     resolution: str, audio: bool) -> str:
    """Stable hash binding an execution record to exactly this project, plan
    content (prompts, snapped seconds, still labels AND their pinned bytes),
    and route (model/resolution/audio). Any change means the recorded clip
    outputs no longer describe this render and must not be skipped-to."""
    import hashlib
    payload = {
        "project": os.path.abspath(str(project_dir)),
        "route": [route_name, resolution, bool(audio)],
        "jobs": [[j.get("plan_n"), j.get("prompt"), j.get("seconds"),
                  j.get("silent"), j.get("reference_still"),
                  j.get("reference_still_path"), j.get("reference_still_sha256")]
                 for j in jobs],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _output_usable(output) -> bool:
    """What can be verified locally before trusting a recorded clip output.
    Remote URLs cannot be re-validated offline; their shape is checked and
    the human review gate owns the final watch."""
    if not isinstance(output, str) or not output.strip():
        return False
    if output.startswith(("http://", "https://")):
        return True
    return os.path.exists(output) and os.path.getsize(output) > 0


def dry_run(project_dir, plan_path=None, credits_per_second: int = DEFAULT_CREDITS_PER_SECOND,
            prompt_for: Optional[Callable] = None, route_name: Optional[str] = None,
            resolution: str = "720p", audio: bool = False,
            credit_cap: Optional[int] = None,
            director_bible: Optional[Dict] = None,
            max_prompt_chars: int = 2500) -> Dict:
    """Write .forge/render_manifest.json: the full job list, per-job credit
    estimate, and which jobs are blocked by missing locked stills. Free.

    With no route_name/director_bible this intentionally preserves the pre-
    upgrade behavior and legacy flat credit estimate. Supplying route_name
    snaps durations to that model and uses the registry quote instead.
    """
    jobs = build_render_jobs(project_dir, plan_path, prompt_for,
                             director_bible=director_bible,
                             max_prompt_chars=max_prompt_chars)
    route_report = None
    if route_name:
        route_report = _apply_route(jobs, route_name, resolution, audio, credit_cap)
    else:
        for j in jobs:
            j["credits_est"] = int(round(j["seconds"] * credits_per_second))
    blocked = [j["plan_n"] for j in jobs if (j["reference_still"] and not j["still_present"])
               or (j["location_still"] and not j["location_still_present"])]
    manifest = {"jobs": jobs, "n_jobs": len(jobs),
                "credits_est_total": (route_report["total_credits"] if route_report
                                      else sum(j["credits_est"] for j in jobs)),
                "blocked_jobs": blocked,
                "ready": not blocked and (route_report is None or route_report["ok"]),
                "written_at": now_iso()}
    if route_report is not None:
        manifest["route_report"] = route_report
    write_json(state_dir(project_dir) / MANIFEST_NAME, manifest)
    return manifest


async def execute_plan(project_dir, generator, plan_path=None,
                       prompt_for: Optional[Callable] = None,
                       route_name: Optional[str] = None,
                       resolution: str = "720p", audio: bool = False,
                       credit_cap: Optional[int] = None,
                       director_bible: Optional[Dict] = None,
                       max_prompt_chars: int = 2500,
                       resume: bool = False) -> List[str]:
    """Paid path: render every job through the given generator (e.g.
    VideoGeneratorMagicHourAPI), which enforces the gates and the credit
    ledger on every call. Returns the clip URLs/paths in plan order.

    resume=True (additive, off by default): record per-clip results in
    .forge/render_execution.json after every render. If a later clip fails,
    re-running with resume=True skips the clips already paid for instead of
    charging them again - the failure mode that once burned double credits
    on a regenerated clip. Opt-in: without resume=True the pre-m15 behavior
    (re-render everything) is unchanged.

    Safety properties of the resume record:
    - Bound by fingerprint: project, plan prompts/seconds, reference-still
      labels AND their pinned bytes, and route model/resolution/audio. Any
      change fails closed instead of returning stale clips.
    - A recorded output is validated before it is reused (local files must
      exist non-empty; URLs are shape-checked only - liveness cannot be
      verified offline, and the review gate owns the final watch).
    - A clip whose submit/poll outcome is unknown is never blindly
      resubmitted: a recorded provider job id is recovered via
      generator.recover_job (no new paid submit); without an id or without
      generator support, resume fails closed with reconcile instructions.
    - A corrupt execution record fails closed via read_json.
    """
    jobs = build_render_jobs(project_dir, plan_path, prompt_for,
                             director_bible=director_bible,
                             max_prompt_chars=max_prompt_chars)
    missing = [j["plan_n"] for j in jobs if j["reference_still"] and not j["still_present"]]
    if missing:
        raise GateLocked(f"render jobs lack locked stills for clips: {missing}")
    if route_name:
        route_report = _apply_route(jobs, route_name, resolution, audio, credit_cap)
        if not route_report["ok"]:
            raise GateLocked("render jobs fail route validation: " +
                             "; ".join(e["error"] for e in route_report["errors"]))
        _verify_generator_route(generator, route_name, resolution, audio, jobs)
    state_file = state_dir(project_dir) / EXECUTION_NAME
    state = None
    if resume:
        fingerprint = plan_fingerprint(project_dir, jobs, route_name, resolution, audio)
        state = read_json(state_file) or {"started_at": now_iso(), "jobs": {}}
        if not isinstance(state.get("jobs"), dict):
            raise GateLocked(f"execution record at {state_file} is malformed; inspect it before re-rendering")
        prior_fp = state.get("fingerprint")
        if prior_fp and prior_fp != fingerprint:
            raise GateLocked(
                "execution record belongs to a different plan/route/still set; "
                "refusing to reuse its clips. Archive it and start a fresh run deliberately.")
        state["fingerprint"] = fingerprint

    async def _recover(job, key, prior):
        recover = getattr(generator, "recover_job", None)
        if not callable(recover):
            raise GateLocked(
                f"clip {key} has in-flight paid job {prior['job_id']}; this generator "
                "cannot recover it. Reconcile the job with the provider before re-rendering.")
        import inspect
        out = recover(prior["job_id"])
        if inspect.isawaitable(out):
            out = await out
        return getattr(out, "data", out)

    urls = []
    for j in jobs:
        key = str(j.get("plan_n"))
        if state is not None:
            prior = state["jobs"].get(key)
            if prior and prior.get("status") == "done":
                if _output_usable(prior.get("output")):
                    urls.append(prior["output"])
                    continue
                raise GateLocked(
                    f"clip {key} was recorded done but its output "
                    f"({prior.get('output')!r}) is missing/empty; restore it or remove "
                    "the entry deliberately before paying to re-render it")
            if prior and prior.get("status") == "submitted" and prior.get("job_id"):
                result = await _recover(j, key, prior)
                state["jobs"][key] = {"status": "done", "output": result,
                                      "recovered_job": prior["job_id"],
                                      "credits_est": j.get("credits_est"),
                                      "rendered_at": now_iso()}
                write_json(state_file, state)
                urls.append(result)
                continue
            if prior and prior.get("status") == "unknown_outcome":
                raise GateLocked(
                    f"clip {key} may already exist provider-side (submit outcome unknown); "
                    "reconcile with the provider, then clear this entry deliberately "
                    "before re-rendering")
        refs = [j["reference_still_path"]] if j["reference_still_path"] else []
        kwargs = {"seconds": j["seconds"]}
        if route_name:
            kwargs["audio"] = audio
        try:
            out = await generator.generate_single_video(j["prompt"], refs, **kwargs)
        except Exception as e:
            if state is not None:
                job_id = getattr(e, "job_id", None)
                entry = {"error": str(e)[:500], "credits_est": j.get("credits_est"),
                         "failed_at": now_iso()}
                if hasattr(e, "job_id"):  # provider may hold a job: never resubmit blindly
                    entry["status"] = "submitted" if job_id else "unknown_outcome"
                    if job_id:
                        entry["job_id"] = job_id
                else:
                    entry["status"] = "failed"
                state["jobs"][key] = entry
                write_json(state_file, state)
            raise
        result = getattr(out, "data", out)
        if state is not None:
            state["jobs"][key] = {"status": "done", "output": result,
                                  "credits_est": j.get("credits_est"),
                                  "rendered_at": now_iso()}
            write_json(state_file, state)
        urls.append(result)
    return urls
