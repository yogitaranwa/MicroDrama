"""Episode video assembly and FFmpeg post-production pipeline.

Normalizes, stitches, and burns ReelShort styled ASS subtitles into master 9:16 vertical episodes.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from ..config import OUTPUT_DIR
from ..models import Shot, Screenplay
from .subtitle import SubtitleGenerator


def get_ffmpeg_binary() -> Optional[str]:
    """Discover FFmpeg executable from imageio-ffmpeg or system PATH."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except ImportError:
        pass

    system_exe = shutil.which("ffmpeg")
    if system_exe:
        return system_exe

    return None


class EpisodeAssembler:
    """Normalizes and stitches video clips into a master 9:16 microdrama episode with burned subtitles."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = get_ffmpeg_binary()

    def run_ffmpeg(self, args: List[str], cwd: Optional[Path] = None) -> None:
        """Run FFmpeg command with robust error capture."""
        if not self.ffmpeg_bin:
            raise RuntimeError(
                "FFmpeg executable not found. Install imageio-ffmpeg or ffmpeg in system PATH."
            )
        cmd = [self.ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y"] + [str(a) for a in args]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg failed with exit code {res.returncode}: {res.stderr}")

    @staticmethod
    def get_dimensions(aspect_ratio: str = "9:16") -> Tuple[int, int]:
        """Return (width, height) for target aspect ratio."""
        if aspect_ratio == "16:9":
            return (1280, 720)
        return (720, 1280)  # Standard high-quality 9:16 vertical mobile

    def extract_last_frame(self, clip_path: Path, out_frame_path: Path) -> Path:
        """Extract the exact ending frame from a shot clip for sequential i2v generation."""
        out_frame_path = Path(out_frame_path)
        out_frame_path.parent.mkdir(parents=True, exist_ok=True)
        # Seek near end (-sseof -0.1) and extract 1 frame
        args = [
            "-sseof", "-0.1",
            "-i", str(clip_path.resolve()),
            "-update", "1",
            "-frames:v", "1",
            "-q:v", "2",
            str(out_frame_path.resolve()),
        ]
        self.run_ffmpeg(args)
        return out_frame_path

    def clip_has_audio(self, clip_path: Path) -> bool:
        """Check whether a video clip contains an active audio stream."""
        if not self.ffmpeg_bin:
            return False
        res = subprocess.run(
            [self.ffmpeg_bin, "-hide_banner", "-i", str(clip_path.resolve())],
            capture_output=True,
            text=True,
        )
        return "Audio:" in res.stderr

    def assemble(
        self,
        screenplay: Screenplay,
        clip_paths: List[Path],
        out_master_path: Optional[Path] = None,
        ass_path: Optional[Path] = None,
        burn_subtitles: bool = True,
        voice_clips: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """Normalize, stitch, and burn ReelShort styled ASS subtitles into complete episode."""
        if len(clip_paths) != len(screenplay.shots):
            raise ValueError(
                f"Shot count mismatch: {len(screenplay.shots)} shots planned, {len(clip_paths)} clips provided."
            )

        for p in clip_paths:
            if not Path(p).is_file():
                raise FileNotFoundError(f"Missing shot clip: {p}")

        w, h = self.get_dimensions(screenplay.aspect_ratio)
        work_dir = self.output_dir / "assembly_tmp"
        work_dir.mkdir(parents=True, exist_ok=True)

        # 1. Normalize each clip: 720x1280, 24fps, yuv420p, 48kHz stereo AAC + Dialogue Mixing
        normalized_clips: List[Path] = []
        for i, (shot, clip_path) in enumerate(zip(screenplay.shots, clip_paths)):
            norm_clip = work_dir / f"norm_{shot.id}.mp4"
            vf_filter = (
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
            )

            # Resolve voice file for this shot if available
            v_clip: Optional[Path] = None
            if voice_clips and shot.id in voice_clips:
                v_clip = Path(voice_clips[shot.id])
            else:
                candidate = clip_path.parent.parent / "voices" / f"{shot.id}_voice.wav"
                if candidate.exists():
                    v_clip = candidate

            has_audio = self.clip_has_audio(clip_path)

            if v_clip and v_clip.exists():
                if has_audio:
                    # Video ambient audio + spoken voice audio mixed
                    filter_complex = (
                        f"[0:v]{vf_filter}[vout];"
                        f"[0:a]volume=0.35[bg];"
                        f"[1:a]volume=1.6[voice];"
                        f"[bg][voice]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                    )
                    args = [
                        "-i", str(clip_path.resolve()),
                        "-i", str(v_clip.resolve()),
                        "-filter_complex", filter_complex,
                        "-map", "[vout]",
                        "-map", "[aout]",
                        "-r", "24",
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-pix_fmt", "yuv420p",
                        "-c:a", "aac",
                        "-ar", "48000",
                        "-ac", "2",
                        str(norm_clip.resolve()),
                    ]
                else:
                    # Video has no audio, use voice audio directly
                    filter_complex = f"[0:v]{vf_filter}[vout]"
                    args = [
                        "-i", str(clip_path.resolve()),
                        "-i", str(v_clip.resolve()),
                        "-filter_complex", filter_complex,
                        "-map", "[vout]",
                        "-map", "1:a",
                        "-r", "24",
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-pix_fmt", "yuv420p",
                        "-c:a", "aac",
                        "-ar", "48000",
                        "-ac", "2",
                        str(norm_clip.resolve()),
                    ]
            else:
                if has_audio:
                    args = [
                        "-i", str(clip_path.resolve()),
                        "-vf", vf_filter,
                        "-r", "24",
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-pix_fmt", "yuv420p",
                        "-c:a", "aac",
                        "-ar", "48000",
                        "-ac", "2",
                        str(norm_clip.resolve()),
                    ]
                else:
                    args = [
                        "-i", str(clip_path.resolve()),
                        "-f", "lavfi", "-t", str(shot.duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                        "-vf", vf_filter,
                        "-map", "0:v",
                        "-map", "1:a",
                        "-r", "24",
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-pix_fmt", "yuv420p",
                        "-c:a", "aac",
                        "-ar", "48000",
                        "-ac", "2",
                        str(norm_clip.resolve()),
                    ]
            self.run_ffmpeg(args)
            normalized_clips.append(norm_clip)

        # 2. Concat demuxer lossless join
        concat_list = work_dir / "concat_list.txt"
        concat_list.write_text(
            "".join(f"file '{p.name}'\n" for p in normalized_clips),
            encoding="utf-8",
        )

        unburned_master = work_dir / "unburned_master.mp4"
        self.run_ffmpeg(
            [
                "-f", "concat",
                "-safe", "0",
                "-i", "concat_list.txt",
                "-c", "copy",
                "-movflags", "+faststart",
                str(unburned_master.name),
            ],
            cwd=work_dir,
        )

        # 3. Determine final output destination
        final_master = out_master_path or (self.output_dir / f"episode_{screenplay.episode_number:02d}_master.mp4")
        final_master.parent.mkdir(parents=True, exist_ok=True)

        # 4. Burn styled ASS subtitles if requested
        if burn_subtitles and ass_path and Path(ass_path).exists():
            # Copy ass to work_dir to prevent Windows colon path issues in FFmpeg filter
            tmp_ass = work_dir / "subtitles.ass"
            shutil.copy2(ass_path, tmp_ass)

            # Apply subtitle filter and -14 LUFS loudness normalization
            args = [
                "-i", str(unburned_master.resolve()),
                "-vf", "subtitles=subtitles.ass",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "22",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(final_master.resolve()),
            ]
            self.run_ffmpeg(args, cwd=work_dir)
        else:
            # Move unburned master directly to final destination
            shutil.copy2(unburned_master, final_master)

        # Cleanup temporary concat files
        shutil.rmtree(work_dir, ignore_errors=True)

        return final_master
