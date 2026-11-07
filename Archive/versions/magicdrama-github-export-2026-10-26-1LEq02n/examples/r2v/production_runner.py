"""Wan 3.0 production runner for the 3-episode Yule Ball series.
HARD GUARD: refuses to submit unless --approved-cap == manifest total and
--approval-ref carries the user's budget-approval message id. --dry-run prints
the plan only. Stop gates: halt after e01s03 (first two-body) for main's
inspection, and after each episode. Any verification failure stops the run.
Stop-on-error is literal: any unexpected API response stops before any retry.
"""
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from magicdrama.audiofirst.magichour_catalog import quote_credits, validate_request_shape
from production_prompts import MANIFEST, AUDIO_DIR, refs_for, prompt_for, missing_mentions
H = {}

API = "https://api.magichour.ai"
ROOT = Path(__file__).resolve().parent
KEY_FILE = Path("/home/sandbox/.vault/magic-hour-api-key-70da61/password")
BANK = json.load(open(str(ROOT / "harry-draconia-reference-bank.json")))
BANK_BY_NAME = {r["name"]: r for r in BANK["references"]}
REF_FILES = {r["name"]: "/downloads/" + r["id"] + ".png" for r in BANK["references"]}
AUDIO_LOCK_FILE = RUN_DIR_DEFAULT = None
def _audio_lock():
    lf = ROOT / "production-2026-10-26" / "accepted-audio-sha256-lock.json"
    return json.loads(lf.read_text()) if lf.exists() else {}
RUN_DIR = ROOT / ("production-" + time.strftime("%Y-%m-%d"))
GATE_AFTER = {("e01", 3): "first two-body shot - STOP for main inspection",
              ("e01", 18): "E01 complete - checkpoint", ("e02", 16): "E02 complete - checkpoint"}


def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stop(msg, receipts):
    receipts["stopped"] = msg
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
    print("STOP:", msg); sys.exit(2)



def complete_job(ep, n, s, job_id, receipts, entry, out_name=None):
    """Poll job to completion, download, run verify gates, update entry in-place."""
    deadline = time.time() + 900
    out = RUN_DIR / (out_name or "%s-s%02d.mp4" % (ep, n))
    while True:
        if time.time() > deadline: stop("timeout %s s%02d job %s" % (ep, n, job_id), receipts)
        time.sleep(15)
        st = requests.get(API + "/v1/video-projects/" + job_id, headers=H, timeout=60)
        if st.status_code != 200: stop("status HTTP %s" % st.status_code, receipts)
        j = st.json(); status = j.get("status")
        if status == "complete":
            dl = (j.get("downloads") or [{}])[0].get("url")
            if not dl: stop("complete no url", receipts)
            vid = requests.get(dl, timeout=300)
            if vid.status_code != 200: stop("download HTTP %s" % vid.status_code, receipts)
            out.write_bytes(vid.content); break
        if status in ("error", "canceled"): stop("job %s %s" % (job_id, status), receipts)

    vdir = RUN_DIR / ("verify-%s-s%02d" % (ep, n))
    ref_audio = str(AUDIO_DIR / s["audio"]) if s.get("audio") else "-"
    vr = subprocess.run([sys.executable, str(ROOT / "verify_shot.py"), str(out), ref_audio, str(vdir)],
                        capture_output=True, text=True)
    if vr.returncode != 0: stop("verify crashed %s s%02d: %s" % (ep, n, vr.stderr[-400:]), receipts)
    v = json.loads((vdir / "verify.json").read_text())
    fps_num, fps_den = v["video"]["r_frame_rate"].split("/")
    fails, warns = [], []
    if int(fps_num) // int(fps_den) != 30: fails.append("fps " + v["video"]["r_frame_rate"])
    if not v.get("audio_track"): fails.append("no audio track")
    # Wan3 resynthesizes dialogue by design (documented owner contract + measured ~0.2 on both
    # prior jobs): envelope correlation vs the reference CANNOT reach waveform-copy levels, so a
    # hard envelope gate is a guaranteed false-fail, not a signal (main 08:48:24: gate engineering
    # must not require exact waveform copy from Wan resynthesis). Record the number for the report;
    # delivery quality is gated by ASR word-diff below plus the mandatory human listen.
    if s.get("audio") and "envelope_correlation" in v:
        warns.append("envelope corr %.2f vs ref (expected ~0.2: Wan3 resynthesizes; not an emotion signal)" % v["envelope_correlation"])
    sampled = v["motion"].get("sampled", 0)
    ns = v["motion"]["near_static"]
    if sampled and ns > 0.4 * sampled and ns > 30:
        fails.append("mannequin risk: %d/%d sampled frames static" % (ns, sampled))
    elif ns > 0:
        warns.append("static frames %d/%d sampled (a hold can be legit; review timestamps)" % (ns, sampled))
    if s.get("audio") and v.get("asr_match") is False:
        # dropped/changed content is never silently passed: gate stops for review
        fails.append("REVIEW REQUIRED - ASR text delta (may be whisper-base noise, may be dropped content): clip='%s' ref='%s'"
                     % (v.get("asr_clip", "")[:80], v.get("asr_ref", "")[:80]))
    entry.update({"state": "verified", "verify": v, "gate_fails": fails, "gate_warns": warns})
    (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
    if fails: stop("gate failures %s s%02d: %s" % (ep, n, fails), receipts)
    if (ep, n) in GATE_AFTER: stop("STOP GATE: " + GATE_AFTER[(ep, n)], receipts)



import stages as STAGES

def _stage_receipts():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    f = RUN_DIR / "run-receipts.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "shots": [], "charged_total": 0}


def _write_stage_receipts(receipts):
    (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))


