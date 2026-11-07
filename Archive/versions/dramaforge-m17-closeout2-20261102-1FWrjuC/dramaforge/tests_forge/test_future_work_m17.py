"""m17: the report's Future Work items, implemented and tested.

1. season archive: manifest, integrity, enforced read-time size limit,
   continuity pass (forge/season_archive.py)
2. form-based intake bound to the planning layer (forge/intake.py)
3. non-spending preflight + one bounded quality test (forge/preflight.py)
4. full-speed review gate (forge/gates/fullspeed.py)
5. lip-sync face policy: profile + multi-face routing (forge/assemble/face_policy.py)
6. vertical 9:16 reframe of existing outputs, no spend (forge/assemble/vertical.py)
7. viewer reception records for pace/music (forge/reception.py)
"""
import json
import os
import subprocess
import zipfile

import numpy as np
import pytest

from forge.gates.common import GateLocked, state_dir
from forge.gates.review import review_episode, signoff
from forge.gates.deliver import deliver
from forge.gates.fullspeed import record_fullspeed_review, require_fullspeed_review


# --- 1. season archive ------------------------------------------------------

from forge.season_archive import (build_manifest, write_archive, read_archive,
                                  continuity_report, require_continuity,
                                  MANIFEST_NAME, DEFAULT_LIMIT_BYTES)


def _season(root, files):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    return root


def test_archive_roundtrip_and_manifest(tmp_path):
    src = _season(tmp_path / "s1", {
        "characters/draconia.png": b"draco-still",
        "wardrobe/draconia_ball.png": b"gown",
        "sets/great_hall.png": b"hall",
        "plans/e01_plan.json": b"[]",
    })
    arc = write_archive(src, tmp_path / "s1.zip", season="S1")
    out = read_archive(arc, tmp_path / "unpacked")
    assert out["files"] == 4
    assert (tmp_path / "unpacked" / "characters/draconia.png").read_bytes() == b"draco-still"
    assert out["manifest"]["total_bytes"] == sum(map(len, [b"draco-still", b"gown", b"hall", b"[]"]))


def test_archive_detects_tampered_member(tmp_path):
    src = _season(tmp_path / "s1", {"characters/a.png": b"original-bytes"})
    arc = write_archive(src, tmp_path / "s1.zip")
    # rebuild the zip with changed bytes but the same manifest
    with zipfile.ZipFile(arc) as zf:
        manifest = zf.read(MANIFEST_NAME)
    with zipfile.ZipFile(arc, "w") as zf:
        zf.writestr(MANIFEST_NAME, manifest)
        zf.writestr("characters/a.png", b"changed-bytes!")
    with pytest.raises(GateLocked, match="integrity"):
        read_archive(arc, tmp_path / "unpacked")
    assert not (tmp_path / "unpacked").exists()


def test_archive_rejects_zipslip_and_extra_files(tmp_path):
    src = _season(tmp_path / "s1", {"characters/a.png": b"x"})
    arc = write_archive(src, tmp_path / "s1.zip")
    with zipfile.ZipFile(arc) as zf:
        manifest = zf.read(MANIFEST_NAME)
        member = zf.read("characters/a.png")
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr(MANIFEST_NAME, manifest)
        zf.writestr("characters/a.png", member)
        zf.writestr("../escape.txt", b"pwned")
    with pytest.raises(GateLocked, match="hostile"):
        read_archive(evil, tmp_path / "unpacked")
    assert not (tmp_path.parent / "escape.txt").exists()


def test_archive_declared_size_limit_refused_before_extract(tmp_path):
    big = tmp_path / "big.zip"
    with zipfile.ZipFile(big, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps({"schema": "dramasaga.season-archive/1",
                                               "assets": [], "total_files": 0}))
        zf.writestr("payload.bin", b"\0" * (2 << 20))  # 2 MiB declared
    with pytest.raises(GateLocked, match="declares"):
        read_archive(big, tmp_path / "unpacked", limit=1 << 20)
    assert not (tmp_path / "unpacked.partial").exists()


