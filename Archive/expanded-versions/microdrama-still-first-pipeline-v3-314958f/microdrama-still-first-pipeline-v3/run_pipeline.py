#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from microdrama.manifest import build_manifest, write_manifest
from microdrama.scriptqa import validate_script_file
from microdrama.stills import build_candidate_plan, estimate_cost
from microdrama.visualqa import qa_report


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

    args = parser.parse_args()

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
        report = qa_report(args.video)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(json.dumps({"out": str(out), "video": args.video}, indent=2))
        return


if __name__ == "__main__":
    main()
