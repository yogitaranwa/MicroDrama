"""High-level Orchestrator for the AI Micro Drama Generator."""

from pathlib import Path
from typing import Dict, List, Optional, Any
from .models import Character, Screenplay, QualityScore
from .templates import get_template, list_templates
from .narrative import Screenwriter, MicrodramaJudge
from .client import MagicHourGenerator, AssetManager
from .postprod import StoryboardGenerator, SubtitleGenerator, EpisodeAssembler
from .config import OUTPUT_DIR, DEFAULT_MODEL, DEFAULT_RESOLUTION


class MicrodramaEngine:
    """End-to-end MicroDrama Generation Pipeline."""

    def __init__(
        self,
        magic_hour_api_key: Optional[str] = None,
        llm_provider: str = "gemini",
        llm_model: str = "gemini-3.5-flash",
        llm_api_key: Optional[str] = None,
        mock_mode: bool = False,
    ):
        self.mock_mode = mock_mode
        self.screenwriter = Screenwriter(
            provider="mock" if mock_mode else llm_provider,
            model=llm_model,
            api_key=llm_api_key,
        )
        self.generator = MagicHourGenerator(
            api_key=magic_hour_api_key,
            mock_mode=mock_mode,
        )
        self.asset_manager = AssetManager(magic_hour_client=self.generator.client)
        self.storyboard_gen = StoryboardGenerator()
        self.assembler = EpisodeAssembler()

    def generate_episode(
        self,
        story_prompt: str,
        template_id: Optional[str] = None,
        reference_images: Optional[Dict[str, str]] = None,
        specific_scenes: Optional[List[str]] = None,
        shot_count: int = 8,
        seconds_per_shot: int = 8,
        model: str = DEFAULT_MODEL,
        resolution: str = DEFAULT_RESOLUTION,
        render_video: bool = True,
        episode_number: int = 1,
        previous_cliffhanger: Optional[str] = None,
        previous_screenplay_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the complete microdrama generation pipeline."""
        print(f"[1/5] Initializing template & character assets (Episode {episode_number})...")
        template = get_template(template_id) if template_id else None

        # Resolve previous episode cliffhanger if continuing a series
        if previous_screenplay_path and Path(previous_screenplay_path).exists():
            try:
                import json
                with open(previous_screenplay_path, "r", encoding="utf-8") as f:
                    prev_data = json.load(f)
                    if not previous_cliffhanger:
                        previous_cliffhanger = prev_data.get("cliffhanger")
                print(f"   Loaded Episode {episode_number - 1} cliffhanger: \"{previous_cliffhanger}\"")
            except Exception as e:
                print(f"[WARN] Could not parse previous screenplay: {e}")
        elif episode_number > 1 and not previous_cliffhanger:
            # Fallback to signature cliffhanger if continuing without file
            if template and template.cliffhanger_formulas:
                previous_cliffhanger = template.cliffhanger_formulas[0]
            else:
                previous_cliffhanger = "Protagonist corners the rival with shocking evidence."
            print(f"   Auto-assigned Episode {episode_number - 1} cliffhanger: \"{previous_cliffhanger}\"")
        
        # Build cast with reference images attached
        cast: List[Character] = []
        if template:
            cast = [c.model_copy() for c in template.default_cast]
        else:
            cast = [
                Character(
                    name="Protagonist",
                    role="Protagonist",
                    look="Striking face, sharp intense eyes, stylish outfit",
                    voice="Urgent, sharp",
                )
            ]

        # Attach user reference images to matching character names or protagonist
        if reference_images:
            for char_name, img_path in reference_images.items():
                matched = False
                for c in cast:
                    if c.name.lower() == char_name.lower():
                        c.reference_image_path = str(img_path)
                        matched = True
                        break
                if not matched and cast:
                    # Attach to primary character if only one provided
                    cast[0].reference_image_path = str(img_path)

        # Upload reference images to Magic Hour
        cast = self.asset_manager.prepare_cast_references(cast)

        print(f"[2/5] Writing high-stakes microdrama screenplay for Episode {episode_number}...")
        screenplay = self.screenwriter.generate_screenplay(
            story_idea=story_prompt,
            cast=cast,
            template=template,
            shot_count=shot_count,
            seconds_per_shot=seconds_per_shot,
            aspect_ratio="9:16",
            specific_scenes=specific_scenes,
            episode_number=episode_number,
            previous_cliffhanger=previous_cliffhanger,
        )

        print("[3/5] Evaluating script against DramaBench microdrama metrics...")
        score = MicrodramaJudge.evaluate(screenplay)
        print(f"   Quality Score: Hook={score.hook_score}/5 | Cliffhanger={score.cliffhanger_score}/5 | Dialogue={score.dialogue_score}/5")

        print("[4/5] Generating zero-cost visual storyboard cards...")
        card_paths = self.storyboard_gen.render_full_storyboard(screenplay)
        clean_title = screenplay.title.replace(" ", "_").replace("'", "").replace(":", "")
        srt_path = OUTPUT_DIR / f"{clean_title}.srt"
        SubtitleGenerator.generate_srt(screenplay, srt_path)

        # Save screenplay JSON for automated series continuity & inspection
        screenplay_json_path = OUTPUT_DIR / f"{clean_title}_screenplay.json"
        with open(screenplay_json_path, "w", encoding="utf-8") as f:
            f.write(screenplay.model_dump_json(indent=2))
        print(f"   Saved {len(card_paths)} storyboard cards, subtitles ({srt_path.name}), and {screenplay_json_path.name}")

        result: Dict[str, Any] = {
            "screenplay": screenplay,
            "screenplay_json": screenplay_json_path,
            "quality_score": score,
            "storyboard_cards": card_paths,
            "subtitles_srt": srt_path,
            "clips": [],
            "master_mp4": None,
        }

        if not render_video:
            print("[INFO] Storyboard ready. Video generation skipped per user request.")
            return result

        print("[5/5] Generating video clips via Magic Hour API...")
        manifest = self.generator.build_shot_manifest(
            screenplay=screenplay,
            model=model,
            resolution=resolution,
            audio=True,
        )

        clip_paths = []
        for i, item in enumerate(manifest, 1):
            shot_id = item["shot_id"]
            print(f"   Rendering shot {i}/{len(manifest)} ({shot_id})...")
            clip_path = self.generator.run_shot(item)
            clip_paths.append(clip_path)

        result["clips"] = clip_paths

        # Post-production assembly if clips are real video files
        if not self.mock_mode and self.assembler.ffmpeg_bin:
            print("[POST-PROD] Assembling vertical 9:16 master episode...")
            master_mp4 = self.assembler.assemble(
                screenplay=screenplay,
                clip_paths=clip_paths,
                out_filename=f"{screenplay.title.replace(' ', '_')}_master.mp4",
            )
            result["master_mp4"] = master_mp4
            print(f"[SUCCESS] Episode complete! Master output: {master_mp4}")
        else:
            print("[INFO] Clips saved. Run FFmpeg assembly to stitch final master MP4.")

        return result