def test_archive_actual_stream_limit_refused_mid_extract(tmp_path):
    """A header that lies about the uncompressed size is caught by the
    streaming byte count: the archive declares 64 bytes but really
    decompresses to 3 MiB."""
    import struct
    lying = tmp_path / "lying.zip"
    real = b"\xff" * (3 << 20)  # 3 MiB actual, compresses a little
    with zipfile.ZipFile(lying, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps({"schema": "dramasaga.season-archive/1",
                                               "assets": [], "total_files": 0}))
        zf.writestr("payload.bin", real)
    with zipfile.ZipFile(lying) as zf:
        info = zf.getinfo("payload.bin")
        local_off = info.header_offset
    data = bytearray(lying.read_bytes())
    # local header: uncompressed size at +22; central header: at cd+24
    data[local_off + 22:local_off + 26] = struct.pack("<I", 64)
    eocd = data.rfind(b"PK\x05\x06")
    cd_off = struct.unpack("<I", data[eocd + 16:eocd + 20])[0]
    pos = cd_off
    while data[pos:pos + 4] == b"PK\x01\x02":
        namelen = struct.unpack("<H", data[pos + 28:pos + 30])[0]
        name = bytes(data[pos + 46:pos + 46 + namelen]).decode()
        if name == "payload.bin":
            data[pos + 24:pos + 28] = struct.pack("<I", 64)
        extralen = struct.unpack("<H", data[pos + 30:pos + 32])[0]
        commentlen = struct.unpack("<H", data[pos + 32:pos + 34])[0]
        pos += 46 + namelen + extralen + commentlen
    lying.write_bytes(bytes(data))
    with pytest.raises(GateLocked, match="corrupt|unreadable|limit"):
        read_archive(lying, tmp_path / "unpacked", limit=1 << 20)
    assert not (tmp_path / "unpacked").exists()
    assert not (tmp_path / "unpacked.partial").exists()


def test_archive_stream_counter_aborts_mid_extract(tmp_path):
    """The streaming byte counter itself: a member is read chunk by chunk and
    the read aborts the moment actual bytes cross the limit. (CPython's
    zipfile already caps output at the declared size, so this guard is what
    protects readers that do not; it is exercised directly here.)"""
    import io
    from forge.season_archive import _extract_streaming
    real = b"\xff" * (3 << 20)
    info = zipfile.ZipInfo("payload.bin")
    info.file_size = len(real)

    class FakeZip:
        def open(self, i):
            return io.BytesIO(real)

    with pytest.raises(GateLocked, match="exceeded"):
        _extract_streaming(FakeZip(), [info], tmp_path / "dest", limit=1 << 20)


def test_archive_one_gib_boundary_streamed(tmp_path):
    """The claimed one-gigabyte archive, exercised for real at the exact
    boundary: the reader streams and verifies a full 1 GiB of decompressed
    payload plus manifest (declared total == limit: accepted), and refuses
    one byte over. Member content is highly compressible zeros, so the zip
    on disk stays small; the bytes counted and hashed are the actual
    decompressed stream."""
    import hashlib
    gib = DEFAULT_LIMIT_BYTES
    manifest = {"schema": "dramasaga.season-archive/1", "season": "S1",
                "created_at": "2026-11-02T00:00:00+0530",
                "assets": [{"path": "assets/gib.bin", "kind": "other",
                            "bytes": 0, "sha256": ""}],
                "total_files": 1, "total_bytes": 0}
    zeros = None  # written in chunks, not held in memory

    def write_arc(path, payload):
        manifest["assets"][0]["bytes"] = payload
        h = hashlib.sha256()
        chunk = b"\0" * (16 << 20)
        full, rem = divmod(payload, len(chunk))
        for _ in range(full):
            h.update(chunk)
        h.update(chunk[:rem])
        manifest["assets"][0]["sha256"] = h.hexdigest()
        manifest["total_bytes"] = payload
        encoded = json.dumps(manifest).encode()
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(MANIFEST_NAME, encoded)
            with zf.open(zipfile.ZipInfo("assets/gib.bin"), "w", force_zip64=True) as fh:
                for _ in range(full):
                    fh.write(chunk)
                fh.write(chunk[:rem])
        return len(encoded)

    # measure the manifest length at the final digit widths (10-digit sizes)
    over = tmp_path / "over.zip"
    mlen = write_arc(over, gib)  # declared total = limit + manifest > limit
    with pytest.raises(GateLocked, match="over the"):
        read_archive(over, tmp_path / "over-out", limit=gib)
    assert not (tmp_path / "over-out").exists()
    payload = gib - mlen
    arc = tmp_path / "gib.zip"
    mlen2 = write_arc(arc, payload)  # declared total is exactly the limit
    assert mlen2 == mlen  # same digit widths, stable boundary math
    out = read_archive(arc, tmp_path / "ok", limit=gib)
    assert out["bytes"] == gib


