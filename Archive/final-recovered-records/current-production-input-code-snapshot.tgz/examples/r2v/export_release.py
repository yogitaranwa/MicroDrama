"""Release-path consolidation with a freshness gate. Local only - no network, no spend.

Two export classes, never conflated:

  --source-zip OUT.zip   code/docs/manifests for REVIEW. NOT production output: no media,
                         no run dirs, no receipts, no probe artifacts; every included text
                         file is hygiene-scanned (secrets, personal emails); a root NOTICE
                         file states exactly what the archive is. Never blocked by unpaid
                         generation - it contains no generation at all.

  --final-media OUTDIR   user-visible DELIVERABLE. Refuses unless every episode in scope
                         has a fresh verified chain: per-shot assemble records in state
                         'assembled' with a live input-fingerprint match, lipsync linkage
                         intact for the record's mode, and an 'edited' episode record whose
                         episode fingerprint matches the CURRENT chain with an intact file.
                         Preview renders and .stale- backups are never copied. Emits
                         MANIFEST.json with hashes + provenance next to the media.

Any refusal exits 2 with precise reasons. This gate is the mechanical readiness check
before anything leaves the workspace; it does not judge media QUALITY (human listen/watch
decisions stay upstream in the stage receipts).
"""
import argparse, json, re, shutil, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import stages as STAGES
import production_runner as PR

MEDIA_EXT = {".mp4", ".mov", ".mkv", ".wav", ".mp3", ".aac", ".m4a", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
EXCLUDE_DIRNAMES = {".git", "__pycache__", "node_modules"}
EXCLUDE_DIR_RE = re.compile(r"^(production|probe)-")          # run dirs hold receipts + media
EXCLUDE_NAME_RE = re.compile(r"(receipts?|\.stale-|(-|_)preview\.|~$|\.zip$)")  # no receipts, backups, previews, or nested archives
TEXT_EXT = {".py", ".md", ".txt", ".json", ".sh", ".ps1", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".csv"}
SECRET_RE = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|xox[baprs]-[0-9A-Za-z-]{10,}|/\."
                       + "vault/" + "|" + "magic-hour" + "-api-key"
                       + ")")  # secrets, tokens, vault paths/key-item names (literals split so this file passes its own scan)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_ALLOW = re.compile(r"(@example\.(com|org|net)\b|@test\.invalid\b|wamid\.)")

SOURCE_NOTICE = """====================================================================
SOURCE / REVIEW EXPORT - THIS IS NOT PRODUCTION OUTPUT
====================================================================
This archive contains source code, manifests and documentation only.
It contains NO production media and NO finished episode video.
Final deliverable media is exported separately and only after every
episode's chain verifies fresh (assemble fingerprints + lipsync
linkage + episode fingerprint) at export time. Do not treat anything
in this archive as viewable product.
====================================================================
"""


def _die(msg, code=2):
    print("REFUSED:", msg)
    sys.exit(code)


def _intact(rec):
    p = rec.get("artifact") if rec else None
    return bool(p) and Path(p).exists() and STAGES.sha256_file(p) == rec.get("sha256")


def _bad_path(rec):
    n = Path(rec.get("artifact", "")).name
    return ".stale-" in n or "-preview" in n


