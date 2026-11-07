"""Pipeline stage provenance: a small sidecar (<video>.stages.json) records
which processing stages produced each video, in order. This is the
enforceable form of the caption-ordering contract (LIPSYNC_PLAN):

- lip-sync REFUSES an input whose log shows captions already burned
  (the face-restore pass would smear the text; m17 Kaggle observation);
- caption burning REFUSES an input with a lip-sync pass planned but not
  yet completed (the text would be baked in before the sync runs).

This is provenance our own pipeline writes and checks - NOT automatic
burned-caption detection, which we do not claim anywhere."""
import json
import os
import time

PLANNED = "lipsync_planned"
SYNCED = "lipsync"
CAPTIONS = "captions"


def _sidecar(path):
    return str(path) + ".stages.json"


def stages_of(path) -> list:
    try:
        with open(_sidecar(path)) as f:
            return list(json.load(f).get("stages", []))
    except (OSError, ValueError):
        return []


def record(path, stage, source=None, strict=False) -> bool:
    """Append `stage` to path's log, inheriting the source video's stages.
    Recording SYNCED clears the PLANNED marker. When strict is False an
    unwritable sidecar (e.g. a read-only dataset mount) is skipped and
    reported False instead of raising."""
    stages = stages_of(source) if source is not None else stages_of(path)
    if stage == SYNCED and PLANNED in stages:
        stages.remove(PLANNED)
    if stage not in stages:
        stages.append(stage)
    try:
        with open(_sidecar(path), "w") as f:
            json.dump({"stages": stages, "updated": time.time()}, f)
    except OSError:
        if strict:
            raise
        return False
    return True


def check_clean_for_lipsync(video):
    """Fail closed when the stage log shows captions already burned on this
    input: lip-syncing it would smear the text inside the face box."""
    if CAPTIONS in stages_of(video):
        from forge.gates.common import GateLocked
        raise GateLocked(
            "lip-sync refused: stage log shows captions already burned on "
            f"{video}; lip-sync must run on the clean pre-caption video "
            "(the face-restore pass smears text pixels)")


def check_ready_for_captions(video):
    """Fail closed when a lip-sync pass is planned for this input but not
    recorded complete: captions burned now would be smeared by the pending
    sync, and the sync would then refuse the captioned video."""
    stages = stages_of(video)
    if PLANNED in stages and SYNCED not in stages:
        from forge.gates.common import GateLocked
        raise GateLocked(
            "caption burn refused: a lip-sync pass is planned for "
            f"{video} but not recorded complete; burn captions AFTER "
            "lip-sync (record the completed sync stage first)")


def main(argv=None) -> int:
    """CLI for GPU job scripts: python -m forge.assemble.stage_log VIDEO
    show | record STAGE [--source SRC]"""
    import argparse
    ap = argparse.ArgumentParser(prog="forge.assemble.stage_log")
    ap.add_argument("video")
    sub = ap.add_subparsers(dest="op", required=True)
    sub.add_parser("show")
    rec = sub.add_parser("record")
    rec.add_argument("stage", choices=[PLANNED, SYNCED, CAPTIONS])
    rec.add_argument("--source", default=None)
    args = ap.parse_args(argv)
    if args.op == "show":
        print(json.dumps(stages_of(args.video)))
        return 0
    ok = record(args.video, args.stage, source=args.source, strict=True)
    print(json.dumps({"recorded": ok, "stages": stages_of(args.video)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
