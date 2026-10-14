"""Microdrama subtitle generator supporting ReelShort styled ASS and standard SRT."""

from pathlib import Path
from typing import Dict, List, Optional
from ..models import Screenplay


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds into standard SRT timestamp HH:MM:SS,mmm."""
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def format_ass_timestamp(seconds: float) -> str:
    """Format seconds into standard ASS timestamp H:MM:SS.cc."""
    cs = round(seconds * 100)
    hours, cs = divmod(cs, 360000)
    minutes, cs = divmod(cs, 6000)
    secs, cs = divmod(cs, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{cs:02}"


# Default speaker colors in BGR hex format for ASS (&H00BBGGRR&)
DEFAULT_SPEAKER_COLORS: Dict[str, str] = {
    "Seraphina": "&H00E8C8FF&",  # Soft Champagne Gold
    "Alexander": "&H00FFFF00&",  # Ice Cyan
    "Victoria": "&H005A33FF&",   # Crimson Coral
    "Protagonist": "&H00E8C8FF&",
    "Deuteragonist": "&H00FFFF00&",
    "Antagonist": "&H005A33FF&",
    "Default": "&H00FFFFFF&",     # Crisp White
}


class SubtitleGenerator:
    """Generates styled ASS and SRT subtitle tracks for microdrama episodes."""

    @staticmethod
    def generate_srt(screenplay: Screenplay, out_file: Optional[Path] = None) -> str:
        """Create timed dialogue SRT file."""
        subtitles: List[str] = []
        current_time = 0.0
        sub_index = 1

        for shot in screenplay.shots:
            shot_duration = float(shot.duration)
            if shot.dialogue and shot.dialogue.strip():
                speaker_tag = f"{shot.speaker}: " if shot.speaker else ""
                text = f"{speaker_tag}{shot.dialogue.strip()}"
                
                # Active dialogue span: first 70% of shot duration
                start_str = format_srt_timestamp(current_time)
                end_str = format_srt_timestamp(current_time + min(shot_duration, max(2.5, len(text.split()) * 0.4)))

                block = f"{sub_index}\n{start_str} --> {end_str}\n{text}\n"
                subtitles.append(block)
                sub_index += 1

            current_time += shot_duration

        srt_content = "\n".join(subtitles)
        if out_file:
            out_file = Path(out_file)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(srt_content, encoding="utf-8")

        return srt_content

    @staticmethod
    def generate_ass(
        screenplay: Screenplay,
        out_file: Optional[Path] = None,
        custom_colors: Optional[Dict[str, str]] = None,
        safe_margin_bottom: int = 120,
    ) -> str:
        """Create ReelShort/DramaBox styled ASS subtitles burned directly into vertical 9:16 master.

        Features:
        - Lower-middle safe zone placement (MarginV=120) above mobile UI
        - Speaker name highlighted in bold with distinct character color
        - Crisp black outline & shadow for high contrast on all scenes
        """
        colors = {**DEFAULT_SPEAKER_COLORS, **(custom_colors or {})}

        # Build unique style entries for each character
        known_speakers = {s.speaker for s in screenplay.shots if s.speaker}
        style_lines = [
            f"Style: Default,Trebuchet MS,24,{colors.get('Default', '&H00FFFFFF&')},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,30,30,{safe_margin_bottom},1"
        ]

        for spk in known_speakers:
            col = colors.get(spk, colors.get("Default", "&H00FFFFFF&"))
            style_lines.append(
                f"Style: {spk},Trebuchet MS,24,{col},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,30,30,{safe_margin_bottom},1"
            )

        header = f"""[Script Info]
Title: {screenplay.title}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{chr(10).join(style_lines)}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        current_time = 0.0

        for shot in screenplay.shots:
            shot_duration = float(shot.duration)
            if shot.dialogue and shot.dialogue.strip():
                speaker = shot.speaker.strip()
                style_name = speaker if speaker in known_speakers else "Default"
                
                start_ts = format_ass_timestamp(current_time)
                # Display length based on word count
                active_len = min(shot_duration, max(2.5, len(shot.dialogue.split()) * 0.42))
                end_ts = format_ass_timestamp(current_time + active_len)

                # Format on-screen line: {\b1}SPEAKER: {\b0}Dialogue text
                if speaker:
                    display_text = f"{{\\b1}}{speaker}: {{\\b0}}{shot.dialogue.strip()}"
                else:
                    display_text = shot.dialogue.strip()

                line = f"Dialogue: 0,{start_ts},{end_ts},{style_name},{speaker},0,0,0,,{display_text}"
                events.append(line)

            current_time += shot_duration

        ass_content = header + "\n".join(events) + "\n"

        if out_file:
            out_file = Path(out_file)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(ass_content, encoding="utf-8")

        return ass_content
