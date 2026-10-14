"""Free silent storyboard card and preview generator using Pillow."""

import textwrap
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont
from ..models import Screenplay, Shot
from ..config import OUTPUT_DIR


def get_font(size: int = 20) -> ImageFont.ImageFont:
    """Load default or scalable font."""
    try:
        return ImageFont.load_default(size=size)
    except (TypeError, OSError):
        return ImageFont.load_default()


class StoryboardGenerator:
    """Generates 9:16 vertical storyboard cards for screenplays without API cost."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (OUTPUT_DIR / "storyboard")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_shot_card(self, shot: Shot, screenplay: Screenplay, width: int = 540, height: int = 960) -> Path:
        """Render a single 9:16 vertical storyboard card."""
        im = Image.new("RGB", (width, height), "#141416")
        draw = ImageDraw.Draw(im)

        # Draw outer decorative frame
        draw.rounded_rectangle((16, 16, width - 16, height - 16), radius=16, outline="#2a2a30", width=2)
        draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=12, fill="#1c1c20")

        # Top badge
        draw.rounded_rectangle((36, 36, width - 36, 76), radius=8, fill="#e50914")
        font_badge = get_font(18)
        draw.text((48, 44), "MICRODRAMA PREVIEW • ZERO-COST STORYBOARD", font=font_badge, fill="#ffffff")

        # Shot ID & Beat Info
        font_title = get_font(28)
        draw.text((40, 96), f"{shot.id.upper()} • {shot.duration}s", font=font_title, fill="#ffffff")
        
        font_sub = get_font(18)
        draw.text((40, 134), f"Beat: {shot.beat or 'Dramatic Action'} | Genre: {screenplay.genre}", font=font_sub, fill="#a0a0ab")

        # Divider
        draw.line((40, 166, width - 40, 166), fill="#2e2e38", width=1)

        y = 186
        sections = [
            ("VISUAL SETTING", shot.visual, "#f4f4f5"),
            ("PHYSICAL ACTION", shot.action, "#fbbf24"),
            ("CAMERA (9:16)", shot.camera, "#38bdf8"),
            ("CONTINUITY", shot.continuity or "Preserve fixed character look", "#94a3b8"),
            ("AUDIO / SFX", shot.audio, "#a78bfa"),
        ]

        wrap_width = 38
        for label, content, color in sections:
            font_lbl = get_font(14)
            draw.text((40, y), label, font=font_lbl, fill="#71717a")
            y += 20

            font_body = get_font(18)
            wrapped_lines = textwrap.wrap(content, width=wrap_width)
            for line in wrapped_lines:
                if y > height - 180:
                    break
                draw.text((40, y), line, font=font_body, fill=color)
                y += 24
            y += 12

        # Dialogue Box (Bottom Safe Area)
        if shot.dialogue and shot.dialogue.strip():
            box_top = height - 160
            draw.rounded_rectangle((36, box_top, width - 36, height - 48), radius=10, fill="#27272e", outline="#f59e0b", width=2)
            speaker_label = f"{shot.speaker or 'SPEAKER'}:"
            draw.text((48, box_top + 12), speaker_label, font=get_font(16), fill="#f59e0b")
            
            diag_lines = textwrap.wrap(f'"{shot.dialogue.strip()}"', width=wrap_width)
            dy = box_top + 36
            for line in diag_lines:
                draw.text((48, dy), line, font=get_font(20), fill="#ffffff")
                dy += 26
        else:
            draw.text((40, height - 80), "(No spoken dialogue in this shot)", font=get_font(16), fill="#52525b")

        out_path = self.output_dir / f"{shot.id}_storyboard.png"
        im.save(out_path, format="PNG")
        return out_path

    def render_full_storyboard(self, screenplay: Screenplay) -> List[Path]:
        """Render all storyboard cards for the episode."""
        paths = []
        for shot in screenplay.shots:
            p = self.render_shot_card(shot, screenplay)
            paths.append(p)
        return paths
