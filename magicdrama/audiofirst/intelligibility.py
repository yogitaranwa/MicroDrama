"""Does the film actually say the script? Local speech recognition compared with the written lines.

Runs faster-whisper on CPU (model downloaded once). Word error rate and the transcript are signal facts about
intelligibility to a recogniser: a high error rate means the words are garbled, wrong, missing or repeated. A low error
rate does not prove the voice sounds good or the lips match.
"""
import re
import subprocess

import numpy as np

from .native_mix import ffmpeg_exe

_MODEL = {}


def _words(text):
    return re.findall(r"[a-z0-9']+", text.lower().replace('’', "'"))


def word_error_rate(expected, heard):
    """Word-level edit distance divided by the number of expected words. Missing, wrong and extra words all count."""
    ref, hyp = _words(expected), _words(heard)
    if not ref:return 0.0 if not hyp else 1.0
    d = np.zeros((len(ref) + 1, len(hyp) + 1), dtype=int)
    d[:, 0] = range(len(ref) + 1);d[0, :] = range(len(hyp) + 1)
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    return float(d[len(ref), len(hyp)] / len(ref))


def transcribe(path, start=0.0, seconds=None, model_size='base.en'):
    """[{start,end,text}] word-level segments for a clip window."""
    from faster_whisper import WhisperModel
    if model_size not in _MODEL:_MODEL[model_size] = WhisperModel(model_size, device='cpu', compute_type='int8')
    cmd = [ffmpeg_exe(), '-v', 'error', '-nostdin', '-ss', f'{start:.3f}']
    if seconds is not None:cmd += ['-t', f'{seconds:.3f}']
    raw = subprocess.run(cmd + ['-i', str(path), '-vn', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    segments, _ = _MODEL[model_size].transcribe(audio, language='en', word_timestamps=True, vad_filter=False, beam_size=5)
    return [{'start': round(w.start, 2), 'end': round(w.end, 2), 'text': w.word.strip()} for s in segments for w in (s.words or [])]


def check_script(path, expected_lines, start=0.0, seconds=None, max_wer=0.35):
    """Compare what a clip says with the lines it should say, in order. WER above `max_wer` means not understandable."""
    words = transcribe(path, start, seconds)
    heard = ' '.join(w['text'] for w in words)
    expected = ' '.join(expected_lines)
    wer = word_error_rate(expected, heard)
    return {'expected': expected, 'heard': heard, 'wer': round(wer, 2), 'understandable': wer <= max_wer, 'words': words,
            'scope': 'Recogniser agreement with the script only; not voice quality, acting or lip sync.'}


def caption_cues_from_words(words, expected_lines, pad=0.25):
    """One cue per script line, timed from the recogniser's own word times (not guessed). The caption text is the script line,
    so a small recogniser slip never reaches the screen. Words are handed to lines in order by expected word count."""
    cues, i = [], 0
    for line in expected_lines:
        n = max(len(_words(line)), 1)
        chunk = words[i:i + n];i += n
        if not chunk:continue
        cues.append({'start': round(chunk[0]['start'], 2), 'end': round(chunk[-1]['end'] + pad, 2), 'text': line})
    return cues