def _upload_generic(path, typ, receipts):
    ext = str(path).rsplit(".", 1)[1].lower()
    r = requests.post(API + "/v1/files/upload-urls", headers=H,
                      json={"items": [{"extension": ext, "type": typ}]}, timeout=60)
    if r.status_code != 200: stop("upload-urls %s HTTP %s" % (path, r.status_code), receipts)
    item = r.json()["items"][0]
    up = requests.put(item["upload_url"], data=Path(path).read_bytes(), timeout=180)
    if up.status_code not in (200, 201, 204): stop("PUT %s HTTP %s" % (path, up.status_code), receipts)
    return item["file_path"]


def _submit_reserved(receipts, ledger_entry, endpoint, body, quote):
    """Same reserve/submit/halt discipline as the legacy path, for a staged job."""
    receipts["shots"].append(ledger_entry)
    _write_stage_receipts(receipts)
    try:
        r = requests.post(API + endpoint, headers=H, json=body, timeout=60)
    except requests.exceptions.ConnectionError as ce:
        pre = "Failed to establish a new connection" in str(ce) or "Name or service not known" in str(ce)
        receipts["shots"][-1].update({"state": "post_exception", "error": str(ce)[:300],
                                      "evidence": "pre_network" if pre else "unknown_transport"})
        _write_stage_receipts(receipts)
        stop("submit transport exception (recorded): %s" % str(ce)[:200], receipts)
    except requests.exceptions.RequestException as re_:
        receipts["shots"][-1].update({"state": "post_exception", "error": str(re_)[:300],
                                      "evidence": "unknown_transport"})
        _write_stage_receipts(receipts)
        stop("submit transport exception (recorded): %s" % str(re_)[:200], receipts)
    if r.status_code != 200:
        definitive = r.status_code in (400, 422)
        receipts["shots"][-1].update({"state": "rejected" if definitive else "post_exception",
                                      "error": "HTTP %s %s" % (r.status_code, r.text[:300]),
                                      "evidence": "provider_rejection" if definitive else "unknown_response"})
        _write_stage_receipts(receipts)
        stop("submit HTTP %s: %s" % (r.status_code, r.text[:600]), receipts)
    data = r.json()
    if not data.get("id") or data.get("credits_charged") != quote:
        stop("submit unexpected response: %s" % r.text[:600], receipts)
    receipts["charged_total"] = receipts.get("charged_total", 0) + data["credits_charged"]
    receipts["shots"][-1].update({"job": data["id"], "charged": data["credits_charged"], "state": "submitted"})
    _write_stage_receipts(receipts)
    return data["id"]


def _poll_image_job(job_id, out_path, receipts):
    deadline = time.time() + 900
    while True:
        if time.time() > deadline: stop("timeout image job %s" % job_id, receipts)
        time.sleep(10)
        st = requests.get(API + "/v1/image-projects/" + job_id, headers=H, timeout=60)
        if st.status_code != 200: stop("image status HTTP %s" % st.status_code, receipts)
        j = st.json(); status = j.get("status")
        if status == "complete":
            dls = j.get("downloads") or []
            if not dls: stop("image complete no url", receipts)
            img = requests.get(dls[0]["url"], timeout=300)
            if img.status_code != 200: stop("image download HTTP %s" % img.status_code, receipts)
            Path(out_path).write_bytes(img.content); return
        if status in ("error", "canceled"): stop("image job %s %s" % (job_id, status), receipts)


def parse_shot_key(text):
    """Parse 'e01:2' or 'e01:2#b1' -> (ep, shot:int, beat:int|None)."""
    ep, rest = text.split(":")
    if "#b" in rest:
        n, b = rest.split("#b"); return ep, int(n), int(b)
    return ep, int(rest), None


def _units(shots):
    """Yield (shot, beat) generation units; beat None for undivided shots."""
    for s in shots:
        beats = STAGES.beats_of(s)
        if beats:
            for b in beats:
                yield s, b
        else:
            yield s, None


def _beat_shot(s, b):
    """Merge a beat into a pseudo-shot for prompt/audio decisions; the approved
    line, speaker and audio ride only on the beat that declares carries_line."""
    if b is None:
        return s
    u = dict(s)
    for k in ("action", "framing_class", "camera", "two_body", "frame", "end_frame"):
        if k in b:
            u[k] = b[k]
    if not b.get("carries_line"):
        u["speaker"] = None; u["line"] = None; u["audio"] = None
    return u


