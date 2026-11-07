"""Episode assembly on MoviePy 2.x (MIT): concat shots, lay voice + ducked BGM, burn captions via ffmpeg."""
import subprocess
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips, afx

def compose(shots, voice, bgm, out, bgm_gain=0.18):
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
        v.write_videofile(out, codec="libx264", audio_codec="aac", fps=30, preset="medium", logger=None)
    finally:
        for c in clips: c.close()
    return out

def burn_captions(video, ass, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"ass={ass}",
                    "-c:v", "libx264", "-crf", "18", "-c:a", "copy", out], check=True)
    return out
