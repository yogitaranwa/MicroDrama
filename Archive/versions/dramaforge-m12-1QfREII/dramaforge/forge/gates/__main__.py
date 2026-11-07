"""CLI: python -m forge.gates <command> <project_dir> ...

  status DIR
  lock-stills DIR label=path [label=path...]
  record-proof DIR VIDEO --shots N --seconds S --locations a[,b]
  signoff-proof DIR REVIEWER
  review DIR EPISODE --shots name:secs[,name:secs...] [--lip-sync-done]
  signoff DIR REVIEWER [--note TEXT]
  deliver DIR EPISODE DEST
  angle-stills DIR PLAN.json
  start-checklist DIR
  check DIR ITEM REVIEWER [--note TEXT]
  checklist DIR
"""
import sys
from forge.gates import (lock_stills, record_proof, signoff_proof,
                         review_episode, signoff, GateLocked)
from forge.gates.deliver import deliver
from forge.gates.common import state_dir, read_json
from forge.gates.angle_stills import angle_coverage, require_angle_stills
from forge.gates.proof_checklist import (start_checklist, check_item,
                                         checklist_status, require_proof_checklist)


def _status(project_dir):
    sd = state_dir(project_dir)
    for name in ("still_lock.json", "scene_proof.json", "proof_checklist.json",
                 "review_report.json",
                 "review_signoff.json", "deliveries.json"):
        rec = read_json(sd / name)
        if rec is None:
            print(f"{name}: MISSING")
        elif name == "still_lock.json":
            print(f"{name}: locked at {rec.get('locked_at')} ({len(rec.get('stills', {}))} stills)")
        elif name == "scene_proof.json":
            print(f"{name}: {rec.get('status')} ({rec.get('n_shots')} shots, {rec.get('seconds')}s)")
        elif name == "review_report.json":
            print(f"{name}: {rec.get('status')} ({len(rec.get('issues', []))} issues)")
        elif name == "review_signoff.json":
            print(f"{name}: signed by {rec.get('reviewer')} at {rec.get('signed_off_at')}")
        elif name == "proof_checklist.json":
            n_open = sum(1 for v in rec.get("items", {}).values() if not v.get("checked"))
            print(f"{name}: {len(rec.get('items', {})) - n_open}/{len(rec.get('items', {}))} items checked")
        else:
            print(f"{name}: {rec.get('last')}")


def main(argv):
    cmd, project_dir = argv[1], argv[2]
    args = argv[3:]
    if cmd == "status":
        _status(project_dir)
    elif cmd == "lock-stills":
        rec = lock_stills(project_dir, dict(a.split("=", 1) for a in args))
        print(f"locked {len(rec['stills'])} stills")
    elif cmd == "record-proof":
        kw = dict(zip(args[1::2], args[2::2]))
        rec = record_proof(project_dir, args[0], int(kw["--shots"]), float(kw["--seconds"]),
                           [x for x in kw.get("--locations", "").split(",") if x])
        print(f"proof recorded: {rec['status']}")
    elif cmd == "signoff-proof":
        rec = signoff_proof(project_dir, args[0])
        print(f"proof approved by {rec['reviewer']}")
    elif cmd == "review":
        kw = dict(zip(args[1::2], args[2::2]))
        shots = [(n, float(s)) for n, s in (x.split(":") for x in kw["--shots"].split(","))]
        rep = review_episode(project_dir, args[0], shots,
                             lip_sync_done="--lip-sync-done" in args)
        print(f"review: {rep['status']}" + (f" issues={rep['issues']}" if rep["issues"] else ""))
    elif cmd == "signoff":
        note = args[args.index("--note") + 1] if "--note" in args else ""
        rec = signoff(project_dir, args[0], note=note)
        print(f"signed off by {rec['reviewer']}")
    elif cmd == "deliver":
        print("delivered:", deliver(project_dir, args[0], args[1]))
    elif cmd == "angle-stills":
        import json
        plan = json.load(open(args[0]))
        cov = angle_coverage(project_dir, plan)
        for l in cov["missing"]:
            print(f"missing: {l}")
        require_angle_stills(project_dir, plan)
        print(f"angle stills cover the plan ({len(cov['needed'])} stills)")
    elif cmd == "start-checklist":
        rec = start_checklist(project_dir)
        print(f"checklist started ({len(rec['items'])} items)")
    elif cmd == "check":
        note = args[args.index("--note") + 1] if "--note" in args else ""
        rec = check_item(project_dir, args[0], args[1], note=note)
        print(f"checked {args[0]} by {rec['items'][args[0]]['reviewer']}")
    elif cmd == "checklist":
        st = checklist_status(project_dir)
        for k, v in st["items"].items():
            mark = "x" if v.get("checked") else " "
            print(f"[{mark}] {k}: {v.get('description', '')}")
        require_proof_checklist(project_dir)
        print("checklist complete")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except GateLocked as e:
        sys.exit(f"GATE LOCKED: {e}")