def _dialogue_window(s):
    """Seconds window the paid lip-sync covers: the carries_line beat span for beat
    shots (the rest is offscreen voice by design), else the whole shot."""
    beats = STAGES.beats_of(s)
    if beats:
        off = 0
        for b in sorted(beats, key=lambda x: x["id"]):
            if b.get("carries_line"):
                return float(off), float(off + b["dur_s"])
            off += b["dur_s"]
    return 0.0, float(s["billing_s"])


def _tag(ep, n, b):
    return "%s-s%02d" % (ep, n) if b is None else "%s-s%02d-b%d" % (ep, n, b["id"])


def stage_frames(args):
    """Compose the locked start frame per shot (ai-image-editor). Artifact must then be
    ACCEPTED via --accept-frame before the video stage can consume it."""
    receipts = _stage_receipts()
    shots = [s for s in MANIFEST["shots"]
             if s.get("frame") or any(b.get("frame") for b in (s.get("beats") or []))]
    if args.only:
        shots = [s for s in shots if "%s:%d" % (s["episode"], s["shot"]) == args.only]
    for s in shots:
        berr = STAGES.validate_beats(s)
        if berr:
            stop("%s s%02d: %s" % (s["episode"], s["shot"], berr), receipts)
    units = [(s, b) for s, b in _units(shots) if (b or s).get("frame") or (b and b.get("frame"))]
    units = [(s, b) for s, b in units if (b.get("frame") if b else s.get("frame"))]
    quote = 50  # nano-banana-2.1 single image at 1k, exact per models page
    if args.approved_cap != quote * len(units) or not args.approval_ref.startswith("wamid."):
        stop("REFUSED: frames stage needs --approved-cap %d and --approval-ref wamid... "
             "(50 cr x %d frame(s), one attempt each)" % (quote * len(units), len(units)), receipts)
    for s, b in units:
        ep, n = s["episode"], s["shot"]
        spec = b["frame"] if b else s["frame"]
        tag = _tag(ep, n, b)
        refs = [_upload_generic(REF_FILES[rn], "image", receipts) for rn in spec.get("refs", [])]
        body = {"name": "%s-start-frame" % tag, "model": "nano-banana-2.1",
                "image_count": 1, "aspect_ratio": "9:16", "resolution": "1k",
                "style": {"prompt": spec["prompt"]}, "assets": {"image_file_paths": refs}}
        jid = _submit_reserved(receipts,
                               {"ep": ep, "shot": n, "beat": b and b["id"], "stage": "frames", "state": "reserved", "intended": quote},
                               "/v1/ai-image-editor", body, quote)
        out = RUN_DIR / ("%s-start.png" % tag)
        _poll_image_job(jid, out, receipts)
        STAGES.record_artifact(receipts, ep, n, "frames", out, "frame_generated",
                               beat=b["id"] if b else None, job=jid)
        _write_stage_receipts(receipts)
        print("frame generated %s job %s - REVIEW then --accept-frame %s" % (tag, jid, "%s:%d%s" % (ep, n, "#b%d" % b["id"] if b else "")))
    stop("frames stage batch done; no frame is video-usable until accepted", receipts)


def accept_frame(args):
    receipts = _stage_receipts()
    if not args.approval_ref.startswith("wamid."):
        stop("REFUSED: --accept-frame needs --approval-ref wamid... (recorded acceptance decision)", receipts)
    ep, n, b = parse_shot_key(args.accept_frame)
    rec = STAGES.get_artifact(receipts, ep, n, "frames", beat=b)
    if not rec or rec.get("state") != "frame_generated":
        stop("no frame_generated artifact for %s:%d to accept" % (ep, n), receipts)
    if STAGES.sha256_file(rec["artifact"]) != rec.get("sha256"):
        stop("frame artifact %s drifted since generation - recompose, do not accept" % rec["artifact"], receipts)
    rec["state"] = "frame_accepted"; rec["acceptance_ref"] = args.approval_ref
    _write_stage_receipts(receipts)
    print("frame accepted for %s:%d (ref %s)" % (ep, n, args.approval_ref))


