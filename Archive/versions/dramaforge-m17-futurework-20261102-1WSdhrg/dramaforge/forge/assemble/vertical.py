"""Vertical 9:16 reframing of already-rendered landscape episodes.

This is the no-spend half of "render the episode set again in vertical 9:16":
the episodes the project already owns are reframed locally (crop + scale,
following the speaker's face when one is found), which costs nothing and
needs no model call. Model REGENERATION at 9:16 stays on the paid path and
remains held for approval; it is not this module.

Two passes, both local:
1. sample_face_track: Haar frontal + profile cascades over frames sampled at
   a fixed cadence give a face-center x per sample (None when no face).
2. reframe: the crop window (height x height*9/16) follows the smoothed
   track, clamped to the frame; with too few detections it falls back to a
   center crop and says so. Frames stream through ffmpeg (libx264); the
   source audio is copied through untouched.
"""
import json
import math
import os
import subprocess
import tempfile

from forge.gates.common import GateLocked, now_iso

DEFAULT_OUT = (720, 1280)  # 9:16
SAMPLE_EVERY_S = 0.5
MIN_FACE_SAMPLES = 5
SMOOTH_WINDOW = 5  # samples


def probe(path) -> dict:
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise GateLocked(f"video missing or empty: {path}")
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        raise GateLocked("ffprobe not found; install ffmpeg")
    except subprocess.CalledProcessError as e:
        raise GateLocked(f"ffprobe failed on {path}: {e.stderr.strip()[:200]}")
    meta = json.loads(out)
    vs = next((s for s in meta.get("streams", []) if s.get("codec_type") == "video"), None)
    if not vs:
        raise GateLocked(f"no video stream in {path}")
    fps_txt = vs.get("avg_frame_rate") or vs.get("r_frame_rate") or "0/1"
    num, _, den = fps_txt.partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return {"width": int(vs["width"]), "height": int(vs["height"]),
            "seconds": float(meta.get("format", {}).get("duration", 0) or 0),
            "fps": fps,
            "has_audio": any(s.get("codec_type") == "audio" for s in meta.get("streams", []))}


def _cascades():
    import cv2
    base = os.path.join(cv2.data.haarcascades)
    frontal = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml")
    profile = cv2.CascadeClassifier(base + "haarcascade_profileface.xml")
    if frontal.empty() or profile.empty():
        raise GateLocked("OpenCV Haar cascades not found")
    return frontal, profile


