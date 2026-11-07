"""Season archive (FR3): a defined manifest of a season's assets, integrity
checks, a size limit enforced when the archive is READ, and a continuity
pass that checks the next season against the characters, wardrobe and sets
it inherits.

Design rules, all fail-closed:
- The manifest is the definition of the archive: every asset is listed with
  its path, kind, byte size and sha256. Reading verifies all of it.
- The size limit is enforced twice at read time: on the declared sizes in
  the zip central directory BEFORE anything is extracted, and again on the
  ACTUAL decompressed bytes as they stream out, so a lying header cannot
  smuggle more data past the limit. Over-limit reads abort and remove the
  partial extraction.
- Hostile member paths (absolute, '..', drive letters, backslashes) are
  rejected before extraction (zip-slip).
- The continuity pass compares two manifests: every character, wardrobe and
  set asset a season inherits must be present in the next season; missing
  inherited assets lock the gate. Changed bytes are reported, not silently
  accepted.
"""
import hashlib
import json
import os
import shutil
import zipfile
from zipfile import BadZipFile
from pathlib import Path

from forge.gates.common import GateLocked, now_iso

SCHEMA = "dramasaga.season-archive/1"
MANIFEST_NAME = "season_manifest.json"
DEFAULT_LIMIT_BYTES = 1 << 30  # 1 GiB: the report's "one gigabyte" archive claim
MAX_MEMBERS = 100_000
_CHUNK = 1 << 20

ASSET_KINDS = ("characters", "wardrobe", "sets", "audio", "plans", "other")
# Kinds the next season must inherit unchanged-or-deliberately for continuity.
CONTINUITY_KINDS = ("characters", "wardrobe", "sets")


def _sha256_path(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _kind_for(relpath: str) -> str:
    top = relpath.replace("\\", "/").split("/", 1)[0].lower()
    for kind in ASSET_KINDS:
        if top == kind or top.startswith(kind.rstrip("s")):
            return kind
    return "other"


def _check_member_name(name: str) -> None:
    """Reject hostile or meaningless archive member names (zip-slip)."""
    if not name or name.endswith("/"):
        return  # directory entries are allowed and never extracted as files
    n = name.replace("\\", "/")
    if name.startswith(("/", "\\")) or n.startswith("/") or ":" in n.split("/")[0]:
        raise GateLocked(f"hostile archive member path: {name!r}")
    if any(part in ("", "..") for part in n.split("/")):
        raise GateLocked(f"hostile archive member path: {name!r}")


def build_manifest(season_dir, season: str = "") -> dict:
    """Walk a season directory into a manifest. Stable ordering, sha256 and
    byte size per asset, kind from the top-level directory."""
    root = Path(season_dir)
    if not root.is_dir():
        raise GateLocked(f"season directory missing: {season_dir}")
    assets = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel == MANIFEST_NAME:
            continue
        _check_member_name(rel)
        assets.append({"path": rel, "kind": _kind_for(rel),
                       "bytes": path.stat().st_size,
                       "sha256": _sha256_path(path)})
    if not assets:
        raise GateLocked(f"season directory holds no assets: {season_dir}")
    return {"schema": SCHEMA,
            "season": season or root.name,
            "created_at": now_iso(),
            "assets": assets,
            "total_files": len(assets),
            "total_bytes": sum(a["bytes"] for a in assets)}


def write_archive(season_dir, out_path, season: str = "",
                  limit: int = DEFAULT_LIMIT_BYTES) -> str:
    """Zip a season directory with its manifest inside. Refuses to create an
    archive whose own assets already exceed the read limit."""
    manifest = build_manifest(season_dir, season=season)
    if manifest["total_bytes"] > limit:
        raise GateLocked(
            f"season assets are {manifest['total_bytes']} bytes, over the "
            f"{limit}-byte archive limit; split or trim before archiving")
    out_path = str(out_path)
    root = Path(season_dir)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=1))
        for asset in manifest["assets"]:
            zf.write(root / asset["path"], asset["path"])
    return out_path


def _extract_streaming(zf, infos, dest: Path, limit: int) -> int:
    """Extract members while counting ACTUAL decompressed bytes. Aborts at
    the limit even when the central directory lied about sizes."""
    total = 0
    for info in infos:
        _check_member_name(info.filename)
        if info.filename.endswith("/"):
            continue
        target = dest / info.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        try:
            src_cm = zf.open(info)
        except BadZipFile as e:
            raise GateLocked(f"archive member {info.filename!r} is corrupt: {e}")
        with src_cm as src, open(target, "wb") as dst:
            while True:
                try:
                    chunk = src.read(_CHUNK)
                except BadZipFile as e:
                    raise GateLocked(f"archive member {info.filename!r} is corrupt: {e}")
                if not chunk:
                    break
                written += len(chunk)
                total += len(chunk)
                if total > limit:
                    raise GateLocked(
                        f"archive exceeded the {limit}-byte read limit during "
                        f"extraction (member {info.filename!r}); partial output removed")
                dst.write(chunk)
        if written != info.file_size:
            raise GateLocked(
                f"archive member {info.filename!r} declared {info.file_size} "
                f"bytes but yielded {written}; refusing a corrupt archive")
    return total