def test_archive_missing_manifest_and_schema(tmp_path):
    plain = tmp_path / "plain.zip"
    with zipfile.ZipFile(plain, "w") as zf:
        zf.writestr("a.txt", b"hi")
    with pytest.raises(GateLocked, match="season_manifest"):
        read_archive(plain, tmp_path / "x")
    with zipfile.ZipFile(plain, "a") as zf:
        zf.writestr(MANIFEST_NAME, json.dumps({"schema": "other/9"}))
    with pytest.raises(GateLocked, match="schema"):
        read_archive(plain, tmp_path / "x")


def test_continuity_pass(tmp_path):
    prev = build_manifest(_season(tmp_path / "s1", {
        "characters/draconia.png": b"a", "characters/harry.png": b"b",
        "wardrobe/gown.png": b"c", "sets/hall.png": b"d", "plans/p.json": b"e"}), season="S1")
    nxt_ok = build_manifest(_season(tmp_path / "s2", {
        "characters/draconia.png": b"a", "characters/harry.png": b"b",
        "wardrobe/gown.png": b"c", "sets/hall.png": b"d",
        "characters/pansy.png": b"new"}), season="S2")
    rep = require_continuity(prev, nxt_ok)
    assert rep["ok"] and rep["added"] == ["characters/pansy.png"]
    nxt_bad = build_manifest(_season(tmp_path / "s2b", {
        "characters/harry.png": b"b", "wardrobe/gown.png": b"c2",
        "sets/hall.png": b"d"}), season="S2")
    rep = continuity_report(prev, nxt_bad)
    assert not rep["ok"]
    assert rep["missing_inherited"] == ["characters/draconia.png"]
    assert rep["changed_inherited"] == ["wardrobe/gown.png"]
    with pytest.raises(GateLocked, match="missing inherited"):
        require_continuity(prev, nxt_bad)


# --- 2. form-based intake ----------------------------------------------------

from forge.intake import (IntakeError, validate_form, brief_text, visual_bible,
                          reference_image_plan, bind_to_planning,
                          MAX_DESCRIPTION_CHARS)


def _form(tmp_path, **over):
    img = tmp_path / "draco.png"
    img.write_bytes(b"\x89PNG fake")
    form = {"genre": "romantasy rivals-to-lovers", "num_characters": 2,
            "description": "Two rivals at a ball trade accusations and fall for each other.",
            "characters": [
                {"name": "Harry", "description": "reserved, dry humour",
                 "reference": {"mode": "upload", "path": str(img)}},
                {"name": "Draconia", "description": "proud, expressive",
                 "reference": {"mode": "generate", "prompt": "photoreal blonde Slytherin"}},
            ]}
    form.update(over)
    return form


def test_intake_valid_form_binds(tmp_path):
    binding = bind_to_planning(_form(tmp_path), tmp_path)
    assert "romantasy" in binding["outline_prompt"]
    assert "Harry" in binding["outline_prompt"] and "Draconia" in binding["outline_prompt"]
    assert binding["visual_bible"]["characters"]["Draconia"] == "proud, expressive"
    assert binding["reference_images"][1]["mode"] == "generate"
    saved = json.loads((state_dir(tmp_path) / "intake.json").read_text())
    assert saved["form"]["num_characters"] == 2