def sample_face_track(path, every_s: float = SAMPLE_EVERY_S,
                      detect_width: int = 640) -> list:
    """[(t_seconds, cx_fraction_or_None, face_width_fraction)] over the video.
    Detection runs on a downscaled gray frame for speed; coordinates are
    returned as fractions of the full frame."""
    import cv2
    frontal, profile = _cascades()
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise GateLocked(f"cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1
    step = max(1, int(round(fps * every_s)))
    samples = []
    idx = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            scale = detect_width / gray.shape[1] if gray.shape[1] > detect_width else 1.0
            if scale != 1.0:
                gray = cv2.resize(gray, None, fx=scale, fy=scale)
            minsize = (max(16, int(40 * scale)),) * 2
            faces = list(frontal.detectMultiScale(gray, 1.1, 5, minSize=minsize))
            faces += list(profile.detectMultiScale(gray, 1.1, 5, minSize=minsize))
            if faces:
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                samples.append((idx / fps, (x + w / 2) / scale / width,
                                w / scale / width))
            else:
                samples.append((idx / fps, None, 0.0))
        idx += 1
        if n_frames and idx > n_frames + step:
            break
    cap.release()
    return samples


def scene_track(path, every_s: float = SAMPLE_EVERY_S) -> list:
    """Scene-aware framing: one stable crop center per detected shot.

    Why: a continuously gliding crop window cuts speakers in half when a
    detection flickers, and jitter reads as a defect. Dialogue microdrama
    reframes want one framing per shot. The center per scene is the median
    of its sampled face centers (center frame when the scene has too few
    detections). Returns [(t_start, cx_fraction)] covering the video."""
    from forge.assemble.qa import cuts
    info = probe(path)
    scenes = cuts(str(path))
    if not scenes:
        scenes = [(0.0, info["seconds"])]
    if scenes and scenes[0][0] > 0:
        scenes = [(0.0, scenes[0][0])] + scenes
    samples = sample_face_track(path, every_s)
    track = []
    for start, end in scenes:
        vals = sorted(cx for t, cx, _ in samples
                      if cx is not None and start <= t < end)
        if len(vals) >= 3:
            cx = vals[len(vals) // 2]
        elif vals:
            cx = vals[0]
        else:
            cx = 0.5
        track.append((start, cx))
    return track


def smooth_track(samples, window: int = SMOOTH_WINDOW) -> list:
    """Median-smooth the valid face centers and interpolate gaps. Returns
    [(t, cx_fraction)] with one center per sample (None-filled gaps bridged
    by nearest valid sample, edges held)."""
    valid = [(t, cx) for t, cx, _ in samples if cx is not None]
    if len(valid) < MIN_FACE_SAMPLES:
        return []
    out = []
    for i, (t, cx, _) in enumerate(samples):
        neighbourhood = [c for _, c in valid if abs(_ - t) <= window / 2 * (samples[1][0] - samples[0][0] if len(samples) > 1 else SAMPLE_EVERY_S)]
        if neighbourhood:
            neighbourhood = sorted(neighbourhood)
            out.append((t, neighbourhood[len(neighbourhood) // 2]))
        else:
            nearest = min(valid, key=lambda vc: abs(vc[0] - t))
            out.append((t, nearest[1]))
    return out


def _track_center(track, t):
    """Crop center at time t: the center of the scene containing t (constant
    within a scene, no interpolation across cuts)."""
    if not track:
        return None
    center = track[0][1]
    for start, c in track:
        if t >= start:
            center = c
        else:
            break
    return center


def reframe(src, dst, out_size=DEFAULT_OUT, mode: str = "auto",
            sample_every_s: float = SAMPLE_EVERY_S) -> dict:
    """Reframe one landscape episode to vertical. mode 'face-track' forces the
    face track (fails if too few detections), 'center' forces a static center
    crop, 'auto' tracks when it can and says which it did."""
    import cv2
    info = probe(src)
    out_w, out_h = out_size
    if out_w <= 0 or out_h <= 0:
        raise GateLocked(f"bad output size {out_size}")
    crop_h = info["height"]
    crop_w = int(round(crop_h * out_w / out_h))
    if crop_w >= info["width"]:
        raise GateLocked(
            f"source {info['width']}x{info['height']} is not wide enough for the "
            f"{out_w}:{out_h} crop ({crop_w}); already vertical or square?")
    crop_w -= crop_w % 2

    track = []
    if mode in ("auto", "face-track"):
        track = scene_track(src, sample_every_s)
    if mode == "face-track" and not track:
        raise GateLocked("face-track mode found too few faces; use auto or center")
    used = "scene-face-track" if track else "center"

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise GateLocked(f"cannot open video: {src}")
    fps = cap.get(cv2.CAP_PROP_FPS) or info["fps"] or 30.0
    max_x = info["width"] - crop_w
    dst = str(dst)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    fd, silent = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
             "-s", f"{out_w}x{out_h}", "-r", f"{fps:.6f}", "-i", "-",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-pix_fmt", "yuv420p", silent],
            stdin=subprocess.PIPE)
        frames = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t = frames / fps
            cx = _track_center(track, t)
            x0 = int(round((cx if cx is not None else 0.5) * info["width"] - crop_w / 2))
            x0 = max(0, min(max_x, x0))
            crop = frame[:, x0:x0 + crop_w]
            enc.stdin.write(cv2.resize(crop, (out_w, out_h),
                                       interpolation=cv2.INTER_AREA).tobytes())
            frames += 1
        cap.release()
        enc.stdin.close()
        if enc.wait() != 0 or frames == 0:
            raise GateLocked(f"ffmpeg encode failed after {frames} frames on {src}")
        if info["has_audio"]:
            mux = subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", str(src),
                 "-map", "0:v", "-map", "1:a?", "-c:v", "copy", "-c:a", "copy",
                 "-shortest", dst],
                capture_output=True, text=True)
            if mux.returncode != 0:
                raise GateLocked(f"audio mux failed on {src}: {mux.stderr.strip()[:200]}")
        else:
            os.replace(silent, dst)
    finally:
        if os.path.exists(silent):
            os.unlink(silent)
    out_info = probe(dst)
    if (out_info["width"], out_info["height"]) != (out_w, out_h):
        raise GateLocked(
            f"output is {out_info['width']}x{out_info['height']}, expected {out_w}x{out_h}")
    return {"src": str(src), "output": dst, "mode": used,
            "out_size": [out_w, out_h], "crop_w": crop_w,
            "frames": frames, "seconds": round(out_info["seconds"], 2),
            "audio_copied": bool(info["has_audio"]),
            "reframed_at": now_iso()}
