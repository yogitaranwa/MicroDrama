"""Pacing: pitch-preserving 1.4x delivery, tight gaps, WPM pass/fail gate measured with WhisperX."""
import os, shutil, statistics, subprocess
import numpy as np
import soundfile as sf

TEMPO = 1.4            # user-locked
GAP_S = 0.6            # reference reels: median 0.8-1.0 s between phrases; tightened
NATURAL_WPM = 150.0
# Calibrated with the SAME WhisperX method: unstretched Kokoro measures ~234, reference reels ~304-326,
# so 1.4x of the TTS baseline (~330) lands on the reference pace.
TARGET_PHRASE_WPM = (290.0, 360.0)

def _require_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH; install ffmpeg (its rubberband filter drives the 1.4x pace)")


def _check_output(out_wav):
    if not os.path.exists(out_wav) or os.path.getsize(out_wav) == 0:
        raise RuntimeError(f"ffmpeg produced no audio at {out_wav}")


def stretch(in_wav, out_wav, tempo=TEMPO):
    _require_ffmpeg()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", in_wav, "-filter:a", f"rubberband=tempo={tempo}:pitch=1.0", out_wav], check=True)
    _check_output(out_wav)
    return out_wav

def trim_silence(in_wav, out_wav, thresh_db=-45):
    _require_ffmpeg()
    one = f"silenceremove=start_periods=1:start_threshold={thresh_db}dB"
    f = f"{one},areverse,{one},areverse"   # trim both edges only, never cut mid-line
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", in_wav, "-af", f, out_wav], check=True)
    _check_output(out_wav)
    return out_wav

def join_lines(wavs, out_wav, gap_s=GAP_S):
    wavs = list(wavs)
    if not wavs:
        raise ValueError("join_lines: no wavs to join")
    parts, sr0 = [], None
    for w in wavs:
        d, sr = sf.read(w)
        d = d if d.ndim == 1 else d.mean(axis=1)
        if sr0 is None:
            sr0 = sr
        elif sr != sr0:
            raise ValueError(f"sample rates must match across lines: {w} has {sr}, expected {sr0}")
        parts += [d, np.zeros(int(gap_s * sr))]
    sf.write(out_wav, np.concatenate(parts[:-1]), sr0)
    return out_wav

def phrase_wpm(words, min_words=4, max_gap=0.35):
    """Median words-per-minute across phrases. Empty input is 0.0 (measured
    silence, not a crash); zero/negative-duration phrases are skipped rather
    than dividing by zero."""
    words = list(words)
    if not words:
        return 0.0
    ph, cur = [], [words[0]]
    for a, b in zip(words, words[1:]):
        if b["start"] - a["end"] < max_gap: cur.append(b)
        else: ph.append(cur); cur = [b]
    ph.append(cur)
    rates = [len(p) / (p[-1]["end"] - p[0]["start"]) * 60 for p in ph
             if len(p) >= min_words and p[-1]["end"] > p[0]["start"]]
    return statistics.median(rates) if rates else 0.0

def gate(words, lo_hi=TARGET_PHRASE_WPM):
    w = phrase_wpm(words)
    return {"phrase_wpm": round(w), "ok": lo_hi[0] <= w <= lo_hi[1], "target": lo_hi}

def build_dialogue_track(raw_line_wavs, out_wav, workdir="/tmp"):
    """raw per-line TTS wavs -> trimmed, stretched, joined track + gate result (needs WhisperX env)."""
    from forge.audio.align import word_times
    done = []
    for i, w in enumerate(raw_line_wavs):
        t = trim_silence(w, f"{workdir}/l{i}_t.wav")
        done.append(stretch(t, f"{workdir}/l{i}_s.wav"))
    join_lines(done, out_wav)
    return gate(word_times(out_wav, model="base"))


def line_tempo(raw_wpm: float, target: float = 330.0, lo: float = 1.15, hi: float = 1.5) -> float:
    """Per-line tempo so fast TTS lines are not over-stretched and slow ones still reach the reel pace.
    Capped at 1.5 because the user judged anything above 1.5x too fast."""
    return round(max(lo, min(hi, target / max(raw_wpm, 1.0))), 3)

def build_track_perline(raw_wavs, raw_wpms, out_wav, workdir="/tmp", measure=None):
    """Trim edges, stretch each line by its own tempo, join with GAP_S. `measure(wav)->phrase WPM` runs the gate."""
    done = []
    for i, (w, r) in enumerate(zip(raw_wavs, raw_wpms)):
        t = trim_silence(w, f"{workdir}/pl{i}_t.wav")
        done.append(stretch(t, f"{workdir}/pl{i}_s.wav", tempo=line_tempo(r)))
    join_lines(done, out_wav)
    return gate(measure(out_wav)) if measure else None