def test_intake_description_limit_enforced(tmp_path):
    ok = _form(tmp_path, description="x" * MAX_DESCRIPTION_CHARS)
    assert validate_form(ok)["description"] == "x" * MAX_DESCRIPTION_CHARS
    with pytest.raises(IntakeError, match="limit"):
        validate_form(_form(tmp_path, description="x" * (MAX_DESCRIPTION_CHARS + 1)))


def test_intake_rejects_bad_forms(tmp_path):
    with pytest.raises(IntakeError, match="genre"):
        validate_form(_form(tmp_path, genre="  "))
    with pytest.raises(IntakeError, match="whole number"):
        validate_form(_form(tmp_path, num_characters=2.5))
    with pytest.raises(IntakeError, match="1..8"):
        validate_form(_form(tmp_path, num_characters=0))
    with pytest.raises(IntakeError, match="character entries"):
        validate_form(_form(tmp_path, characters=_form(tmp_path)["characters"][:1]))
    with pytest.raises(IntakeError, match="duplicate"):
        dup = _form(tmp_path)
        dup["characters"][1]["name"] = "harry"
        validate_form(dup)
    with pytest.raises(IntakeError, match="missing or empty"):
        validate_form(_form(tmp_path, characters=[
            {"name": "A", "reference": {"mode": "upload", "path": str(tmp_path / "none.png")}},
            {"name": "B", "reference": {"mode": "generate"}},
        ]))
    with pytest.raises(IntakeError, match="not an image"):
        bad = tmp_path / "notes.txt"
        bad.write_text("hi")
        validate_form(_form(tmp_path, characters=[
            {"name": "A", "reference": {"mode": "upload", "path": str(bad)}},
            {"name": "B", "reference": {"mode": "generate"}},
        ]))


# --- 3. preflight + bounded quality check ------------------------------------

from forge.preflight import preflight, bounded_quality_check, PREFLIGHT_NAME


def _project_with_plan(tmp_path):
    plan = [{"plan_n": 1, "src_shot": 1, "kind": "dialogue", "speaker": "Draconia",
             "camera": "close-up", "location": "great hall", "action": "turns",
             "line": {"speaker": "Draconia", "text": "Line one."}, "seconds": 6}]
    out = tmp_path / "out"
    out.mkdir()
    (out / "e01_plan.json").write_text(json.dumps(plan))
    return tmp_path


def test_preflight_reports_without_spending(tmp_path):
    proj = _project_with_plan(tmp_path)
    ledger = state_dir(proj) / "ledger.json"
    ledger.write_text(json.dumps({"approved": 100, "spent": 10}))
    rep = preflight(proj, route_name="veo3.1-lite", resolution="720p", audio=True)
    assert rep["n_jobs"] == 1 and rep["estimate_credits"] > 0
    assert not rep["ok"]  # stills are not locked
    assert any("stills" in i for i in rep["issues"])
    assert json.loads(ledger.read_text()) == {"approved": 100, "spent": 10}  # untouched
    saved = json.loads((state_dir(proj) / PREFLIGHT_NAME).read_text())
    assert saved["estimate_credits"] == rep["estimate_credits"]


def test_preflight_budget_and_route_fail_closed(tmp_path):
    proj = _project_with_plan(tmp_path)
    (state_dir(proj) / "ledger.json").write_text(json.dumps({"approved": 0, "spent": 0}))
    rep = preflight(proj)
    assert any("approved budget" in i for i in rep["issues"])
    with pytest.raises(GateLocked, match="unknown model route"):
        preflight(proj, route_name="no-such-model")


def _make_episode(path, seconds=4, with_audio=True, fps=10, size=(160, 90)):
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size={size[0]}x{size[1]}:rate={fps}"]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(path)]
    subprocess.run(cmd, check=True)
    return str(path)


def test_bounded_quality_check_runs_free(tmp_path):
    ep = _make_episode(tmp_path / "ep.mp4")
    rep = bounded_quality_check(ep)
    assert rep["ok"] and rep["seconds"] > 3
    assert rep["audio_streams"] == 1 and not rep["vertical"]


