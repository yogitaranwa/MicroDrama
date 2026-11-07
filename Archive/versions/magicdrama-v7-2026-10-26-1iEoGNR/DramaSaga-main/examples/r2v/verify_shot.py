"""Reusable 4-gate verification for one generated shot clip.
Gates: (1) actual fps/duration via ffprobe; (2) audio-ref honor via ASR + envelope
correlation; (3) temporal motion profile (mannequin-hold detector); (4) frame
extraction for visual identity/action inspection (grids for agent/human eye test).
Usage: python3 verify_shot.py <clip> <ref_audio_or_-> <out_dir>
"""
import json, subprocess, sys, wave
from pathlib import Path

import numpy as np


def ffprobe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,r_frame_rate,avg_frame_rate,duration,width,height",
                        "-show_entries", "format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    return json.loads(r.stdout)


def envelope_wav(path, win=320):
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    m = len(a) // win * win
    return np.sqrt((a[:m].reshape(-1, win) ** 2).mean(axis=1))


def to_wav(src, out):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
                    "-f", "wav", out], check=True)


def envelope_correlation(clip_wav, ref_wav, max_lag=50):
    pe, re_ = envelope_wav(clip_wav), envelope_wav(ref_wav)
    L = min(len(pe), len(re_))
    best, bestlag = -2, 0
    for lag in range(-max_lag, max_lag + 1):
        x, y = (pe[lag:L], re_[:L - lag]) if lag >= 0 else (pe[:L + lag], re_[-lag:L])
        if len(x) < 20: continue
        x = x - x.mean(); y = y - y.mean()
        d = float(np.sqrt((x ** 2).sum() * (y ** 2).sum()))
        if d == 0: continue
        c = float((x * y).sum() / d)
        if c > best: best, bestlag = c, lag
    return best, bestlag * 0.02


def asr(wav):
    from faster_whisper import WhisperModel
    m = WhisperModel("base")
    segs, _ = m.transcribe(wav, beam_size=5)
    return " ".join(s.text for s in segs).strip()


def motion_profile(clip, workdir):
    d = Path(workdir); d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", clip, "-vf", "fps=30",
                    "-q:v", "3", str(d / "f_%03d.png")], check=True)
    from PIL import Image
    prev, diffs, n = None, [], 0
    for f in sorted(d.glob("f_*.png")):
        a = np.asarray(Image.open(f).convert("L").resize((90, 160)), dtype=np.float32)
        if prev is not None: diffs.append(float(np.abs(a - prev).mean()))
        prev = a; n += 1
    for f in d.glob("f_*.png"): f.unlink()
    arr = np.array(diffs) if diffs else np.zeros(1)
    return {"frames": n, "mean": round(float(arr.mean()), 2), "min": round(float(arr.min()), 2),
            "max": round(float(arr.max()), 2), "near_static": int((arr < 0.5).sum()), "sampled": int(arr.size)}


def grids(clip, out_prefix):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", clip,
                    "-vf", "select='not(mod(n\\,10))',scale=270:480,tile=4x3", "-frames:v", "1",
                    out_prefix + "-seqfull.png"], check=True)


def main():
    clip, ref, outdir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    outdir.mkdir(parents=True, exist_ok=True)
    rep = {"clip": clip}
    meta = ffprobe(clip)
    v = next(s for s in meta["streams"] if s["codec_type"] == "video")
    rep["video"] = {"r_frame_rate": v["r_frame_rate"], "avg_frame_rate": v["avg_frame_rate"],
                    "w": v["width"], "h": v["height"], "dur": meta["format"]["duration"]}
    rep["audio_track"] = any(s["codec_type"] == "audio" for s in meta["streams"])
    clip_wav = str(outdir / "clip.wav"); to_wav(clip, clip_wav)
    if ref != "-":
        ref_wav = str(outdir / "ref.wav"); to_wav(ref, ref_wav)
        c, lag = envelope_correlation(clip_wav, ref_wav)
        rep["envelope_correlation"] = round(c, 3); rep["lag_s"] = round(lag, 2)
        rep["asr_clip"] = asr(clip_wav); rep["asr_ref"] = asr(ref_wav)
        import re as _re
        rep["asr_match"] = _re.sub(r"[^a-z0-9 ]", "", rep["asr_clip"].lower()) == _re.sub(r"[^a-z0-9 ]", "", rep["asr_ref"].lower())
    rep["motion"] = motion_profile(clip, outdir / "frames")
    grids(clip, str(outdir / "grid"))
    (outdir / "verify.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
