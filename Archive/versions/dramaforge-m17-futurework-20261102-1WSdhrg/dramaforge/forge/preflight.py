"""Non-spending preflight of an open generation graph, plus one bounded
quality test on already-paid outputs - run BEFORE any new spending.

preflight() walks exactly the graph a render would execute (same plan loader,
same job builder, same route validation) and reports what a paid run would
need, without reserving a single credit. It proves it spent nothing by
snapshotting the ledger before and after; any change fails closed.

bounded_quality_check() is the project's own comparison record made
executable: the local, free QA checks (duration, hard cuts, black frames,
silence, caption stream) run on ONE already-rendered episode, so quality is
measured on output the project already owns instead of hypothesized before
spending again. It is bounded: files over MAX_SECONDS are refused.
"""
import json
import os
import subprocess

from forge.gates.common import GateLocked, read_json, state_dir, now_iso
from forge.gates.still_first import LOCK_NAME
from forge.guard.ledger import Ledger
from forge.render_plan import build_render_jobs, _load_plan
from forge.planning.routes import route as resolve_route

PREFLIGHT_NAME = "preflight.json"
MAX_SECONDS = 300  # the quality check is bounded to one short episode


def _ffprobe(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        raise GateLocked("ffprobe not found; install ffmpeg to run the quality check")
    except subprocess.CalledProcessError as e:
        raise GateLocked(f"ffprobe failed on {path}: {e.stderr.strip()[:200]}")
    return json.loads(out)


def preflight(project_dir, plan_path=None, route_name=None, resolution="720p",
              audio: bool = False, credit_cap=None, ledger_path=None) -> dict:
    """Walk the render graph without spending. Checks, in order:
    plan loads; route resolvable and every job's duration snappable; every
    still the jobs depend on is locked; gate state files readable; the
    approved budget covers the estimate. Writes .forge/preflight.json.
    The ledger is snapshotted before and after; a changed ledger means this
    function is being misused in a live render and fails closed."""
    ledger = Ledger(ledger_path or (state_dir(project_dir) / "ledger.json"))
    before = ledger._read()
    issues = []

    plan = _load_plan(project_dir, plan_path)
    jobs = build_render_jobs(project_dir, plan_path)

    total = 0
    if route_name:
        try:
            rt = resolve_route(route_name)
        except ValueError as e:
            raise GateLocked(str(e))
        for job in jobs:
            try:
                snapped = rt.duration_for(job["seconds"])
                _, credits = rt.credits_for(snapped, resolution, audio=audio)
                job["seconds"] = snapped
                job["credits_est"] = credits
                total += credits
            except ValueError as e:
                issues.append(f"clip {job.get('plan_n')}: {e}")
    else:
        from forge.render_plan import DEFAULT_CREDITS_PER_SECOND
        for job in jobs:
            job["credits_est"] = int(round(job["seconds"] * DEFAULT_CREDITS_PER_SECOND))
            total += job["credits_est"]

    missing_stills = [j["plan_n"] for j in jobs
                      if (j["reference_still"] and not j["still_present"])
                      or (j["location_still"] and not j["location_still_present"])]
    if missing_stills:
        issues.append(f"locked stills missing for clips: {missing_stills}")

    for name in ("still_lock.json", "scene_proof.json", "proof_checklist.json"):
        read_json(state_dir(project_dir) / name)  # corrupt state raises, by design

    if credit_cap is not None and total > credit_cap:
        issues.append(f"estimate {total} credits exceeds the credit cap {credit_cap}")
    remaining = before["approved"] - before["spent"]
    if total > remaining:
        issues.append(
            f"estimate {total} credits exceeds the approved budget remaining ({remaining})")

    after = ledger._read()
    if after != before:
        raise GateLocked("ledger changed during preflight; preflight must never spend")

    report = {"ok": not issues, "issues": issues, "n_jobs": len(jobs),
              "estimate_credits": total,
              "route": {"model": route_name, "resolution": resolution, "audio": audio},
              "ledger": {"approved": before["approved"], "spent": before["spent"]},
              "ran_at": now_iso()}
    from forge.gates.common import write_json
    write_json(state_dir(project_dir) / PREFLIGHT_NAME, report)
    return report


def bounded_quality_check(video_path, max_seconds: float = MAX_SECONDS) -> dict:
    """One bounded, free quality pass over an already-rendered episode:
    duration, resolution, hard cuts (PySceneDetect), black frames and silent
    stretches (ffmpeg), and whether a subtitle/caption stream is present.
    Refuses files over max_seconds so the check stays bounded. Local only;
    judges nothing a human ear/eye owns - the report feeds the review gate."""
    video_path = str(video_path)
    if not os.path.isfile(video_path) or os.path.getsize(video_path) == 0:
        raise GateLocked(f"episode file missing or empty: {video_path}")
    meta = _ffprobe(video_path)
    seconds = float(meta.get("format", {}).get("duration", 0) or 0)
    if seconds <= 0:
        raise GateLocked(f"could not read a duration from {video_path}")
    if seconds > max_seconds:
        raise GateLocked(
            f"{seconds:.0f}s exceeds the bounded-check limit of {max_seconds}s; "
            "split the episode or raise the bound deliberately")
    video_streams = [s for s in meta.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in meta.get("streams", []) if s.get("codec_type") == "audio"]
    sub_streams = [s for s in meta.get("streams", []) if s.get("codec_type") == "subtitle"]
    issues = []
    if not video_streams:
        issues.append("no video stream")
    if not audio_streams:
        issues.append("no audio stream")

    from forge.assemble.qa import cuts
    found = cuts(video_path)
    width = int(video_streams[0].get("width", 0)) if video_streams else 0
    height = int(video_streams[0].get("height", 0)) if video_streams else 0

    def _ffmpeg_filter(spec):
        try:
            return subprocess.run(
                ["ffmpeg", "-hide_banner", "-nostats", "-i", video_path,
                 "-vf", spec, "-f", "null", "-"],
                capture_output=True, text=True, timeout=600).stderr
        except FileNotFoundError:
            raise GateLocked("ffmpeg not found; install ffmpeg to run the quality check")

    black = [line for line in _ffmpeg_filter("blackdetect=d=0.5:pix_th=0.10").splitlines()
             if "blackdetect:" in line]
    if black:
        issues.append(f"black frames detected: {len(black)} stretch(es)")
    sil = [line for line in
           subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video_path,
                           "-af", "silencedetect=n=-45dB:d=3", "-f", "null", "-"],
                          capture_output=True, text=True, timeout=600).stderr.splitlines()
           if "silence_start" in line]
    if sil:
        issues.append(f"silent stretches over 3s: {len(sil)}")

    report = {"episode": video_path, "seconds": round(seconds, 2),
              "width": width, "height": height,
              "vertical": bool(height > width),
              "scenes": len(found), "hard_cuts": max(0, len(found) - 1),
              "audio_streams": len(audio_streams),
              "caption_stream": bool(sub_streams),
              "issues": issues, "ok": not issues,
              "checked_at": now_iso()}
    return report