def test_bounded_quality_check_refuses_long_files(tmp_path):
    ep = _make_episode(tmp_path / "ep.mp4")
    with pytest.raises(GateLocked, match="bounded"):
        bounded_quality_check(ep, max_seconds=2)


# --- 4. full-speed review gate ------------------------------------------------

def _reviewed_episode(tmp_path):
    ep = tmp_path / "ep.mp4"
    ep.write_bytes(b"episode-bytes")
    review_episode(tmp_path, str(ep), [("s1", 10.0)], lip_sync_done=True)
    signoff(tmp_path, "reviewer-a")
    return str(ep)


def test_fullspeed_record_and_require(tmp_path):
    ep = _reviewed_episode(tmp_path)
    rec = record_fullspeed_review(
        tmp_path, "project-owner", watched_full_speed=True, listened=True,
        observations=[{"t": 12.0, "kind": "sync", "note": "mouth soft on one line"}],
        verdict="issues", note="one line to retake")
    assert rec["verdict"] == "issues"
    with pytest.raises(GateLocked, match="verdict"):
        require_fullspeed_review(tmp_path, ep)
    with pytest.raises(GateLocked):
        deliver(tmp_path, ep, tmp_path / "out")


def test_fullspeed_requires_real_watch_and_listen(tmp_path):
    _reviewed_episode(tmp_path)
    with pytest.raises(GateLocked, match="full speed"):
        record_fullspeed_review(tmp_path, "r", watched_full_speed=False, listened=True,
                                verdict="approved")
    with pytest.raises(GateLocked, match="listened"):
        record_fullspeed_review(tmp_path, "r", watched_full_speed=True, listened=False,
                                verdict="approved")
    with pytest.raises(GateLocked, match="reviewer"):
        record_fullspeed_review(tmp_path, " ", watched_full_speed=True, listened=True,
                                verdict="approved")


def test_fullspeed_invalidated_by_new_cut(tmp_path):
    ep = _reviewed_episode(tmp_path)
    record_fullspeed_review(tmp_path, "r", watched_full_speed=True, listened=True,
                            verdict="approved")
    require_fullspeed_review(tmp_path, ep)
    (tmp_path / "ep.mp4").write_bytes(b"episode-bytes-v2")
    with pytest.raises(GateLocked, match="changed"):
        require_fullspeed_review(tmp_path, ep)


# --- 5. lip-sync face policy ---------------------------------------------------

from forge.assemble.face_policy import classify_pose, select_face, classify_shot


def _landmarks(nose_x=0.5, left_eye_x=0.4, right_eye_x=0.6, y=0.5, scale=100):
    lm = np.zeros((478, 2))
    lm[1] = (nose_x * scale, y * scale)
    lm[33] = (left_eye_x * scale, y * scale)
    lm[263] = (right_eye_x * scale, y * scale)
    lm[10] = (nose_x * scale, 0.2 * scale)
    lm[152] = (nose_x * scale, 0.8 * scale)
    # spread far-away filler indices so face_width is stable (never touch
    # the policy indices 1, 10, 33, 152, 263)
    lm[300:] = np.linspace((0, 0), (scale, scale), 178)
    return lm


def _det(lm, box):
    return {"landmarks": lm, "box": box}


def test_pose_front_vs_profile():
    front = classify_pose(_landmarks())
    assert front["pose"] == "front"
    profile = classify_pose(_landmarks(left_eye_x=0.47, right_eye_x=0.6))
    assert profile["pose"] == "profile" and profile["visible_side"] == "right"
    profile_l = classify_pose(_landmarks(left_eye_x=0.4, right_eye_x=0.53))
    assert profile_l["pose"] == "profile" and profile_l["visible_side"] == "left"


def test_select_face_multi_policy():
    big = _det(_landmarks(), (0, 0, 100, 100))
    small = _det(_landmarks(), (200, 200, 210, 210))
    sel = select_face([small, big])
    assert sel["index"] == 1 and sel["n_faces"] == 2
    assert not sel["ambiguous"]  # the small face is far below the ratio
    similar = _det(_landmarks(), (200, 0, 290, 90))
    sel = select_face([big, similar])
    assert sel["ambiguous"]


