"""CLI: python -m forge.gates <command> <project_dir> ...

  status DIR
  lock-stills DIR label=path [label=path...]
  record-proof DIR VIDEO --shots N --seconds S --locations a[,b]
  signoff-proof DIR REVIEWER
  review DIR EPISODE --shots name:secs[,name:secs...] [--lip-sync-done]
  signoff DIR REVIEWER [--note TEXT]
  deliver DIR EPISODE DEST
"""
import sys
from forge.gates import (lock_stills, record_proof, signoff_proof,
                         review_episode, signoff, GateLocked)
from forge.gates.deliver import deliver
from forge.gates.common import state_dir, read_json


def _status(project_dir):
    sd = state_dir(project_dir)
    for name in ("still_lock.json", "scene_proof.json", "review_report.json",
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
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except GateLocked as e:
        sys.exit(f"GATE LOCKED: {e}")