def stage_video(args):
    """Per-shot i2v bound to the ACCEPTED composed start frame (and end frame where declared).
    Blocked by construction unless the frames artifact is accepted and hash-intact."""
    receipts = _stage_receipts()
    shots = MANIFEST["shots"]
    if args.only:
        shots = [s for s in shots if "%s:%d" % (s["episode"], s["shot"]) == args.only]
    total = sum(s["billing_s"] * 96 for s in shots)
    if args.approved_cap != total or not args.approval_ref.startswith("wamid."):
        stop("REFUSED: video stage needs --approved-cap %d and --approval-ref wamid..." % total, receipts)
    for s, b in _units(shots):
        ep, n = s["episode"], s["shot"]
        u = _beat_shot(s, b)
        sec = b["dur_s"] if b else s["billing_s"]
        tag = _tag(ep, n, b)
        frec = STAGES.require_artifact(receipts, ep, n, "video", lambda m: stop(m, receipts),
                                       beat=b["id"] if b else None)
        start_fp = _upload_generic(frec["artifact"], "image", receipts)
        assets = {"image_file_path": start_fp}
        if u.get("end_frame"):
            erec = STAGES.get_artifact(receipts, ep, n, "frames_end", beat=b["id"] if b else None)
            if not erec or erec.get("state") != "frame_accepted":
                stop("%s declares end_frame but no accepted end-frame artifact" % tag, receipts)
            assets["end_image_file_path"] = _upload_generic(erec["artifact"], "image", receipts)
        body = {"name": "%s-i2v" % tag, "model": "wan-3.0", "end_seconds": sec,
                "resolution": "720p", "aspect_ratio": "9:16", "audio": True,
                "style": {"prompt": prompt_for(u)}, "assets": assets}
        jid = _submit_reserved(receipts,
                               {"ep": ep, "shot": n, "beat": b and b["id"], "stage": "video", "state": "reserved", "intended": sec * 96},
                               "/v1/image-to-video", body, sec * 96)
        complete_job(ep, n, u, jid, receipts, receipts["shots"][-1], out_name="%s.mp4" % tag)
        out = RUN_DIR / ("%s.mp4" % tag)
        STAGES.record_artifact(receipts, ep, n, "video", out, "video_verified",
                               beat=b["id"] if b else None, job=jid)
        _write_stage_receipts(receipts)
        print("video verified %s job %s" % (tag, jid))
    stop("video stage batch done", receipts)



def stage_assemble(args):
    """Mux the accepted hash-locked audio onto the verified video (free, local).
    The approved ElevenLabs take becomes the literal soundtrack; generated video audio is dropped."""
    receipts = _stage_receipts()
    shots = MANIFEST["shots"]
    if args.only:
        shots = [s for s in shots if "%s:%d" % (s["episode"], s["shot"]) == args.only]
    alock = _audio_lock()
    for s in shots:
        berr = STAGES.validate_beats(s)
        if berr:
            stop("%s s%02d: %s" % (s["episode"], s["shot"], berr), receipts)
    for s, b in ((s, None) for s in shots):  # shot-level assembly; beats merge first
        ep, n = s["episode"], s["shot"]
        beats = STAGES.beats_of(s)
        if beats:
            # merge per-beat verified videos in beat order, preserving total approved timing
            blines = []
            for bb in sorted(beats, key=lambda x: x["id"]):
                vrec = STAGES.require_artifact(receipts, ep, n, "assemble", lambda m: stop(m, receipts), beat=bb["id"])
                blines.append("file '%s'" % vrec["artifact"])
            blst = RUN_DIR / ("%s-beatconcat.txt" % _tag(ep, n, None))
            blst.write_text("\n".join(blines) + "\n")
            merged = RUN_DIR / ("%s-beatmerge.mp4" % _tag(ep, n, None))
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                                "-i", str(blst), "-c", "copy", str(merged)], capture_output=True, text=True)
            if r.returncode != 0 or not merged.exists():
                stop("ffmpeg beat merge failed %s s%02d: %s" % (ep, n, r.stderr[-300:]), receipts)
            vrec = {"artifact": str(merged), "job": None}
        else:
            vrec = STAGES.require_artifact(receipts, ep, n, "assemble", lambda m: stop(m, receipts))
        u = s
        tag = _tag(ep, n, None)
        beat_id = None
        out = RUN_DIR / ("%s-assembled.mp4" % tag)
        if not u.get("audio"):
            # wordless unit (insert/action beat or silent shot): approved audio has no
            # place here; carry the verified video through unchanged
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vrec["artifact"],
                                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                                "-shortest", str(out)], capture_output=True, text=True)
            if r.returncode != 0 or not out.exists():
                stop("ffmpeg passthrough failed %s: %s" % (tag, r.stderr[-300:]), receipts)
            STAGES.record_artifact(receipts, ep, n, "assemble", out, "assembled", beat=beat_id,
                                   mode="passthrough", source_video_job=vrec.get("job"))
            _write_stage_receipts(receipts)
            print("assembled (wordless passthrough) %s -> %s" % (tag, out))
            continue
        apath = AUDIO_DIR / u["audio"]
        if not apath.exists():
            stop("accepted audio missing: %s" % apath, receipts)
        if u["audio"] in alock and STAGES.sha256_file(apath) != alock[u["audio"]]:
            stop("accepted-audio hash mismatch for %s - audio drifted from accepted set" % u["audio"], receipts)
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vrec["artifact"], "-i", str(apath),
                            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            stop("ffmpeg assemble failed %s: %s" % (tag, r.stderr[-300:]), receipts)
        STAGES.record_artifact(receipts, ep, n, "assemble", out, "assembled", beat=beat_id,
                               mode="mux", audio=u["audio"], audio_sha256=STAGES.sha256_file(apath),
                               source_video_job=vrec.get("job"))
        _write_stage_receipts(receipts)
        print("assembled %s -> %s (audio %s)" % (tag, out, u["audio"]))
    stop("assemble stage batch done", receipts)


def _duration_s(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip())


