#!/usr/bin/env python
"""AI MicroDrama Series Generator CLI (run_series.py).

Features:
- Interactive Step-by-Step Terminal Wizard (when run without arguments)
- Full command-line flag support for CI/CD and scripted automation
- Automatic IP sanitization (Option B) for any copyrighted concepts
- Checkpoint persistence and resume capability
"""

import sys
import argparse
from pathlib import Path

# Safe Windows console encoding setup
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from microdrama.series.archetypes import ArchetypeSanitizer, GENRE_TAXONOMY
from microdrama.series_engine import SeriesEngine


def run_interactive_wizard():
    """Interactive Step-by-Step Terminal Wizard for launching a microdrama series."""
    print("=" * 65)
    print("[AI MICRODRAMA SERIES GENERATOR v2.1]")
    print("Built on Magic Hour API | Gemini Flash | DramaBench 500")
    print("=" * 65)
    print("Press Enter to accept defaults shown in [brackets].\n")

    # 1. Title
    raw_title = input("? Series Title [The Cold CEO's Contract Bride]: ").strip()
    title = raw_title if raw_title else "The Cold CEO's Contract Bride"

    # 2. Genre
    print("\nAvailable Genres:")
    for idx, (gk, ginfo) in enumerate(GENRE_TAXONOMY.items(), 1):
        print(f"  [{idx}] {gk:20} - {ginfo['display_name']}")
    raw_genre = input("? Select Genre (1-4 or name) [1 - contract_marriage]: ").strip()
    genre_map = {"1": "contract_marriage", "2": "revenge_comeback", "3": "arcane_academy", "4": "hidden_billionaire"}
    genre = genre_map.get(raw_genre, raw_genre if raw_genre else "contract_marriage")

    # 3. Episodes
    raw_episodes = input("\n? Number of Episodes to generate [10]: ").strip()
    try:
        episodes_count = int(raw_episodes) if raw_episodes else 10
    except ValueError:
        episodes_count = 10

    # 4. Cast Archetypes
    ginfo = ArchetypeSanitizer.get_genre_info(genre)
    def_prot = ginfo["default_protagonist"]["name"] + " - " + ginfo["default_protagonist"]["look"][:40]
    def_deut = ginfo["default_deuteragonist"]["name"] + " - " + ginfo["default_deuteragonist"]["look"][:40]
    def_ant = ginfo["default_antagonist"]["name"] + " - " + ginfo["default_antagonist"]["look"][:40]

    raw_p = input(f"\n? Protagonist [{def_prot}]: ").strip()
    protagonist = raw_p if raw_p else def_prot

    raw_d = input(f"? Deuteragonist [{def_deut}]: ").strip()
    deuteragonist = raw_d if raw_d else def_deut

    raw_a = input(f"? Antagonist [{def_ant}]: ").strip()
    antagonist = raw_a if raw_a else def_ant

    # 5. Production Mode
    print("\nProduction Modes:")
    print("  [1] Full Video Render with Burned-In ASS Subtitles (Uses Magic Hour Video API - Characters & Voice)")
    print("  [2] Screenplay & Storyboard Only (0 Credits, script & preview cards only)")
    raw_mode = input("? Select Mode [1]: ").strip()
    render_video = (raw_mode != "2")

    # Auto IP sanitization
    sanitized_title = ArchetypeSanitizer.sanitize_text(title)
    if sanitized_title != title:
        print(f"\n[IP SANITIZER]: Renamed protected IP '{title}' -> '{sanitized_title}'")
        title = sanitized_title

    print("\n" + "=" * 65)
    print(f"[INIT] Series: \"{title}\" ({episodes_count} Episodes)")
    print(f"[GENRE] {genre} | Mode: {'FULL VIDEO RENDER' if render_video else 'FREE STORYBOARD PREVIEW'}")
    print("=" * 65 + "\n")

    engine = SeriesEngine(
        series_name=title,
        genre=genre,
        protagonist=protagonist,
        deuteragonist=deuteragonist,
        antagonist=antagonist,
        render_video=render_video,
        episodes_count=episodes_count,
    )
    engine.generate_all_episodes()


def main():
    parser = argparse.ArgumentParser(
        description="AI MicroDrama Series Generator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--wizard", action="store_true", help="Launch interactive step-by-step wizard")
    parser.add_argument("--series-name", type=str, default="The Cold CEO's Contract Bride", help="Series title")
    parser.add_argument("--genre", type=str, default="contract_marriage", help="Genre slug (e.g. contract_marriage)")
    parser.add_argument("--episodes", type=int, default=10, help="Number of episodes (default: 10)")
    parser.add_argument("--start-ep", type=int, default=1, help="Starting episode number (default: 1)")
    parser.add_argument("--end-ep", type=int, default=None, help="Ending episode number (default: episodes count)")
    parser.add_argument("--protagonist", type=str, default=None, help="Protagonist description")
    parser.add_argument("--deuteragonist", type=str, default=None, help="Deuteragonist description")
    parser.add_argument("--antagonist", type=str, default=None, help="Antagonist description")
    parser.add_argument("--render-video", action="store_true", help="Render video clips via Magic Hour and stitch master")
    parser.add_argument("--storyboard-only", action="store_true", help="Generate scripts and storyboard cards without video")
    parser.add_argument("--mock", action="store_true", help="Run with mock LLM and mock video for offline testing")
    parser.add_argument("--regenerate", action="store_true", help="Force regenerate existing cached episodes")
    parser.add_argument("--model", type=str, default="ltx-2.5", help="Magic Hour video model (default: ltx-2.5)")
    parser.add_argument("--resolution", type=str, default="480p", help="Resolution: 480p, 720p, 1080p")

    # If run with no CLI arguments, default to interactive wizard
    if len(sys.argv) == 1:
        run_interactive_wizard()
        return

    args = parser.parse_args()

    if args.wizard:
        run_interactive_wizard()
        return

    # Check IP sanitization
    sanitized_name = ArchetypeSanitizer.sanitize_text(args.series_name)
    if sanitized_name != args.series_name:
        print(f"[IP SANITIZER] Converted '{args.series_name}' -> '{sanitized_name}'")

    render_video = not args.storyboard_only

    engine = SeriesEngine(
        series_name=sanitized_name,
        genre=args.genre,
        protagonist=args.protagonist,
        deuteragonist=args.deuteragonist,
        antagonist=args.antagonist,
        render_video=render_video,
        mock_mode=args.mock,
        model=args.model,
        resolution=args.resolution,
        episodes_count=args.episodes,
    )

    end_ep = args.end_ep or args.episodes
    engine.generate_all_episodes(
        start_ep=args.start_ep,
        end_ep=end_ep,
        force_regenerate=args.regenerate,
    )


if __name__ == "__main__":
    main()
