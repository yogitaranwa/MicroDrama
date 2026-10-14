"""Series Engine: High-level Orchestrator for 10-Episode Continuous Microdrama Series."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Character, Screenplay, GenreTemplate, QualityScore
from .templates import get_template
from .narrative import Screenwriter
from .client import MagicHourGenerator, AssetManager, VoiceManager
from .postprod import StoryboardGenerator, SubtitleGenerator, EpisodeAssembler
from .series import (
    SeriesOrganizer,
    SeriesBibleManager,
    ArcPlanner,
    ArchetypeSanitizer,
    ContinuityValidator,
    SemanticVerificationRunner,
)


class SeriesEngine:
    """End-to-end multi-episode microdrama generator with Bible continuity and FFmpeg stitching."""

    def __init__(
        self,
        series_name: str = "The Cold CEO's Contract Bride",
        genre: str = "contract_marriage",
        base_dir: Optional[Path] = None,
        protagonist: Optional[str] = None,
        deuteragonist: Optional[str] = None,
        antagonist: Optional[str] = None,
        render_video: bool = False,
        use_frame_extraction: bool = True,
        mock_mode: bool = False,
        model: str = "ltx-2.5",
        resolution: str = "480p",
        episodes_count: int = 10,
    ):
        self.series_name = series_name
        self.genre = genre.lower().replace(" ", "_")
        self.render_video = render_video
        self.use_frame_extraction = use_frame_extraction
        self.mock_mode = mock_mode
        self.model = model
        self.resolution = resolution
        self.episodes_count = episodes_count

        # 1. Setup Organizer
        self.organizer = SeriesOrganizer(self.series_name, base_dir=base_dir)
        self.organizer.ensure_series_structure(episodes_count=self.episodes_count)

        # 2. Setup or Load Series Bible
        self.bible = SeriesBibleManager(self.organizer.get_bible_path())
        genre_info = ArchetypeSanitizer.get_genre_info(self.genre)

        if not self.bible.bible_path.exists() or not self.bible.state.characters:
            # Build cast
            p_data = genre_info.get("default_protagonist", {})
            d_data = genre_info.get("default_deuteragonist", {})
            a_data = genre_info.get("default_antagonist", {})

            if protagonist:
                p_data = {**p_data, "name": protagonist.split("-")[0].strip(), "look": protagonist}
            if deuteragonist:
                d_data = {**d_data, "name": deuteragonist.split("-")[0].strip(), "look": deuteragonist}
            if antagonist:
                a_data = {**a_data, "name": antagonist.split("-")[0].strip(), "look": antagonist}

            # Sanitize any copyrighted IP
            initial_cast = [
                ArchetypeSanitizer.sanitize_dict(p_data),
                ArchetypeSanitizer.sanitize_dict(d_data),
                ArchetypeSanitizer.sanitize_dict(a_data),
            ]

            self.bible.initialize_series(
                title=self.series_name,
                genre=self.genre,
                logline=f"High-stakes {genre_info.get('display_name', self.genre)} microdrama series.",
                target_episodes=self.episodes_count,
                initial_characters=initial_cast,
            )

        # Check and bind canonical character reference portraits
        char_dir = self.organizer.series_dir / "characters"
        char_dir.mkdir(parents=True, exist_ok=True)
        for char_name, b_char in self.bible.state.characters.items():
            if not b_char.reference_image_path:
                for cand in char_dir.glob(f"{char_name.lower()}*.*"):
                    if cand.suffix.lower() in (".png", ".jpg", ".jpeg"):
                        b_char.reference_image_path = str(cand.resolve())
                        break

        # 3. Setup Arc Plan
        if self.genre == "contract_marriage":
            self.arc_plan = ArcPlanner.plan_contract_marriage_10(self.series_name)
        else:
            self.arc_plan = ArcPlanner.plan_custom_series(
                title=self.series_name,
                genre=self.genre,
                protagonist=protagonist or "Protagonist",
                deuteragonist=deuteragonist or "Deuteragonist",
                antagonist=antagonist or "Antagonist",
                episodes_count=self.episodes_count,
            )

        # 4. Save Netflix-style metadata
        self.organizer.save_metadata({
            "series_id": self.organizer.series_slug,
            "title": self.series_name,
            "genre": self.genre,
            "category": genre_info.get("category", "Drama"),
            "mood": genre_info.get("mood", "Intense, thrilling"),
            "themes": genre_info.get("themes", []),
            "episodes_count": self.episodes_count,
            "episode_duration_sec": 64,
            "cast": [
                {"name": c.name, "role": c.role, "archetype": c.archetype}
                for c in self.bible.state.characters.values()
            ],
        })

        # 5. Production Sub-engines
        self.screenwriter = Screenwriter(
            provider="mock" if self.mock_mode else "gemini",
            model="gemini-3.5-flash",
        )
        self.generator = MagicHourGenerator(mock_mode=self.mock_mode)
        self.storyboard_gen = StoryboardGenerator(output_dir=None)
        self.assembler = EpisodeAssembler()
        self.voice_manager = VoiceManager(
            magic_hour_client=self.generator.client if not self.mock_mode else None,
            mock_mode=self.mock_mode,
        )

    def generate_episode(
        self,
        episode_number: int,
        force_regenerate: bool = False,
    ) -> Dict[str, Any]:
        """Generate a single episode end-to-end within the series arc."""
        print(f"\n=======================================================")
        print(f"[SERIES] GENERATING EPISODE {episode_number}/{self.episodes_count}: {self.series_name}")
        print(f"=======================================================")

        screenplay_path = self.organizer.get_screenplay_path(episode_number)
        master_path = self.organizer.get_master_path(episode_number)
        ass_path = self.organizer.get_subtitles_path(episode_number, "ass")
        srt_path = self.organizer.get_subtitles_path(episode_number, "srt")
        continuity_path = self.organizer.get_continuity_report_path(episode_number)
        quality_path = self.organizer.get_quality_scores_path(episode_number)
        semantic_path = self.organizer.get_semantic_test_path(episode_number)

        # 1. Check existing completion
        if not force_regenerate and screenplay_path.exists():
            if not self.render_video or (master_path.exists() and master_path.stat().st_size > 1_000_000):
                print(f"[CACHE] Episode {episode_number} already completed. Loading from disk.")
                with open(screenplay_path, "r", encoding="utf-8") as f:
                    cached_sp = Screenplay.model_validate_json(f.read())
                return {
                    "episode_number": episode_number,
                    "title": cached_sp.title,
                    "screenplay_path": str(screenplay_path),
                    "master_path": str(master_path) if master_path.exists() else None,
                    "status": "CACHED",
                }

        # 2. Retrieve arc beat plan
        arc_beat = None
        if self.arc_plan.episodes and episode_number <= len(self.arc_plan.episodes):
            arc_beat = self.arc_plan.episodes[episode_number - 1]

        prompt_premise = (
            f"{arc_beat.act_phase}: {arc_beat.core_objective}. "
            f"Twist: {arc_beat.escalation_twist}. "
            f"Ending cliffhanger: {arc_beat.cliffhanger_prompt}"
            if arc_beat
            else f"High tension escalation in Episode {episode_number}."
        )

        cast_list = [
            Character(
                name=c.name,
                role=c.role,
                look=c.look,
                voice=c.voice,
                reference_image_path=c.reference_image_path,
                api_asset_path=c.api_asset_path,
            )
            for c in self.bible.state.characters.values()
        ]
        template = get_template(self.genre)

        # Load previous screenplay for continuity checks if ep > 1
        prev_sp: Optional[Screenplay] = None
        if episode_number > 1:
            prev_sp_path = self.organizer.get_screenplay_path(episode_number - 1)
            if prev_sp_path.exists():
                with open(prev_sp_path, "r", encoding="utf-8") as f:
                    prev_sp = Screenplay.model_validate_json(f.read())

        # 3. Stage 1 & 2: Generate Screenplay with Multi-Pass Review
        print(f"[STAGE 1/4] Writing & Reviewing Screenplay (Bible Continuity Loop)...")
        screenplay, cont_report, qscore = self.screenwriter.generate_screenplay_with_review(
            story_idea=prompt_premise,
            bible=self.bible,
            cast=cast_list,
            template=template,
            shot_count=8,
            seconds_per_shot=8,
            episode_number=episode_number,
            previous_screenplay=prev_sp,
            max_passes=3,
        )

        # Save screenplay JSON
        screenplay_path.write_text(screenplay.model_dump_json(indent=2), encoding="utf-8")
        print(f"  [OK] Screenplay saved: {screenplay_path.name} (Title: \"{screenplay.title}\")")

        # Save verification reports
        with open(continuity_path, "w", encoding="utf-8") as f:
            json.dump(cont_report.to_dict(), f, indent=2)
        with open(quality_path, "w", encoding="utf-8") as f:
            json.dump(qscore.model_dump(), f, indent=2)

        # 4. Stage 3: Render Storyboard Cards
        print(f"[STAGE 2/4] Rendering 9:16 Storyboard Cards (Zero-cost Preview)...")
        sb_dir = self.organizer.get_storyboard_dir(episode_number)
        self.storyboard_gen.output_dir = sb_dir
        sb_cards = self.storyboard_gen.render_full_storyboard(screenplay)
        print(f"  [OK] Generated {len(sb_cards)} storyboard cards in {sb_dir.name}/")

        # 5. Stage 4: Semantic Verification Unit Tests (Option C)
        print(f"[STAGE 3/4] Running Semantic Verification Unit Tests...")
        sem_report = SemanticVerificationRunner.run_verification(
            screenplay=screenplay,
            bible=self.bible,
            previous_screenplay=prev_sp,
            out_file=semantic_path,
        )
        print(f"  [OK] Semantic Audit Verdict: {sem_report['overall_verdict']} (Score: {sem_report['continuity_score']}/5.0)")

        # 6. Stage 5: Subtitle Generation (ASS & SRT)
        print(f"[STAGE 4/4] Generating ReelShort Styled ASS Subtitles...")
        SubtitleGenerator.generate_ass(screenplay, out_file=ass_path, safe_margin_bottom=120)
        SubtitleGenerator.generate_srt(screenplay, out_file=srt_path)
        print(f"  [OK] Styled ASS Subtitles saved: {ass_path.name}")

        # 7. Video Rendering & FFmpeg Stitching (if enabled)
        master_video_str = None
        if self.render_video:
            # Stage 7a: Generate character dialogue voices via Magic Hour
            if not self.mock_mode:
                print(f"\n[VOICE ACTING] Synthesizing character dialogue lines...")
                for shot in screenplay.shots:
                    if shot.dialogue:
                        v_target = self.organizer.get_shot_voice_path(episode_number, shot.id)
                        if not v_target.exists() or v_target.stat().st_size < 1000:
                            print(f"  [VOICE] {shot.id} - {shot.speaker}: \"{shot.dialogue}\"")
                            self.voice_manager.generate_shot_voice(
                                speaker=shot.speaker,
                                dialogue=shot.dialogue,
                                voice_hint=shot.audio or "",
                                out_file=v_target,
                            )

            print(f"\n[VIDEO RENDER] Sequentially generating 8 clips via Magic Hour...")
            clips = self.generator.generate_episode_sequentially(
                screenplay=screenplay,
                organizer=self.organizer,
                model=self.model,
                resolution=self.resolution,
                audio=True,
                use_frame_extraction=self.use_frame_extraction,
            )

            print(f"[FFMPEG STITCH] Concatenating 8 clips with mixed voice acting & burning ASS subtitles into master...")
            final_master = self.assembler.assemble(
                screenplay=screenplay,
                clip_paths=clips,
                out_master_path=master_path,
                ass_path=ass_path,
                burn_subtitles=True,
            )
            print(f"  [OK] Master Video Ready: {final_master.resolve()}")
            master_video_str = str(final_master)

        # 8. Commit Updates to Series Bible
        self.bible.record_cliffhanger(episode_number, screenplay.cliffhanger)
        if episode_number > 1:
            self.bible.resolve_cliffhanger(episode_number - 1, resolving_episode=episode_number)
        if arc_beat and arc_beat.thread_to_open:
            self.bible.add_plot_thread(arc_beat.thread_to_open, arc_beat.thread_to_open.replace("_", " ").title(), episode_number, 10)
        if arc_beat and arc_beat.thread_to_advance:
            self.bible.touch_plot_thread(arc_beat.thread_to_advance, episode_number)

        self.bible.record_episode_recap(
            episode_number,
            f"{screenplay.title}: {screenplay.hook} -> {screenplay.cliffhanger}"
        )
        self.bible.commit()

        return {
            "episode_number": episode_number,
            "title": screenplay.title,
            "screenplay_path": str(screenplay_path),
            "storyboard_count": len(sb_cards),
            "subtitles_ass": str(ass_path),
            "verification_verdict": sem_report["overall_verdict"],
            "master_video": master_video_str,
            "status": "SUCCESS",
        }

    def generate_all_episodes(
        self,
        start_ep: int = 1,
        end_ep: Optional[int] = None,
        force_regenerate: bool = False,
    ) -> List[Dict[str, Any]]:
        """Batch generate all episodes with automatic checkpointing."""
        end_ep = end_ep or self.episodes_count
        print(f"\n[LAUNCH] Starting Series Pipeline: '{self.series_name}' ({end_ep - start_ep + 1} episodes)")
        print(f"[PATH] Output Directory: {self.organizer.series_dir.resolve()}")
        print(f"[MODE] Video Rendering: {'ENABLED (Frame Extraction Opt A)' if self.render_video else 'DISABLED (Free Storyboard & Script Mode)'}\n")

        results = []
        for ep in range(start_ep, end_ep + 1):
            res = self.generate_episode(ep, force_regenerate=force_regenerate)
            results.append(res)

        print("\n=======================================================")
        print(f"[COMPLETE] SERIES GENERATION COMPLETE: {len(results)} EPISODES PROCESSED")
        print(f"=======================================================")
        return results