def final_media(outdir, run_dir, manifest_path, episodes):
    receipts = json.loads((run_dir / "run-receipts.json").read_text())
    manifest = json.loads(manifest_path.read_text()) if manifest_path else PR.MANIFEST
    shots = [s for s in manifest["shots"] if not episodes or s["episode"] in episodes]
    if not shots:
        _die("no shots in scope")
    eps = {}
    for s in shots:
        eps.setdefault(s["episode"], []).append(s)
    problems, files = [], {}
    for ep, ss in sorted(eps.items()):
        ss.sort(key=lambda s: s["shot"])
        for s in ss:
            tag = "%s s%02d" % (s["episode"], s["shot"])
            arec = STAGES.get_artifact(receipts, s["episode"], s["shot"], "assemble")
            if not arec or arec.get("state") != "assembled":
                problems.append("%s: no current assemble record (state %s)" % (tag, arec and arec.get("state")))
                continue
            if arec.get("inputs_sha256") != PR._assemble_inputs_fp(receipts, s):
                problems.append("%s: assemble inputs stale (video/FX/take/offset changed since assemble)" % tag)
            if not _intact(arec):
                problems.append("%s: assemble artifact missing or drifted from recorded hash" % tag)
            if _bad_path(arec):
                problems.append("%s: assemble artifact path is a preview/backup name - never export those" % tag)
            lrec = STAGES.get_artifact(receipts, s["episode"], s["shot"], "lipsync")
            if not lrec or lrec.get("state") != "lipsync_done":
                problems.append("%s: lipsync not done (state %s)" % (tag, lrec and lrec.get("state")))
            else:
                if lrec.get("mode") == "lipsync" and lrec.get("upstream_sha256") != arec.get("sha256"):
                    problems.append("%s: lipsync output predates current assemble" % tag)
                if lrec.get("mode") == "soundtrack" and lrec.get("artifact") != arec.get("artifact"):
                    problems.append("%s: soundtrack pass-through names the wrong assemble artifact" % tag)
                if not _intact(lrec):
                    problems.append("%s: lipsync artifact missing or drifted" % tag)
        erec = STAGES.get_artifact(receipts, ep, 0, "edit")
        if not erec or erec.get("state") != "edited":
            problems.append("%s: episode not edited (state %s)" % (ep, erec and erec.get("state")))
            continue
        if erec.get("inputs_sha256") != PR._episode_inputs_fp(receipts, ss):
            problems.append("%s: episode fingerprint mismatch - chain changed since edit; re-run --stage edit" % ep)
        if not _intact(erec):
            problems.append("%s: episode file missing or drifted from recorded hash" % ep)
        if _bad_path(erec):
            problems.append("%s: episode path is a preview/backup name - never export those" % ep)
        files[ep] = erec
    if problems:
        for p in problems:
            print("STALE:", p)
        _die("final-media export blocked: %d freshness problem(s). Re-run --stage assemble/lipsync/edit "
             "until the chain verifies, or drop the episode from scope. Stale output is never deliverable." % len(problems))
    outdir.mkdir(parents=True, exist_ok=True)
    manifest_out = {"exported_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "class": "final-media", "freshness_verified_at_export": True, "episodes": []}
    for ep, erec in sorted(files.items()):
        dst = outdir / Path(erec["artifact"]).name
        shutil.copy2(erec["artifact"], dst)
        manifest_out["episodes"].append({
            "episode": ep, "file": dst.name, "sha256": STAGES.sha256_file(dst),
            "shots": [s["shot"] for s in eps[ep]],
            "episode_inputs_sha256": erec["inputs_sha256"],
            "duration_s": PR._duration_s(dst)})
    (outdir / "MANIFEST.json").write_text(json.dumps(manifest_out, indent=2))
    print("final-media export OK: %d episode(s) -> %s (fresh chain verified at export time)" % (len(files), outdir))


def source_zip(outzip, include_root):
    include_root = include_root.resolve()
    if not include_root.is_dir():
        _die("include root not a directory: %s" % include_root)
    entries, offenders = [], []
    for p in sorted(include_root.rglob("*")):
        rel = p.relative_to(include_root)
        if any(part in EXCLUDE_DIRNAMES or EXCLUDE_DIR_RE.match(part) for part in rel.parts):
            continue
        if p.is_dir():
            continue
        if p.suffix.lower() in MEDIA_EXT or EXCLUDE_NAME_RE.search(p.name):
            continue
        entries.append((rel, p))
        if p.suffix.lower() in TEXT_EXT:
            try:
                text = p.read_text(errors="replace")
            except OSError:
                continue
            if SECRET_RE.search(text):
                offenders.append("%s: secret-like content (private key / cloud token)" % rel)
            for m in EMAIL_RE.finditer(text):
                if not EMAIL_ALLOW.search(m.group(0)):
                    offenders.append("%s: email address %r" % (rel, m.group(0)))
    if offenders:
        for o in offenders[:20]:
            print("HYGIENE:", o)
        _die("source zip blocked: %d hygiene finding(s) - no personal emails/secrets in exports" % len(offenders))
    if not entries:
        _die("nothing to include")
    outzip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(outzip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("EXPORT-READER-NOTICE.txt", SOURCE_NOTICE)
        for rel, p in entries:
            z.write(p, str(rel))
    print("source zip OK: %d files -> %s (REVIEW ONLY - not production output, no media, hygiene-scanned)"
          % (len(entries), outzip))


def main(argv=None):
    ap = argparse.ArgumentParser(description="gated release consolidation (local, free)")
    ap.add_argument("--source-zip", default="", help="write a REVIEW source archive (not production output)")
    ap.add_argument("--include-root", default=str(ROOT.parents[1]), help="tree to include in --source-zip (default: repo root)")
    ap.add_argument("--final-media", default="", help="write deliverable episodes to this directory (freshness-gated)")
    ap.add_argument("--run-dir", default=str(PR.RUN_DIR), help="run dir holding run-receipts.json")
    ap.add_argument("--manifest-json", default="", help="override manifest (default: production manifest)")
    ap.add_argument("--episodes", default="", help="comma-separated episode ids to export (default: all in manifest)")
    args = ap.parse_args(argv)
    if not args.source_zip and not args.final_media:
        _die("choose --source-zip (review) or --final-media (deliverable) - they are different things")
    if args.source_zip:
        source_zip(Path(args.source_zip), Path(args.include_root))
    if args.final_media:
        eps = [e for e in args.episodes.split(",") if e]
        final_media(Path(args.final_media), Path(args.run_dir),
                    Path(args.manifest_json) if args.manifest_json else None, eps)


if __name__ == "__main__":
    main()