def test_classify_shot_verdicts():
    front = [_det(_landmarks(), (0, 0, 100, 100))]
    ok = classify_shot([front] * 10)
    assert ok["verdict"] == "ok"
    multi = classify_shot([[_det(_landmarks(), (0, 0, 100, 100)),
                            _det(_landmarks(), (0, 0, 90, 90))]] * 10)
    assert multi["verdict"] == "unsupported"
    prof = classify_shot([[_det(_landmarks(left_eye_x=0.47, right_eye_x=0.6),
                                (0, 0, 100, 100))]] * 10)
    assert prof["verdict"] == "review" and prof["profile"]
    missing = classify_shot([[], front, [], front, [], front, [], front, [], front])
    assert missing["verdict"] == "review"


# --- 6. vertical reframe --------------------------------------------------------

from forge.assemble.vertical import probe, reframe, smooth_track


def test_reframe_center_crop_and_audio(tmp_path):
    src = _make_episode(tmp_path / "src.mp4", seconds=2, size=(160, 90))
    rep = reframe(src, tmp_path / "out.mp4", out_size=(90, 160), mode="center")
    assert rep["mode"] == "center" and rep["out_size"] == [90, 160]
    info = probe(tmp_path / "out.mp4")
    assert (info["width"], info["height"]) == (90, 160)
    assert info["has_audio"]
    assert abs(info["seconds"] - 2) < 0.6


def test_reframe_refuses_vertical_source(tmp_path):
    src = _make_episode(tmp_path / "vert.mp4", seconds=1, size=(90, 160))
    with pytest.raises(GateLocked, match="not wide enough"):
        reframe(src, tmp_path / "out.mp4", out_size=(90, 160), mode="center")


def test_smooth_track_gap_bridging():
    samples = [(0.0, 0.2, 0.1), (0.5, None, 0.0), (1.0, 0.8, 0.1)]
    assert smooth_track(samples, window=1) == []  # 2 valid < MIN_FACE_SAMPLES
    samples += [(1.5, 0.7, 0.1), (2.0, 0.6, 0.1), (2.5, 0.65, 0.1)]
    track = smooth_track(samples, window=1)
    assert len(track) == 6 and all(c is not None for _, c in track)


# --- 7. viewer reception ---------------------------------------------------------

from forge.reception import record_viewing, read_store, aggregate, STORE_NAME


def test_reception_record_and_aggregate(tmp_path):
    store = tmp_path / STORE_NAME
    record_viewing(store, "EP01", "viewer-a", pace=4, music_level=3,
                   moments=[{"t": 30.0, "kind": "pace", "note": "drags here"}])
    record_viewing(store, "EP01", "viewer-b", pace=2, music_level=5)
    record_viewing(store, "EP02", "viewer-a", pace=5, music_level=5)
    agg = aggregate(store)
    assert agg["episodes"]["EP01"]["viewings"] == 2
    assert agg["episodes"]["EP01"]["pace_mean"] == 3.0
    assert agg["episodes"]["EP01"]["viewers"] == 2
    assert agg["episodes"]["EP02"]["music_level_mean"] == 5.0


def test_reception_validation_and_corrupt_lines(tmp_path):
    store = tmp_path / STORE_NAME
    with pytest.raises(GateLocked, match="1-5"):
        record_viewing(store, "EP01", "v", pace=6, music_level=3)
    with pytest.raises(GateLocked, match="viewer"):
        record_viewing(store, "EP01", " ", pace=3, music_level=3)
    with pytest.raises(GateLocked, match="whole-number"):
        record_viewing(store, "EP01", "v", pace=3.5, music_level=3)
    record_viewing(store, "EP01", "v", pace=3, music_level=3)
    with open(store, "a") as fh:
        fh.write("{not json\n")
    store_data = read_store(store)
    assert store_data["skipped_lines"] == 1 and len(store_data["records"]) == 1
