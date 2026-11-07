"""Episode assembly on MoviePy 2.x (MIT): concat shots, lay voice + ducked BGM, burn captions via ffmpeg."""
import os
import subprocess
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips, afx

def compose(shots, voice, bgm, out, bgm_gain=0.18, words=None, hooks=None, ass_kw=None,
            speaker_segments=None):
    """Assemble the episode. Optional m11 caption hierarchy: when `words`
    (dialogue timings) or `hooks` (hook/cliffhanger overlays) are given, the
    two-layer captions are burned in as part of the ordinary compose, via
    burn_caption_hierarchy. When `speaker_segments`
    ([{"speaker", "text", "start", "end"}]) are given, the
    speaker-differentiated captions (per-speaker style) are burned instead -
    they carry both colour and ">>" prefixes, so they replace the plain
    dialogue layer rather than stacking on it. Without any of them the
    output is exactly the pre-m11 assembly."""
    clips = [VideoFileClip(p) for p in shots]
    try:
        v = concatenate_videoclips(clips, method="compose")
        tracks = []
        if voice:
            va = AudioFileClip(voice); tracks.append(va)
        if bgm:
            b = AudioFileClip(bgm).with_effects([afx.MultiplyVolume(bgm_gain), afx.AudioLoop(duration=v.duration)])
            tracks.append(b)
        if tracks:
            v = v.with_audio(CompositeAudioClip(tracks).with_duration(v.duration))
        if words or hooks or speaker_segments:
            silent_out = out + ".nocaptions.mp4"
            v.write_videofile(silent_out, codec="libx264", audio_codec="aac", fps=30, preset="medium", logger=None)
        else:
            v.write_videofile(out, codec="libx264", audio_codec="aac", fps=30, preset="medium", logger=None)
    finally:
        for c in clips: c.close()
    if words or hooks or speaker_segments:
        try:
            if speaker_segments:
                burn_speaker_captions(silent_out, speaker_segments, out,
                                      **(ass_kw or {}))
            else:
                burn_caption_hierarchy(silent_out, words or [], hooks or [], out,
                                       **(ass_kw or {}))
        finally:
            if os.path.exists(silent_out):
                os.remove(silent_out)
    return out

def _escape_filter_path(path) -> str:
    """Escape a filesystem path for use inside an ffmpeg filtergraph.

    Colons, commas, brackets, semicolons, quotes, backslashes and spaces are
    all special to the filter parser (Colab's 'My Drive' paths hit this).
    Quoting the value and backslash-escaping quote/backslash keeps the ass=
    filter working for any path."""
    p = str(path).replace("\\", "\\\\").replace("'", "\\'")
    return "'" + p + "'"


def burn_captions(video, ass, out):
    """Final edit step. Captions are always burned AFTER any lip-sync pass:
    the sync model's face-restore region smears existing text pixels
    (observed on the m17 Kaggle run), so captioning a pre-synced video is
    the only safe order. There is no automatic burned-caption detection."""
    if not os.path.exists(ass):
        raise FileNotFoundError(f"caption file missing: {ass}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf",
                    f"ass={_escape_filter_path(ass)}",
                    "-c:v", "libx264", "-crf", "18", "-c:a", "copy", out], check=True)
    return out


def burn_speaker_captions(video, segments, out, ass_path=None, **ass_kw):
    """Burn per-speaker styled dialogue captions (forge.assemble.speaker_captions)
    onto an assembled video. Pure edit step: no generation, no credits. Pass
    margin_v in ass_kw when the source shots already carry burned captions so
    the new lines stack above them (manual placement, not detection)."""
    from forge.assemble.speaker_captions import write_speaker_ass
    ass_path = ass_path or (out + ".speaker.ass")
    write_speaker_ass(segments, ass_path, **ass_kw)
    return burn_captions(video, ass_path, out)


def burn_caption_hierarchy(video, words, hooks, out, ass_path=None, **ass_kw):
    """m11: burn the two-layer caption hierarchy (white dialogue + yellow
    hook/cliffhanger) onto an assembled video. Writes the ASS via
    forge.assemble.hook_captions, then reuses burn_captions. Pure edit step:
    no generation, no credits."""
    from forge.assemble.hook_captions import write_hierarchy_ass
    ass_path = ass_path or (out + ".captions.ass")
    write_hierarchy_ass(words, hooks, ass_path, **ass_kw)
    return burn_captions(video, ass_path, out)
