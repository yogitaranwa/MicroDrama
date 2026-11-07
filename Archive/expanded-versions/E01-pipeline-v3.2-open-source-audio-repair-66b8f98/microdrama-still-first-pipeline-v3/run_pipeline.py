#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from microdrama.manifest import build_manifest, write_manifest
from microdrama.scriptqa import validate_script_file
from microdrama.stills import build_candidate_plan, estimate_cost
from microdrama.detectors import mechanical_report
from microdrama.reviewgate import (evaluate_episode, gate_check,
                                   load_receipts, scaffold_receipt)
from microdrama.continuity import validate_continuity_document
from microdrama.routes import plan_route
from microdrama.visualqa import full_qa_report, qa_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Still-first MicroDrama pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate-script")
    p.add_argument("--script", required=True)

    p = sub.add_parser("plan-stills")
    p.add_argument("--shot-plan", required=True)
    p.add_argument("--target", type=int, default=252)
    p.add_argument("--out", required=True)

    p = sub.add_parser("estimate-still-cost")
    p.add_argument("--target", type=int, required=True)
    p.add_argument("--model", required=True)
    
    p = sub.add_parser("qa-video")
    p.add_argument("--video", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--dialogue-windows", default=None,
                   help="Optional JSON file with a list of {start,end} line windows; "
                        "enables music-bed gap level measurement")

    p = sub.add_parser("gate-check")
    p.add_argument("--requirements", required=True,
                   help="Gate requirements config (beats, timings, required actions)")
    p.add_argument("--assets", required=True,
                   help="JSON mapping of beat id to asset path")
    p.add_argument("--receipts-dir", default=None,
                   help="Directory of *.receipt.json human review receipts")
    p.add_argument("--out", default=None)

    p = sub.add_parser("assemble")
    p.add_argument("--requirements", required=True,
                   help="Gate requirements config (beats, timings, required actions)")
    p.add_argument("--assets", required=True,
                   help="JSON mapping of beat id to shot video path")
    p.add_argument("--receipts-dir", required=True,
                   help="Directory of *.receipt.json human review receipts")
    p.add_argument("--audio", required=True, help="Final audio file to mux")
    p.add_argument("--episode-receipt", default=None,
                   help="Optional episode receipt with full_playback and "
                        "emotional_listen; without it the output is labeled a "
                        "review candidate, never a finished episode")
    p.add_argument("--out", required=True)

    p = sub.add_parser("verify-episode", help="Check exact existing candidate bytes without re-encoding")
    p.add_argument("--video", required=True)
    p.add_argument("--episode-receipt", required=True)

    p = sub.add_parser("validate-continuity",
                       help="Validate a continuity contract: reference bank coverage, "
                            "per-shot state, cut transitions and action phases. "
                            "Contract completeness only, not media acceptance.")
    p.add_argument("--contract", required=True)
    p.add_argument("--out", default=None)

    p = sub.add_parser("plan-route",
                       help="Check which generation routes may carry a shot's hard "
                            "requirements, given project evidence of route failures.")
    p.add_argument("--requirements", required=True,
                   help="JSON file of requirement flags (locked_camera, exact_wardrobe, "
                        "off_lens_eyelines, scripted_action, audio_led_performance, "
                        "masked_or_structured_edit) plus optional seconds/references")
    p.add_argument("--out", default=None)

    p = sub.add_parser("review-receipt")
    p.add_argument("--asset", required=True)
    p.add_argument("--beat", required=True)
    p.add_argument("--requirements", default=None, help="Required for shot receipts; binds exact beat requirements")
    p.add_argument("--out", required=True)

    args = parser.parse_args()
    if args.command == "assemble":
        import fcntl
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lock_handle = output_path.with_suffix(output_path.suffix + ".lock").open("a")
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another assembly holds this output lock") from error

    if args.command == "validate-script":
        issues = validate_script_file(args.script)
        print(json.dumps([issue.__dict__ for issue in issues], indent=2))
        if any(issue.severity == "error" for issue in issues):
            raise SystemExit(1)
        return

    if args.command == "plan-stills":
        plan = build_candidate_plan(args.shot_plan, args.target)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=2))
        manifest = build_manifest([args.shot_plan, args.out], {"stage": "still_candidate_plan", "paid_generation": False})
        write_manifest(str(out) + ".manifest.json", manifest)
        print(json.dumps({"out": str(out), "candidate_count": plan["candidate_count"], "required_states": plan["required_states"]}, indent=2))
        return

    if args.command == "estimate-still-cost":
        print(json.dumps(estimate_cost(args.target, args.model), indent=2))
        return

    if args.command == "qa-video":
        windows = None
        if args.dialogue_windows:
            windows = json.loads(Path(args.dialogue_windows).read_text())
        report = full_qa_report(args.video, dialogue_windows=windows)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        defects = report["mechanical"]["defects"]
        print(json.dumps({"out": str(out), "video": args.video,
                          "mechanical_pass": report["mechanical_pass"],
                          "defect_count": len(defects)}, indent=2))
        if defects:
            raise SystemExit(1)
        return

    if args.command == "gate-check":
        requirements = json.loads(Path(args.requirements).read_text())
        assets = json.loads(Path(args.assets).read_text())
        receipts = load_receipts(args.receipts_dir) if args.receipts_dir else {}
        result = gate_check(requirements, assets, receipts)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=2))
        print(json.dumps({"all_approved": result["all_approved"],
                          "counts": result["counts"],
                          "beats": [{"beat": b["beat"], "status": b["status"],
                                     "reasons": b["reasons"]} for b in result["beats"]]},
                         indent=2))
        if not result["all_approved"]:
            raise SystemExit(1)
        return

    if args.command == "assemble":
        requirements = json.loads(Path(args.requirements).read_text())
        assets = json.loads(Path(args.assets).read_text())
        receipts = load_receipts(args.receipts_dir)

        # Validate before invoking any encoder or touching an existing output.
        from microdrama.assembly_safety import validate_assembly_inputs
        validate_assembly_inputs(requirements, assets, args.audio, args.out)

        # Stage 1: per-beat gate. Any reject or pause stops assembly entirely:
        # no output file is produced (owner rule: missing scripted action is a
        # reject, unestablished quality is a pause - never assemble anyway).
        gate = gate_check(requirements, assets, receipts)
        if not gate["all_approved"]:
            print(json.dumps({"assembled": False, "counts": gate["counts"],
                              "beats": [{"beat": b["beat"], "status": b["status"],
                                         "reasons": b["reasons"]}
                                        for b in gate["beats"]]}, indent=2))
            raise SystemExit(1)

        # Stage 2: concat in beat order and mux the final audio.
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        beats = requirements["beats"]
        listing = out.with_suffix(".concat.txt")
        from microdrama.assembly_safety import ffconcat_entry
        listing.write_text("".join(
            ffconcat_entry(assets[str(b["beat"])]) for b in beats))
        silent_video = out.with_suffix(".video-only.mp4")
        try:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                            "-i", str(listing), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-an", str(silent_video)], check=True)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silent_video),
                            "-i", args.audio, "-map", "0:v", "-map", "1:a",
                            "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)],
                           check=True)
        finally:
            listing.unlink(missing_ok=True)
            silent_video.unlink(missing_ok=True)

        # Stage 3: episode-level mechanical checks on the assembled bytes.
        windows = [w for b in beats for w in b["lines"]]
        mechanical = mechanical_report(out, dialogue_windows=windows)
        if mechanical["defects"]:
            report_path = out.with_suffix(".mechanical-report.json")
            report_path.write_text(json.dumps(mechanical, indent=2))
            out.unlink()  # a defective assembly is not a deliverable
            print(json.dumps({"assembled": False, "stage": "episode_mechanical",
                              "defects": mechanical["defects"],
                              "report": str(report_path)}, indent=2))
            raise SystemExit(1)

        # Stage 4: without an episode review receipt this is a review
        # candidate; with a complete one it may be called final.
        episode_receipt = (json.loads(Path(args.episode_receipt).read_text())
                           if args.episode_receipt else None)
        episode = evaluate_episode(out, episode_receipt, dialogue_windows=windows,
                                   mechanical=mechanical)
        print(json.dumps({"assembled": True, "out": str(out),
                          "episode_status": episode["status"],
                          "reasons": episode["reasons"],
                          "scope": episode["scope"]}, indent=2))
        if episode["status"] != "APPROVED":
            raise SystemExit(2)  # assembled, but only a review candidate
        return

    if args.command == "verify-episode":
        receipt = json.loads(Path(args.episode_receipt).read_text())
        verdict = evaluate_episode(args.video, receipt)
        print(json.dumps(verdict, indent=2))
        if verdict["status"] != "APPROVED":
            raise SystemExit(2)
        return

    if args.command == "validate-continuity":
        doc = json.loads(Path(args.contract).read_text())
        report = validate_continuity_document(doc)
        text = json.dumps(report, indent=2, sort_keys=True)
        if args.out:
            Path(args.out).write_text(text + "\n")
        print(text)
        raise SystemExit(0 if report["status"] == "pass" else 1)

    if args.command == "plan-route":
        requirements = json.loads(Path(args.requirements).read_text())
        report = plan_route(requirements)
        text = json.dumps(report, indent=2, sort_keys=True)
        if args.out:
            Path(args.out).write_text(text + "\n")
        print(text)
        raise SystemExit(0 if report["status"] == "ok" else 1)

    if args.command == "review-receipt":
        req = None
        if args.beat != "episode":
            if not args.requirements:
                raise ValueError("Shot receipts require --requirements")
            reqs = json.loads(Path(args.requirements).read_text())
            from microdrama.reviewgate import validate_requirements
            validate_requirements(reqs)
            req = next(b for b in reqs["beats"] if str(b["beat"]) == args.beat)
        receipt = scaffold_receipt(args.asset, args.beat, req)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2))
        print(json.dumps({"out": str(out),
                          "note": "Receipt scaffolded with asset hash. A named reviewer "
                                  "fills reviewer, reviewed_at and each check after "
                                  "actually watching the asset."}, indent=2))
        return


if __name__ == "__main__":
    main()
