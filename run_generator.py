"""CLI runner for AI Micro Drama Generator."""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.microdrama.engine import MicrodramaEngine
from src.microdrama.templates import list_templates


def main():
    parser = argparse.ArgumentParser(
        description="AI Micro Drama Generator — Generate viral vertical (9:16) microdrama episodes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="An unsuspecting protagonist finds an impossible note in their own handwriting warning: DO NOT OPEN THE DOOR.",
        help="Story premise, plot outline, or specific instructions.",
    )
    parser.add_argument(
        "--template",
        type=str,
        default="thriller_loop",
        choices=[t.id for t in list_templates()] + ["none"],
        help="Pre-engineered microdrama trope template.",
    )
    parser.add_argument(
        "--char-image",
        type=str,
        default=None,
        help="Path to character reference image for face/wardrobe consistency.",
    )
    parser.add_argument(
        "--char-name",
        type=str,
        default="Protagonist",
        help="Name of the character for the reference image.",
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=8,
        help="Total number of shots in the episode (1-12).",
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=8,
        help="Duration in seconds per shot (typically 5-10s).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="ltx-2.5",
        help="Magic Hour video model (e.g. ltx-2.5, kling-2.6, kling-3.0, wan-2.2).",
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default="480p",
        choices=["480p", "720p", "1080p"],
        help="Target video resolution.",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="gemini",
        choices=["gemini", "openai", "mock"],
        help="LLM provider for scriptwriting.",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="gemini-3.5-flash",
        help="Specific LLM model to use (default: gemini-3.5-flash).",
    )
    parser.add_argument(
        "--episode",
        type=int,
        default=1,
        help="Episode number in the microdrama series (e.g. 1, 2, 3).",
    )
    parser.add_argument(
        "--prev-screenplay",
        type=str,
        default=None,
        help="Path to previous episode screenplay JSON to automatically pull cliffhanger & context.",
    )
    parser.add_argument(
        "--prev-cliffhanger",
        type=str,
        default=None,
        help="Custom previous cliffhanger description to resolve in Shot 1.",
    )
    parser.add_argument(
        "--storyboard-only",
        action="store_true",
        help="Generate screenplay and free 9:16 visual storyboard cards only (zero API video cost).",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run fully offline simulation without calling live APIs.",
    )

    args = parser.parse_args()

    template_id = None if args.template == "none" else args.template
    reference_images = {args.char_name: args.char_image} if args.char_image else None

    print("\n" + "=" * 60)
    print(f"AI MICRO DRAMA GENERATOR — EPISODE {args.episode}")
    print(f"* Template: {args.template}")
    print(f"* Shots: {args.shots} x {args.seconds}s (~{args.shots * args.seconds}s episode)")
    print(f"* Video Model: {args.model} ({args.resolution})")
    print(f"* LLM Writer: {args.provider} ({args.llm_model})")
    print(f"* Reference Image: {args.char_image or 'None'}")
    if args.episode > 1:
        print(f"* Series Continuity: Continuing from Episode {args.episode - 1}")
    print("=" * 60 + "\n")

    engine = MicrodramaEngine(
        llm_provider=args.provider,
        llm_model=args.llm_model,
        mock_mode=args.mock,
    )

    result = engine.generate_episode(
        story_prompt=args.prompt,
        template_id=template_id,
        reference_images=reference_images,
        shot_count=args.shots,
        seconds_per_shot=args.seconds,
        model=args.model,
        resolution=args.resolution,
        render_video=not args.storyboard_only,
        episode_number=args.episode,
        previous_cliffhanger=args.prev_cliffhanger,
        previous_screenplay_path=args.prev_screenplay,
    )

    screenplay = result["screenplay"]
    print("\n" + "=" * 60)
    print(f"SCREENPLAY GENERATED: {screenplay.title}")
    print(f"Logline: {screenplay.logline}")
    print(f"Hook: {screenplay.hook}")
    print(f"Cliffhanger: {screenplay.cliffhanger}")
    print("-" * 60)
    for s in screenplay.shots:
        diag = f'"{s.dialogue}"' if s.dialogue else "(no dialogue)"
        print(f"[{s.id}] {s.duration}s | {s.speaker or 'Narrative'}: {diag}")
        print(f"     Action: {s.action}")
        print(f"     Camera: {s.camera}")
    print("=" * 60)
    print(f"Storyboard cards saved in: outputs/storyboard/")
    print(f"Subtitle file: {result['subtitles_srt']}")
    if result.get("master_mp4"):
        print(f"Master Episode: {result['master_mp4']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
