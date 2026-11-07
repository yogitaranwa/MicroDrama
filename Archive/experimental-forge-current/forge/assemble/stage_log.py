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


def provenance(path) -> str:
    """'recorded' when a readable stage log exists for this video, 'corrupt'
    when the sidecar exists but cannot be parsed, else 'unknown'. Neither
    unknown nor corrupt is a synonym for clean: callers must report them,
    never silently treat a foreign input as verified pre-caption."""
    import os as _os
    if not _os.path.exists(_sidecar(path)):
        return "unknown"
    try:
        with open(_sidecar(path)) as f:
            json.load(f)
    except (OSError, ValueError):
        return "corrupt"
    return "recorded"


def record(path, stage, source=None, sources=None, strict=False) -> bool:
    """Append `stage` to path's log, inheriting stages from the source
    video(s) (ordered union, so an assembled video carries every shot's
    provenance). Recording SYNCED clears the PLANNED marker. The log notes
    whether the source provenance was recorded or unknown. When strict is
    False an unwritable sidecar (e.g. a read-only dataset mount) is
    skipped and reported False instead of raising."""
    origins = list(sources) if sources is not None else ([source] if source is not None else [])
    if origins:
        stages = []
        for o in origins:
            for s in stages_of(o):
                if s not in stages:
                    stages.append(s)
        src_prov = ("recorded" if any(provenance(o) == "recorded" for o in origins)
                    else "unknown")
    else:
        stages = stages_of(path)
        src_prov = None
    if stage == SYNCED and PLANNED in stages:
        stages.remove(PLANNED)
    if stage not in stages:
        stages.append(stage)
    payload = {"stages": stages, "updated": time.time()}
    if src_prov is not None:
        payload["source_provenance"] = src_prov
    try:
        with open(_sidecar(path), "w") as f:
            json.dump(payload, f)
    except OSError:
        if strict:
            raise
        return False
    return True


def copy_with(src, dst) -> str:
    """Copy a video together with its stage log so provenance travels from
    the GPU host / download step into assembly. Returns the provenance
    that traveled: 'recorded' or 'unknown' (never upgrades unknown to
    clean)."""
    import shutil
    prov = provenance(src)
    shutil.copy2(src, dst)
    if prov == "recorded":
        shutil.copy2(_sidecar(src), _sidecar(dst))
    return prov


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