def _facecheck_sheet(video, out_png, density=9):
    """Free local evidence: `density` sampled frames across the clip in a tile.
    Sampled observation only - sparse samples can MISS a brief readable mouth or
    camera change; supports a face-visibility verdict, never proves every-frame
    motion or sync. When the tile is ambiguous, record 'ambiguous' and re-sample
    denser (--facecheck-frames) or inspect motion directly before judging."""
    d = _duration_s(video)
    frs = []
    for i in range(density):
        t = d * (i + 0.5) / density
        fp = RUN_DIR / ("facecheck-%d.png" % i)
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % t, "-i", str(video),
                            "-frames:v", "1", str(fp)], capture_output=True, text=True)
        if r.returncode != 0 or not fp.exists():
            stop("ffmpeg facecheck frame failed: %s" % r.stderr[-300:], _stage_receipts())
        frs.append(fp)
    from PIL import Image
    ims = [Image.open(str(f)) for f in frs]
    cols = 3; rows = -(-len(ims) // cols)
    cw = max(i.size[0] for i in ims); ch = max(i.size[1] for i in ims)
    sheet = Image.new("RGB", (cw * cols, ch * rows))
    for k, i in enumerate(ims):
        sheet.paste(i, ((k % cols) * cw, (k // cols) * ch))
    sheet.save(str(out_png))
    return out_png


def record_face_verdict(args):
    """Record a human face-visibility verdict from the sampled facecheck sheet, e.g.
    --face-verdict e01:3=readable  (values: readable | not_readable | ambiguous). Free, local."""
    receipts = _stage_receipts()
    key, _, val = args.face_verdict.partition("=")
    if val not in ("readable", "not_readable", "ambiguous") or ":" not in key:
        stop("bad --face-verdict, want ep:shot=readable|not_readable", receipts)
    ep, n, b = parse_shot_key(key)
    receipts.setdefault("stage_shots", {}).setdefault(STAGES._key(ep, n, b), {})["face_verdict"] = val
    _write_stage_receipts(receipts)
    print("face verdict recorded for %s -> %s" % (STAGES._key(ep, n, b), val))


def stage_lipsync(args):
    """Per-shot lip-sync gated on ACTUAL face visibility in the generated video.
    Always refreshes the sampled facecheck sheet (free). Dialogue shots stop until a
    --face-verdict is recorded; the verdict, not the manifest class, decides.
    soundtrack-mode shots pass the assembled clip through with approved audio intact.
    Paid lip-sync additionally requires --approved-cap == quote and --approval-ref wamid.
    Contract: POST /v1/lip-sync, lite mode, per-frame billing settling to rendered frames."""
    receipts = _stage_receipts()
    shots = MANIFEST["shots"]
    if args.only:
        shots = [s for s in shots if "%s:%d" % (s["episode"], s["shot"]) == args.only]
    fps = min(30.0, float(MANIFEST.get("fps_actual_verified", 30)))
    plans, total = {}, 0
    for s in shots:
        berr = STAGES.validate_beats(s)
        if berr:
            stop("%s s%02d: %s" % (s["episode"], s["shot"], berr), receipts)
    for s in shots:
        ep, n = s["episode"], s["shot"]
        key = STAGES._key(ep, n, None)
        STAGES.require_artifact(receipts, ep, n, "lipsync", lambda m: stop(m, receipts))
        verdict = receipts.get("stage_shots", {}).get(key, {}).get("face_verdict")
        plan = STAGES.lipsync_plan(s, face_verdict=verdict)
        plans[key] = plan
        if plan["mode"] == "lipsync" and not plan["needs_verdict"]:  # unresolved excluded: batch stops on it below
            w0, w1 = _dialogue_window(s)
            total += int(-(-(w1 - w0) * fps // 1))  # ceil frames, 1 cr/frame lite
    if total and (args.approved_cap != total or not args.approval_ref.startswith("wamid.")):
        stop("REFUSED: lipsync stage needs --approved-cap %d and --approval-ref wamid... "
             "(lite ~1 cr/frame at %.0f fps, settles to rendered frames)" % (total, fps), receipts)
    for s in shots:
        ep, n = s["episode"], s["shot"]
        key = STAGES._key(ep, n, None)
        tag = _tag(ep, n, None)
        arec = STAGES.get_artifact(receipts, ep, n, "assemble")
        sheet = _facecheck_sheet(arec["artifact"], RUN_DIR / ("%s-facecheck.png" % tag),
                                 density=args.facecheck_frames)
        plan = plans[key]
        if plan["mode"] == "unresolved":
            stop("%s: face visibility UNRESOLVED - %s (sheet %s)" % (tag, plan["reason"], sheet), receipts)
        if plan["needs_verdict"]:
            stop("%s: face verdict REQUIRED before paid lip-sync - inspect sampled sheet %s "
                 "then run --face-verdict %s=readable|not_readable|ambiguous (%s)"
                 % (tag, sheet, key, plan["reason"]), receipts)
        if plan["mode"] == "soundtrack":
            STAGES.record_artifact(receipts, ep, n, "lipsync", arec["artifact"], "lipsync_done",
                                   mode="soundtrack", reason=plan["reason"], facecheck=str(sheet))
            _write_stage_receipts(receipts)
            print("lipsync skip (soundtrack) %s: %s" % (tag, plan["reason"]))
            continue
        w0, w1 = _dialogue_window(s)
        vid_fp = _upload_generic(arec["artifact"], "video", receipts)
        aud_fp = _upload_generic(str(AUDIO_DIR / s["audio"]), "audio", receipts)
        frames = int(-(-(w1 - w0) * fps // 1))
        body = {"name": "%s-lipsync" % tag,
                "assets": {"video_file_path": vid_fp, "audio_file_path": aud_fp, "video_source": "file"},
                "style": {"generation_mode": "lite"},
                "start_seconds": w0, "end_seconds": w1,
                "max_fps_limit": fps}
        jid = _submit_reserved(receipts,
                               {"ep": ep, "shot": n, "stage": "lipsync", "state": "reserved", "intended": frames},
                               "/v1/lip-sync", body, frames)
        complete_job(ep, n, s, jid, receipts, receipts["shots"][-1], out_name="%s.mp4" % tag)
        out = RUN_DIR / ("%s.mp4" % tag)
        STAGES.record_artifact(receipts, ep, n, "lipsync", out, "lipsync_done",
                               mode="lipsync", job=jid, window=[w0, w1],
                               face_verdict=receipts["stage_shots"][key].get("face_verdict"))
        _write_stage_receipts(receipts)
        print("lipsync done %s job %s (window %.1f-%.1fs)" % (tag, jid, w0, w1))
    stop("lipsync stage batch done", receipts)


def stage_edit(args):
    """Concatenate each episode's lipsync_done clips in shot order (free, local).
    Blocked unless EVERY shot of the episode cleared the lipsync stage."""
    receipts = _stage_receipts()
    eps = {}
    for s in MANIFEST["shots"]:
        eps.setdefault(s["episode"], []).append(s)
    if args.only:
        ep = args.only.split(":")[0]
        eps = {ep: eps[ep]}
    for ep, shots in eps.items():
        shots.sort(key=lambda s: s["shot"])
        lst = RUN_DIR / ("%s-concat.txt" % ep)
        lines = []
        for s in shots:
            berr = STAGES.validate_beats(s)
            if berr:
                stop("%s s%02d: %s" % (s["episode"], s["shot"], berr), receipts)
            rec = STAGES.require_artifact(receipts, s["episode"], s["shot"], "edit",
                                          lambda m: stop(m, receipts))
            lines.append("file '%s'" % rec["artifact"])
        lst.write_text("\n".join(lines) + "\n")
        out = RUN_DIR / ("%s-edited.mp4" % ep)
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                            "-i", str(lst), "-c", "copy", str(out)], capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            stop("ffmpeg edit concat failed %s: %s" % (ep, r.stderr[-300:]), receipts)
        STAGES.record_artifact(receipts, ep, 0, "edit", out, "edited", shots=len(shots))
        _write_stage_receipts(receipts)
        print("edited %s (%d shots) -> %s" % (ep, len(shots), out))
    stop("edit stage batch done", receipts)



def stage_unimplemented(args):
    receipts = _stage_receipts()
    STAGES.require_artifact(receipts, "-", 0, args.stage, lambda m: stop(m, receipts))



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved-cap", type=int, default=0)
    ap.add_argument("--approval-ref", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resume", action="store_true", help="skip shots already state=verified in run-receipts.json")
    ap.add_argument("--only", default="", help="run exactly one shot, e.g. e01:3, then stop")
    ap.add_argument("--max-jobs", type=int, default=0, help="stop after N submissions this run (0=all)")
    ap.add_argument("--submit-only", action="store_true", help="stop after recording the submission; poll later via --resume")
    ap.add_argument("--stage", default="", help="staged pipeline: frames|video|assemble|lipsync|edit")
    ap.add_argument("--face-verdict", default="", help="record face verdict from facecheck sheet, e.g. e01:3=readable|not_readable|ambiguous (beat keys: e01:2#b1)")
    ap.add_argument("--facecheck-frames", type=int, default=9, help="samples per facecheck tile; raise when a 9-frame tile is ambiguous")
    ap.add_argument("--accept-frame", default="", help="record acceptance of a generated frame, e.g. e01:2 (needs --approval-ref)")
    ap.add_argument("--legacy-t2v", action="store_true", help="DEPRECATED single-pass t2v route (no locked frames); explicit opt-in only")
    args = ap.parse_args()

    global H
    if not args.stage and not args.accept_frame and not args.face_verdict and not args.legacy_t2v and not args.dry_run:
        print("STOP: the ordinary entrypoint is the STAGED pipeline. Choose a stage:")
        print("  --stage frames    compose locked start frames (then --accept-frame ep:shot --approval-ref wamid...)")
        print("  --stage video     per-shot i2v bound to accepted frames")
        print("  --stage assemble  mux approved audio onto verified video (free, local)")
        print("  --stage lipsync   lip-sync only where actual generated faces are readable (--face-verdict from facecheck sheet)")
        print("  --stage edit      concat each episode's cleared clips (free, local)")
        print("  --legacy-t2v      DEPRECATED single-pass route, explicit opt-in only")
        sys.exit(2)
    if args.accept_frame:
        token0 = KEY_FILE.read_text().strip()
        H = {"Authorization": "Bearer " + token0}
        accept_frame(args); return
    if args.face_verdict:
        record_face_verdict(args); return
    if args.stage:
        for w in STAGES.validate_manifest(MANIFEST["shots"]):
            print("planner note:", w)
        token0 = KEY_FILE.read_text().strip()
        H = {"Authorization": "Bearer " + token0}
        if args.stage == "frames": stage_frames(args); return
        if args.stage == "video": stage_video(args); return
        if args.stage == "assemble": stage_assemble(args); return
        if args.stage == "lipsync": stage_lipsync(args); return
        if args.stage == "edit": stage_edit(args); return
        stage_unimplemented(args); return

    total = MANIFEST["total_cr"]
    if args.dry_run:
        print("DRY RUN: %d shots, %ds, %d credits" % (MANIFEST["total_shots"], MANIFEST["total_s"], total))
        for s in MANIFEST["shots"][:6]:
            print(" ", s["episode"], "s%02d" % s["shot"], s["billing_s"], "s", s["billing_s"] * 96, "cr", "2body" if s["two_body"] else "")
        print("  ..."); return
    if args.approved_cap != total or not args.approval_ref.startswith("wamid."):
        print("REFUSED: need --approved-cap %d and --approval-ref wamid... (user budget approval)" % total)
        sys.exit(2)

    def balance():
        r = requests.get(API + "/v1/account", headers=H, timeout=60)
        if r.status_code != 200: stop("balance read HTTP %s" % r.status_code, receipts)
        return r.json().get("credits")

    receipts = {"manifest_total": total, "approval_ref": args.approval_ref,
                "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "shots": [], "charged_total": 0}
    token = KEY_FILE.read_text().strip()
    H = {"Authorization": "Bearer " + token}
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    uploaded = {}
    def upload(path, name, typ):
        if name in uploaded: return uploaded[name]
        if name in BANK_BY_NAME and sha256(path) != BANK_BY_NAME[name]["sha256"]:
            stop("hash mismatch for " + name, receipts)
        alock = _audio_lock()
        for fn, h in alock.items():
            if name == fn.rsplit(".", 1)[0] and sha256(path) != h:
                stop("accepted-audio hash mismatch for " + fn + " - audio drifted from accepted set", receipts)
        ext = path.rsplit(".", 1)[1].lower()
        r = requests.post(API + "/v1/files/upload-urls", headers=H,
                          json={"items": [{"extension": ext, "type": typ}]}, timeout=60)
        if r.status_code != 200: stop("upload-urls %s HTTP %s: %s" % (name, r.status_code, r.text[:400]), receipts)
        item = r.json()["items"][0]
        up = requests.put(item["upload_url"], data=Path(path).read_bytes(), timeout=180)
        if up.status_code not in (200, 201, 204): stop("PUT %s HTTP %s" % (name, up.status_code), receipts)
        uploaded[name] = item["file_path"]; return uploaded[name]

    preflight_missing = []
    for s in MANIFEST["shots"]:
        miss = missing_mentions(s)
        if miss:
            preflight_missing.append("%s s%02d: %s" % (s["episode"], s["shot"], ", ".join(miss)))
    if preflight_missing:
        stop("REF MENTION PREFLIGHT FAILED (no POSTs made):\n  " + "\n  ".join(preflight_missing), receipts)

    done_keys = set()
    if (RUN_DIR / "run-receipts.json").exists():
        prior_r = json.loads((RUN_DIR / "run-receipts.json").read_text())
        receipts["shots"] = prior_r.get("shots", [])
        receipts["charged_total"] = sum(x.get("charged", 0) for x in receipts["shots"]
                                        if x.get("state") not in ("released_pre_network", "released_provider_rejection", "rejected", "reserved", "post_exception"))
        (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
        for x in receipts["shots"]:
            if x.get("state") == "submitted":
                # job id known: resume by polling this job; never re-POST.
                jid = x["job"]
                print("resume: polling known job %s for %s s%02d" % (jid, x["ep"], x["shot"]))
                shot_def = { (s["episode"], s["shot"]): s for s in MANIFEST["shots"] }[(x["ep"], x["shot"])]
                complete_job(x["ep"], x["shot"], shot_def, jid, receipts, x)
                print("resume: %s s%02d verified via known job" % (x["ep"], x["shot"]))
            if x.get("state") == "reserved":
                # No verified provider outcome: HALT regardless of balance.
                # Balance is diagnostic only - delayed billing, refunds, offsetting
                # activity and the user's independent MH usage make it non-proof.
                now_bal = balance()
                stop("UNKNOWN SUBMISSION STATE %s s%02d: reserved %d cr, no provider outcome recorded "
                     "(balance %s -> %s, diagnostic only). Reconcile in MH dashboard; no automatic resubmit."
                     % (x["ep"], x["shot"], x.get("intended", 0), x.get("balance_before"), now_bal), receipts)
            if x.get("state") == "post_exception":
                # Only definitive pre-network failure (connection refused / DNS: no bytes
                # transmitted) or provider rejection evidence may release a reservation.
                if x.get("evidence") == "pre_network":
                    x["state"] = "released_pre_network"
                else:
                    stop("UNKNOWN TRANSPORT OUTCOME %s s%02d: %s - halting, no automatic resubmit."
                         % (x["ep"], x["shot"], x.get("error", "")[:200]), receipts)
            if x.get("state") == "rejected":
                x["state"] = "released_provider_rejection"  # definitive provider answer, no charge
    if args.resume and (RUN_DIR / "run-receipts.json").exists():
        done_keys = {(x["ep"], x["shot"]) for x in receipts["shots"] if x.get("state") in ("verified", "downloaded")}
        print("resuming: %d shots already verified, %d cr already charged" % (len(done_keys), receipts["charged_total"]))
    submitted_this_run = 0
    for s in MANIFEST["shots"]:
        ep, n, sec = s["episode"], s["shot"], s["billing_s"]
        if (ep, n) in done_keys:
            continue
        if args.only and "%s:%d" % (ep, n) != args.only:
            continue
        if args.max_jobs and submitted_this_run >= args.max_jobs:
            stop("max-jobs %d reached" % args.max_jobs, receipts)
        quote = quote_credits("wan-3.0", sec, "720p")
        if quote != sec * 96: stop("catalog quote %s != manifest %s for %s s%02d" % (quote, sec * 96, ep, n), receipts)
        if receipts["charged_total"] + quote > args.approved_cap: stop("cap would be exceeded", receipts)
        validate_request_shape("wan-3.0", sec, "720p", "9:16", len(refs_for(s)) + (1 if s.get("audio") else 0), audio=True)

        receipts["shots"].append({"ep": ep, "shot": n, "state": "reserved", "intended": quote,
                                  "balance_before": balance()})
        (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
        refs = [{"file_path": upload(REF_FILES[rn], rn, "image"), "name": rn} for rn in refs_for(s)]
        if s.get("audio"):
            ap_ = str(AUDIO_DIR / s["audio"])
            refs.append({"file_path": upload(ap_, s["audio"].rsplit(".", 1)[0], "audio"),
                         "name": s["audio"].rsplit(".", 1)[0]})
        body = {"name": "%s-s%02d-wan30" % (ep, n), "model": "wan-3.0", "end_seconds": sec,
                "resolution": "720p", "aspect_ratio": "9:16", "audio": True,
                "references": refs, "style": {"prompt": prompt_for(s)}}
        try:
            r = requests.post(API + "/v1/text-to-video", headers=H, json=body, timeout=60)
        except requests.exceptions.ConnectionError as ce:
            pre = "Failed to establish a new connection" in str(ce) or "Name or service not known" in str(ce)
            receipts["shots"][-1].update({"state": "post_exception", "error": str(ce)[:300],
                                          "evidence": "pre_network" if pre else "unknown_transport"})
            (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
            stop("submit %s s%02d transport exception (recorded): %s" % (ep, n, str(ce)[:200]), receipts)
        except requests.exceptions.RequestException as re_:
            receipts["shots"][-1].update({"state": "post_exception", "error": str(re_)[:300],
                                          "evidence": "unknown_transport"})
            (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
            stop("submit %s s%02d transport exception (recorded): %s" % (ep, n, str(re_)[:200]), receipts)
        if r.status_code != 200:
            definitive = r.status_code in (400, 422)
            receipts["shots"][-1].update({"state": "rejected" if definitive else "post_exception",
                                          "error": "HTTP %s %s" % (r.status_code, r.text[:300]),
                                          "evidence": "provider_rejection" if definitive else "unknown_response"})
            (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
            stop("submit %s s%02d HTTP %s: %s" % (ep, n, r.status_code, r.text[:600]), receipts)
        data = r.json()
        if not data.get("id") or data.get("credits_charged") != quote:
            stop("submit %s s%02d unexpected: %s" % (ep, n, r.text[:600]), receipts)
        receipts["charged_total"] += data["credits_charged"]
        job_id = data["id"]
        submitted_this_run += 1
        receipts["shots"][-1].update({"job": job_id, "charged": data["credits_charged"], "state": "submitted"})
        (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
        if args.submit_only:
            stop("submit-only: job %s recorded for %s s%02d; poll via --resume" % (job_id, ep, n), receipts)
        (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
        print("submitted %s s%02d job %s charged %d" % (ep, n, job_id, data["credits_charged"]))

        complete_job(ep, n, s, job_id, receipts, receipts["shots"][-1])

    receipts["done"] = True
    (RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts, indent=2))
    print("ALL SHOTS COMPLETE. charged_total", receipts["charged_total"])


if __name__ == "__main__":
    main()