def read_archive(zip_path, dest_dir, limit: int = DEFAULT_LIMIT_BYTES) -> dict:
    """Read a season archive under the size limit and verify it against its
    manifest. Returns {manifest, bytes, files, dest}. Fails closed: any
    limit breach, hostile path, missing/extra/corrupt asset raises GateLocked
    and no partial extraction is left behind."""
    zip_path = str(zip_path)
    dest = Path(dest_dir)
    if not zipfile.is_zipfile(zip_path):
        raise GateLocked(f"not a zip archive: {zip_path}")
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_MEMBERS:
            raise GateLocked(f"archive has {len(infos)} members, over the {MAX_MEMBERS} cap")
        for info in infos:
            _check_member_name(info.filename)
        declared = sum(i.file_size for i in infos if not i.filename.endswith("/"))
        if declared > limit:
            raise GateLocked(
                f"archive declares {declared} uncompressed bytes, over the "
                f"{limit}-byte limit; not extracted")
        names = {i.filename for i in infos if not i.filename.endswith("/")}
        if MANIFEST_NAME not in names:
            raise GateLocked(f"archive has no {MANIFEST_NAME}; not a season archive")
        try:
            manifest = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise GateLocked(f"manifest is unreadable: {e}")
        if manifest.get("schema") != SCHEMA:
            raise GateLocked(f"manifest schema {manifest.get('schema')!r} != {SCHEMA!r}")
        staged = dest.parent / (dest.name + ".partial")
        if staged.exists():
            shutil.rmtree(staged)
        staged.mkdir(parents=True)
        try:
            actual = _extract_streaming(zf, infos, staged, limit)
        except BaseException:
            shutil.rmtree(staged, ignore_errors=True)
            raise
    errors = _verify_against_manifest(staged, manifest)
    if errors:
        shutil.rmtree(staged, ignore_errors=True)
        raise GateLocked("archive failed integrity checks: " + "; ".join(errors))
    if dest.exists():
        shutil.rmtree(dest)
    os.replace(staged, dest)
    return {"manifest": manifest, "bytes": actual,
            "files": len(manifest["assets"]), "dest": str(dest)}


def _verify_against_manifest(root: Path, manifest: dict):
    """Every manifest asset present with matching size and sha256; no extra
    files on disk. Returns a list of problems (empty = verified)."""
    problems = []
    listed = set()
    for asset in manifest.get("assets", []):
        rel, listed_add = asset.get("path", ""), listed.add
        listed_add(rel)
        p = root / rel
        if not p.is_file():
            problems.append(f"missing asset {rel!r}")
            continue
        if p.stat().st_size != asset.get("bytes"):
            problems.append(f"size mismatch on {rel!r}")
            continue
        if _sha256_path(p) != asset.get("sha256"):
            problems.append(f"sha256 mismatch on {rel!r}")
    extras = [p.relative_to(root).as_posix() for p in root.rglob("*")
              if p.is_file() and p.name != MANIFEST_NAME
              and p.relative_to(root).as_posix() not in listed]
    for rel in extras:
        problems.append(f"unlisted file in archive: {rel!r}")
    if manifest.get("total_files") != len(manifest.get("assets", [])):
        problems.append("manifest total_files disagrees with its asset list")
    return problems


def continuity_report(prev_manifest: dict, next_manifest: dict) -> dict:
    """Check the next season against the characters, wardrobe and sets it
    inherits. Matched by asset path; changed bytes are flagged; missing
    inherited assets make the report not ok."""
    prev_by_path = {a["path"]: a for a in prev_manifest.get("assets", [])}
    next_by_path = {a["path"]: a for a in next_manifest.get("assets", [])}
    missing, changed, kept, added = [], [], [], []
    for path, asset in sorted(prev_by_path.items()):
        if asset.get("kind") not in CONTINUITY_KINDS:
            continue
        nxt = next_by_path.get(path)
        if nxt is None:
            missing.append(path)
        elif nxt.get("sha256") != asset.get("sha256"):
            changed.append(path)
        else:
            kept.append(path)
    for path, asset in sorted(next_by_path.items()):
        if asset.get("kind") in CONTINUITY_KINDS and path not in prev_by_path:
            added.append(path)
    return {"ok": not missing,
            "season_from": prev_manifest.get("season", ""),
            "season_to": next_manifest.get("season", ""),
            "missing_inherited": missing,
            "changed_inherited": changed,
            "kept": kept,
            "added": added,
            "checked_kinds": list(CONTINUITY_KINDS)}


def require_continuity(prev_manifest: dict, next_manifest: dict) -> dict:
    """Gate form of continuity_report: missing inherited characters,
    wardrobe or sets lock the next season until a human resolves them."""
    report = continuity_report(prev_manifest, next_manifest)
    if not report["ok"]:
        raise GateLocked(
            "next season is missing inherited assets: "
            + ", ".join(report["missing_inherited"]))
    return report
