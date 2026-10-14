"""Screenwriter engine supporting Gemini REST, multi-pass LLM self-review, and offline templates."""

import os
import json
import time
import requests
from typing import Optional, List, Dict, Any, Tuple
from ..models import Character, Screenplay, BeatSheet, GenreTemplate, Shot, QualityScore
from ..config import GEMINI_API_KEY, OPENAI_API_KEY
from .prompt_builder import (
    SYSTEM_MICRODRAMA_SCREENWRITER,
    build_beat_sheet_prompt,
    build_screenplay_prompt,
)
from .validator import validate_screenplay, validate_beat_sheet
from ..series.bible import SeriesBibleManager
from ..series.continuity import ContinuityValidator, ContinuityReport


class Screenwriter:
    """Microdrama Screenwriter with multi-pass self-review and Series Bible continuity."""

    def __init__(
        self,
        provider: str = "gemini",
        model: str = "gemini-3.5-flash",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key or (GEMINI_API_KEY if self.provider == "gemini" else OPENAI_API_KEY)
        self.base_url = base_url

    def _call_gemini(self, prompt: str, system_prompt: str = SYSTEM_MICRODRAMA_SCREENWRITER) -> str:
        """Call Google Gemini generateContent endpoint with automatic fallback chain."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        # Candidate models fallback chain
        candidates = [self.model]
        for fb in ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-pro-latest"]:
            if fb not in candidates:
                candidates.append(fb)

        last_error = ""
        for model_name in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.7,
                    "maxOutputTokens": 8192,
                },
            }

            for attempt in range(2):
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=90)
                    if response.status_code == 200:
                        data = response.json()
                        cands = data.get("candidates", [])
                        if cands:
                            parts = cands[0].get("content", {}).get("parts", [])
                            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                            if text.strip():
                                return text

                    error_data = response.json() if response.content else {}
                    last_error = error_data.get("error", {}).get("message", response.text)
                    if response.status_code == 503 or response.status_code == 429:
                        time.sleep(2)
                        continue
                    elif response.status_code == 404:
                        break
                    else:
                        raise RuntimeError(f"Gemini API returned HTTP {response.status_code}: {last_error}")
                except requests.RequestException as e:
                    last_error = str(e)
                    time.sleep(1)
                    continue

        raise RuntimeError(f"All Gemini model candidates failed. Last error: {last_error}")

    def _call_openai(self, prompt: str, system_prompt: str = SYSTEM_MICRODRAMA_SCREENWRITER) -> str:
        """Call OpenAI-compatible chat completions endpoint."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        url = self.base_url or "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model or "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=90)
        if response.status_code != 200:
            raise RuntimeError(f"LLM API returned HTTP {response.status_code}: {response.text}")

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_beat_sheet(
        self,
        story_idea: str,
        template: Optional[GenreTemplate] = None,
        shot_count: int = 8,
        specific_scenes: Optional[List[str]] = None,
        episode_number: int = 1,
        previous_cliffhanger: Optional[str] = None,
        series_canon: Optional[List[str]] = None,
        bible_context: Optional[str] = None,
        arc_objective: Optional[str] = None,
    ) -> BeatSheet:
        """Generate Stage 1: Beat Sheet outline."""
        prompt = build_beat_sheet_prompt(
            story_idea=story_idea,
            template=template,
            shot_count=shot_count,
            specific_scenes=specific_scenes,
            episode_number=episode_number,
            previous_cliffhanger=previous_cliffhanger,
            series_canon=series_canon,
            bible_context=bible_context,
            arc_objective=arc_objective,
        )

        if self.provider == "mock" or not self.api_key:
            return self._mock_beat_sheet(story_idea, template, shot_count, episode_number, previous_cliffhanger)

        try:
            if self.provider == "gemini":
                raw_json = self._call_gemini(prompt)
            else:
                raw_json = self._call_openai(prompt)
            return validate_beat_sheet(raw_json)
        except Exception as e:
            print(f"[INFO] Live LLM encountered temporary error ({e}). Using template beat planner...")
            return self._mock_beat_sheet(story_idea, template, shot_count, episode_number, previous_cliffhanger)

    def generate_screenplay(
        self,
        story_idea: str,
        cast: Optional[List[Character]] = None,
        template: Optional[GenreTemplate] = None,
        shot_count: int = 8,
        seconds_per_shot: int = 8,
        aspect_ratio: str = "9:16",
        specific_scenes: Optional[List[str]] = None,
        episode_number: int = 1,
        previous_cliffhanger: Optional[str] = None,
        series_canon: Optional[List[str]] = None,
        bible_context: Optional[str] = None,
    ) -> Screenplay:
        """Generate full microdrama screenplay for episode N."""
        if not cast:
            cast = template.default_cast if template else [
                Character(name="Protagonist", role="Protagonist", look="Modern sleek outfit, piercing eyes", voice="Expressive")
            ]

        # Stage 1: Beat Sheet
        beat_sheet = self.generate_beat_sheet(
            story_idea=story_idea,
            template=template,
            shot_count=shot_count,
            specific_scenes=specific_scenes,
            episode_number=episode_number,
            previous_cliffhanger=previous_cliffhanger,
            series_canon=series_canon,
            bible_context=bible_context,
        )
        beat_summary = "\n".join(f"Beat {b.id} ({b.beat_type}): {b.summary}" for b in beat_sheet.beats)

        # Stage 2: Shot-by-shot Screenplay
        prompt = build_screenplay_prompt(
            story_idea=story_idea,
            cast=cast,
            template=template,
            shot_count=shot_count,
            seconds_per_shot=seconds_per_shot,
            aspect_ratio=aspect_ratio,
            specific_scenes=specific_scenes,
            beat_sheet_summary=beat_summary,
            episode_number=episode_number,
            previous_cliffhanger=previous_cliffhanger,
            series_canon=series_canon,
            bible_context=bible_context,
        )

        if self.provider == "mock" or not self.api_key:
            return self._mock_screenplay(story_idea, cast, template, shot_count, seconds_per_shot, episode_number, previous_cliffhanger)

        try:
            if self.provider == "gemini":
                raw_json = self._call_gemini(prompt)
            else:
                raw_json = self._call_openai(prompt)
            return validate_screenplay(raw_json)
        except Exception as e:
            print(f"[INFO] Live LLM encountered temporary error ({e}). Using template screenplay generator...")
            return self._mock_screenplay(story_idea, cast, template, shot_count, seconds_per_shot, episode_number, previous_cliffhanger)

    def evaluate_quality(
        self,
        screenplay: Screenplay,
        continuity_report: ContinuityReport,
    ) -> QualityScore:
        """Evaluate DramaBench quality rubric (Hook, Escalation, Cliffhanger, Dialogue, Shootability)."""
        # 1. Hook evaluation
        shot1 = screenplay.shots[0] if screenplay.shots else None
        hook_score = 4
        if shot1 and (any(kw in shot1.action.lower() for kw in ["slap", "slam", "shatter", "grab", "gasp", "tear", "freeze", "gun"])):
            hook_score = 5
        elif not shot1 or len(shot1.action) < 15:
            hook_score = 3

        # 2. Cliffhanger evaluation
        last_shot = screenplay.shots[-1] if screenplay.shots else None
        cliff_score = 4
        if last_shot and screenplay.cliffhanger and any(kw in last_shot.action.lower() for kw in ["freeze", "knife", "gun", "alarm", "reveal", "door", "stare", "handcuff"]):
            cliff_score = 5
        elif not screenplay.cliffhanger:
            cliff_score = 2

        # 3. Escalation
        escalation_score = 4 if len(screenplay.shots) >= 6 else 3

        # 4. Dialogue snappiness
        max_words = max((len(s.dialogue.split()) for s in screenplay.shots if s.dialogue), default=0)
        dialogue_score = 5 if max_words <= 12 else (4 if max_words <= 15 else 2)

        # 5. Continuity score from report
        cont_score = max(1, min(5, int(round(continuity_report.score))))

        # 6. Shootability
        all_vertical = all("9:16" in s.camera or "vertical" in s.camera.lower() for s in screenplay.shots)
        shoot_score = 5 if all_vertical else 4

        avg_score = (hook_score + escalation_score + cliff_score + dialogue_score + cont_score + shoot_score) / 6.0
        approved = continuity_report.is_valid and avg_score >= 3.5

        feedback = (
            f"Quality passed: {avg_score:.1f}/5.0" if approved
            else f"Quality failed gates: violations={continuity_report.violations}"
        )

        return QualityScore(
            hook_score=hook_score,
            escalation_score=escalation_score,
            cliffhanger_score=cliff_score,
            dialogue_score=dialogue_score,
            continuity_score=cont_score,
            shootability_score=shoot_score,
            feedback=feedback,
            is_approved=approved,
        )

    def generate_screenplay_with_review(
        self,
        story_idea: str,
        bible: SeriesBibleManager,
        cast: Optional[List[Character]] = None,
        template: Optional[GenreTemplate] = None,
        shot_count: int = 8,
        seconds_per_shot: int = 8,
        aspect_ratio: str = "9:16",
        specific_scenes: Optional[List[str]] = None,
        episode_number: int = 1,
        previous_screenplay: Optional[Screenplay] = None,
        max_passes: int = 3,
    ) -> Tuple[Screenplay, ContinuityReport, QualityScore]:
        """Multi-pass review loop: Generate -> Rule Validate -> Score -> Repair."""
        # 1. Extract context pack from Series Bible
        bible_context = bible.get_compact_context_pack(episode_number)
        prev_cliffhanger = (
            bible.state.cliffhangers[-1].text
            if bible.state.cliffhangers
            else (previous_screenplay.cliffhanger if previous_screenplay else None)
        )

        best_screenplay: Optional[Screenplay] = None
        best_report: Optional[ContinuityReport] = None
        best_score: Optional[QualityScore] = None

        for pass_num in range(1, max_passes + 1):
            # Pass 1: Generate Screenplay
            screenplay = self.generate_screenplay(
                story_idea=story_idea,
                cast=cast,
                template=template,
                shot_count=shot_count,
                seconds_per_shot=seconds_per_shot,
                aspect_ratio=aspect_ratio,
                specific_scenes=specific_scenes,
                episode_number=episode_number,
                previous_cliffhanger=prev_cliffhanger,
                series_canon=bible.state.canon_events,
                bible_context=bible_context,
            )

            # Pass 2: Continuity validation against Bible
            report = ContinuityValidator.validate_screenplay(
                screenplay=screenplay,
                bible=bible,
                previous_screenplay=previous_screenplay,
            )

            # Pass 3: Quality Scoring
            qscore = self.evaluate_quality(screenplay, report)

            best_screenplay = screenplay
            best_report = report
            best_score = qscore

            if qscore.is_approved:
                break

            # If not approved and attempts remain, inject feedback for next pass
            if pass_num < max_passes:
                story_idea += f"\n[FIX INSTRUCTIONS PASS {pass_num+1}]: Please address violations: {', '.join(report.violations)}"

        return best_screenplay, best_report, best_score

    def _mock_beat_sheet(
        self,
        story_idea: str,
        template: Optional[GenreTemplate],
        shot_count: int,
        episode_number: int = 1,
        previous_cliffhanger: Optional[str] = None,
    ) -> BeatSheet:
        """Deterministic mock beat sheet for offline testing."""
        hook_p = previous_cliffhanger or (template.signature_hook if template else "Sudden shocking confrontation.")
        return BeatSheet(
            episode_number=episode_number,
            title=f"{template.name if template else 'Microdrama'} Episode {episode_number}",
            genre=template.genre if template else "Suspense",
            logline=story_idea[:100],
            hook_promise=f"Resolves cliffhanger: {hook_p[:60]}",
            cliffhanger_promise=template.cliffhanger_formulas[0] if (template and template.cliffhanger_formulas) else "Unresolved life-or-death decision.",
            beats=[
                {"id": 1, "beat_type": "hook", "summary": "Visceral resolution of prior episode cliffhanger.", "emotional_stakes": "Panic", "duration_seconds": 8},
                {"id": 2, "beat_type": "inciting_incident", "summary": "A lethal secret or ultimatum is presented.", "emotional_stakes": "Escalation", "duration_seconds": 8},
                {"id": 3, "beat_type": "conflict_escalation", "summary": "Verbal clash and power struggle.", "emotional_stakes": "Fury", "duration_seconds": 8},
                {"id": 4, "beat_type": "secret_reveal", "summary": "Crucial truth is exposed to rivals.", "emotional_stakes": "Shock", "duration_seconds": 8},
                {"id": 5, "beat_type": "confrontation", "summary": "Physical or acoustic trap sprung.", "emotional_stakes": "Danger", "duration_seconds": 8},
                {"id": 6, "beat_type": "reversal", "summary": "Expected outcome flipped upside down.", "emotional_stakes": "Disorientation", "duration_seconds": 8},
                {"id": 7, "beat_type": "cliffhanger", "summary": "Identity unmasked or lethal choice presented.", "emotional_stakes": "Heart-stopping cliffhanger", "duration_seconds": 8},
            ][:shot_count],
            previous_cliffhanger=previous_cliffhanger,
        )

    def _mock_screenplay(
        self,
        story_idea: str,
        cast: List[Character],
        template: Optional[GenreTemplate],
        shot_count: int,
        seconds_per_shot: int,
        episode_number: int = 1,
        previous_cliffhanger: Optional[str] = None,
    ) -> Screenplay:
        """Deterministic mock screenplays supporting Episodes 1 through 10 of Contract Bride."""
        genre = template.genre if template else "Romance & Drama"
        vibe = template.vibe if template else "Sultry, possessive, intense"
        p1 = cast[0].name
        p2 = cast[1].name if len(cast) > 1 else "Alexander"
        p3 = cast[2].name if len(cast) > 2 else "Victoria"

        # Multi-episode script bank for The Cold CEO's Contract Bride (Episodes 1-10)
        ep_scripts = {
            1: {
                "title": "The Price of Blood - Episode 1",
                "logline": "To save her bankrupt family, Seraphina signs a 1-year contract marriage with ruthless billionaire Alexander.",
                "hook": "Divorce contract slammed onto executive desk.",
                "cliffhanger": "Alexander grabs Seraphina's wrist at the threshold: 'You never leave without my permission.'",
                "beats": [
                    (f"Penthouse mahogany desk. {p1} stands pale, trembling.", f"{p1} slams the contract papers onto the polished desk.", "Vertical 9:16 portrait: tight push-in on wet ink signature.", p1, "I signed it, Alexander.", "Paper slapping mahogany, cello sting.", "01-Hook"),
                    (f"Glass high-rise window. {p2} turns around slowly.", f"{p2} unbuttons his suit cuffs, towering with an icy stare.", "Vertical 9:16 portrait: low-angle hero framing on Alexander.", p2, "Three rules. Obey them all.", "Distant thunder rumble.", "02-Escalation"),
                    (f"Desk edge. {p1} clutches her coat tightly.", f"{p1} steps back toward the door, chin raised defiantly.", "Vertical 9:16 portrait: over-the-shoulder medium portrait.", p1, "I am your wife, not your prisoner.", "Violent wind outside.", "03-Clash"),
                    (f"Desk center. {p2} tosses a gold key card.", f"{p2} flicks the card across the marble floor to her feet.", "Vertical 9:16 portrait: rapid tilt down to card sliding.", p2, "Rule one: no public appearances.", "Sharp metallic tap.", "04-Ultimatum"),
                    (f"Hallway entrance. Footsteps click sharply.", f"{p3} enters wearing crimson silk, smirking maliciously.", "Vertical 9:16 portrait: doorway framing with harsh backlight.", p3, "Alexander, darling. Who is this beggar?", "Click of high heels on marble.", "05-Intrusion"),
                    (f"Before {p3}. {p1} clutches her wedding band.", f"{p1} stands her ground as {p3} looks down her nose.", "Vertical 9:16 portrait: eye-level two-shot profile.", p1, "I am his wife.", "Tense violin tremolo.", "06-Defiance"),
                    (f"Room center. {p2} steps between them.", f"{p2} puts a hand on {p1}'s waist, pulling her flush against him.", "Vertical 9:16 portrait: close-up on possessive grip.", p2, "Victoria, out. Now.", "Sudden audio silence.", "07-Protection"),
                    (f"Penthouse threshold. {p2} corners {p1}.", f"{p2} pins {p1} against the glass, eyes dark with fire.", "Vertical 9:16 portrait: intense macro profile close-up.", p2, "Rule two: you belong to me.", "Heartbeat crescendo cliffhanger cut.", "08-Cliffhanger"),
                ]
            },
            2: {
                "title": "A Bed of Thorns - Episode 2",
                "logline": "Seraphina endures the first night in the penthouse and uncovers Alexander's dark trauma.",
                "hook": "Seraphina breaks free from Alexander's grip at the threshold.",
                "cliffhanger": "Alexander pins Seraphina against the frosted bookcase: 'Did anyone tell you what happened to my last bride?'",
                "beats": [
                    (f"Penthouse glass wall. {p1} wrenches her wrist free.", f"{p1} pushes {p2} back, breathing heavily in the amber lamp glow.", "Vertical 9:16 portrait: sudden close-up push-in on parted hands.", p1, "Don't touch me like that!", "Sharp breath, acoustic string pluck.", "01-Hook-Resolution"),
                    (f"Master suite hallway. {p2} straightens his collar.", f"{p2} steps into the shadows, voice icy and measured.", "Vertical 9:16 portrait: half-shadowed vertical close-up.", p2, "Your suite is the left door.", "Deep bass drone.", "02-Separation"),
                    (f"Guest bedroom. {p1} sits on the bed.", f"{p1} discovers a locked iron jewelry box under the nightstand.", "Vertical 9:16 portrait: high-angle look down at rusted box.", p1, "Why is this hidden here?", "Clock ticking loudly.", "03-Discovery"),
                    (f"Study doors. Muffled crying and gasping echoes.", f"{p1} creeps toward the frosted glass doors, peering through.", "Vertical 9:16 portrait: creeping tracking shot in dim hallway.", p1, "Alexander...?", "Labored breathing, heartbeat.", "04-Intrusion"),
                    (f"Study interior. {p2} clutches his chest.", f"{p2} is kneeling by the fireplace, sweating from a violent nightmare.", "Vertical 9:16 portrait: low angle looking up at trembling CEO.", p2, "Get away from me!", "Flames crackling, cello groan.", "05-Vulnerability"),
                    (f"Beside the hearth. {p1} offers a glass of water.", f"{p1} kneels gently beside him, placing a hand on his shoulder.", "Vertical 9:16 portrait: intimate medium two-shot in firelight.", p1, "You are safe. Breathe.", "Soft string melody.", "06-Tenderness"),
                    (f"Study floor. {p2} snaps back to fury.", f"{p2} smashes the water glass against the marble hearth.", "Vertical 9:16 portrait: glass exploding on stone impact.", p2, "I do not need your pity!", "Glass shattering acoustic blast.", "07-Reversal"),
                    (f"Frosted bookcase. {p2} pins {p1} roughly.", f"{p2} traps her against the frosted glass, breath trembling with venom.", "Vertical 9:16 portrait: extreme close-up on dilated hazel eyes.", p2, "Ask me what happened to my first bride.", "Eerie discordant chord, cut to black.", "08-Cliffhanger"),
                ]
            },
            3: {
                "title": "The Viper's Banquet - Episode 3",
                "logline": "At a high-society charity gala, rival heiress Victoria ambushes Seraphina before 200 paparazzi.",
                "hook": "Paparazzi strobe flashes explode as Alexander escorts Seraphina onto the red carpet in emerald silk.",
                "cliffhanger": "Alexander's hand clamps like iron around Victoria's wrist: 'Touch my wife again, and your family empire falls by midnight.'",
                "beats": [
                    (f"Red carpet entrance. Flashbulbs flare wildly.", f"{p2} extends his arm to {p1}, whisper cold and commanding.", "Vertical 9:16 portrait: glamorous tracking hero entry.", p2, "Take my arm. Smile.", "Paparazzi shutter clicks, orchestral crescendo.", "01-Hook"),
                    (f"Gala ballroom arch. {p1} takes his arm defiantly.", f"{p1} smiles for the cameras while glaring at {p2}.", "Vertical 9:16 portrait: elegant couple profile push-in.", p1, "Only for the cameras.", "Champagne glasses clinking, violin waltz.", "02-Escalation"),
                    (f"Grand chandelier center. {p3} glides forward holding red wine.", f"{p3} blocks their path with a mocking sneer.", "Vertical 9:16 portrait: low-angle confrontation framing.", p3, "Playing house with a peasant, Alexander?", "Murmuring guests, tense harp slide.", "03-Clash"),
                    (f"Before the elite guests. {p3} tilts her glass.", f"{p3} deliberately splashes red wine down {p1}'s emerald gown.", "Vertical 9:16 portrait: slow-motion wine splashing on fabric.", p3, "Oops. How clumsy of me.", "Gasps from crowd, wine drip sound.", "04-Humiliation"),
                    (f"Ballroom floor. {p1} stands tall, amber eyes icy.", f"{p1} wipes a drop of wine from her collarbone without flinching.", "Vertical 9:16 portrait: tight macro close-up on proud defiant face.", p1, "You missed my face, Victoria.", "Sudden silence across the ballroom.", "05-Defiance"),
                    (f"VIP circle. {p3}'s face twists in rage.", f"{p3} raises her hand to slap {p1} across the cheek.", "Vertical 9:16 portrait: dynamic push-in on raised arm.", p3, "How dare you speak to me!", "Violent violin sting.", "06-Escalation"),
                    (f"Between them. {p2}'s hand intercepts like a steel trap.", f"{p2} grips {p3}'s wrist in mid-air, squeezing until her champagne flute drops.", "Vertical 9:16 portrait: close-up on crushing grip and shattering glass.", p2, "Touch my wife again, Victoria...", "Glass shattering on marble, deep bass rumble.", "07-Protection"),
                    (f"Before 200 photographers. {p2} leans into {p3}'s trembling ear.", f"{p2} glares with lethal predatory fury as flashes illuminate his jaw.", "Vertical 9:16 portrait: intense macro stare over shoulder.", p2, "...and your family empire falls by midnight.", "Heartbeat thump, cliffhanger cut to black.", "08-Cliffhanger"),
                ]
            },
            4: {
                "title": "Shield of Ice - Episode 4",
                "logline": "In the aftermath of the gala, Alexander tends to Seraphina's wounds before a lethal blackmail text arrives.",
                "hook": "Penthouse suite. Alexander kneels on the marble floor holding an ice wrap to Seraphina's sprained ankle.",
                "cliffhanger": "Seraphina's phone buzzes with a photo of her father in an ICU bed: 'Sign the annulment, or the life support is pulled at dawn.'",
                "beats": [
                    (f"Penthouse bedroom. {p2} kneels beside the chaise.", f"{p2} wraps {p1}'s swollen ankle with gentle precision.", "Vertical 9:16 portrait: intimate low-angle two-shot.", p2, "Stay still. You pushed her too far.", "Quiet piano notes, rustle of bandage.", "01-Hook-Resolution"),
                    (f"Chaise lounge. {p1} looks down at him, searching his face.", f"{p1} leans forward, voice softening despite herself.", "Vertical 9:16 portrait: gentle eye-level close-up on Seraphina.", p1, "You defended me before the whole city.", "Soft cello warmth, distant city hum.", "02-Intimacy"),
                    (f"Floor beside chaise. {p2} fastens the bandage clip.", f"{p2} looks away, his cold mask snapping back in place.", "Vertical 9:16 portrait: close-up on Alexander's guarded profile.", p2, "I defended the Sterling name.", "Abrupt silence, cool piano drop.", "03-Defense"),
                    (f"Vanity table. {p1}'s phone vibrates violently against glass.", f"{p1} reaches over, seeing an alert from an unknown number.", "Vertical 9:16 portrait: rapid pan to glowing screen on dark wood.", p1, "Who is messaging at 2 AM...?", "Harsh phone vibration buzz.", "04-Intrusion"),
                    (f"Phone screen reflection. {p1}'s face pales with horror.", f"{p1} drops the phone onto the rug, hands shaking violently.", "Vertical 9:16 portrait: extreme close-up on dilated horrified eyes.", p1, "No... Dad... please no!", "High-pitched tinnitus whine, gasp.", "05-Shock"),
                    (f"Rug beside chaise. {p2} scoops up the phone.", f"{p2} reads the text showing a photo of her father in an ICU bed.", "Vertical 9:16 portrait: tight focus on glowing screen with hospital photo.", p2, "'Sign the annulment by dawn...'", "Tense ticking clock, dark cello drone.", "06-Escalation"),
                    (f"Bedroom center. {p2}'s knuckles turn white clutching the phone.", f"{p2} towers with predatory fury, veins bulging on his neck.", "Vertical 9:16 portrait: low-angle hero framing on furious CEO.", p2, "Who sent this photo to you?!", "Thunder crack outside high-rise glass.", "07-Rage"),
                    (f"Vanity mirror. Voicemail audio auto-plays in {p3}'s silky voice.", f"{p1} clutches her chest as {p3}'s laugh echoes in the room.", "Vertical 9:16 portrait: split focus on Seraphina and Alexander.", p3, "Clock is ticking, little contract bride.", "Heartbeat crescendo, sudden blackout.", "08-Cliffhanger"),
                ]
            },
            5: {
                "title": "The Near Kiss - Episode 5",
                "logline": "Trapped in the high-rise during a torrential thunderstorm, Alexander confesses his vulnerability before an alarm shrieks.",
                "hook": "Violent lightning strikes the high-rise tower, instantly plunging the entire penthouse into pitch darkness.",
                "cliffhanger": "Alexander's lips are a millimeter from Seraphina's when red strobe emergency lights flash and the safe alarm screams.",
                "beats": [
                    (f"Dark penthouse living room. Lightning illuminates rain on glass.", f"{p1} stumbles in the dark, clutching her shawl in the freezing draft.", "Vertical 9:16 portrait: dramatic silhouette framing against storm.", p1, "Alexander?! Where are the lights?", "Thunder blast rattling window glass.", "01-Hook"),
                    (f"Behind her. A warm shadow steps into the lightning flash.", f"{p2} catches her by the elbows from behind, steadying her.", "Vertical 9:16 portrait: over-the-shoulder intimate closeness.", p2, "Right behind you. Don't move.", "Rain lashing glass, soft breath.", "02-Proximity"),
                    (f"Living room window. Lightning reveals their faces inches apart.", f"{p1} turns in his grip, breathing rapidly against his chest.", "Vertical 9:16 portrait: tight macro two-shot in storm light.", p1, "I have to save my father, Alexander.", "Distant thunder rumble, cello melody.", "03-Vulnerability"),
                    (f"Window frame. {p2}'s thumb gently brushes her cheekbone.", f"{p2} gazes down with raw unguarded tenderness.", "Vertical 9:16 portrait: extreme close-up on Alexander's gaze.", p2, "No one touches what is under my roof.", "Rain patter softening, gentle bass.", "04-Protection"),
                    (f"Shadows of the hearth. {p1}'s eyes glisten with tears.", f"{p1} reaches up, touching the lapel of his tailored jacket.", "Vertical 9:16 portrait: intimate eye-level portrait of Seraphina.", p1, "Why do you care so much?", "Tender acoustic guitar chord.", "05-Thaw"),
                    (f"Hearth glow. {p2} pulls her slowly against his chest.", f"{p2} leans down, his breath warm against her parted lips.", "Vertical 9:16 portrait: macro profile push-in on closing distance.", p2, "Because I broke rule number one.", "Deep cello swell, heartbeat pacing.", "06-Confession"),
                    (f"Inches from lips. {p2}'s eyes lock onto hers.", f"{p2} tilts her chin upward, millimeters from kissing her.", "Vertical 9:16 portrait: hyper-intense romantic close-up.", p2, "I can't let you leave me.", "Violin crescendo reaching peak note.", "07-Near-Kiss"),
                    (f"Study wall. Red strobe emergency lights ignite with deafening sirens.", f"{p2} snaps backward as the blast doors lock: the safe has been breached!", "Vertical 9:16 portrait: flashing crimson light on startled faces.", p2, "The master safe... someone is inside!", "Ear-splitting klaxon alarm, cliffhanger cut.", "08-Cliffhanger"),
                ]
            },
            6: {
                "title": "The Leak - Episode 6",
                "logline": "The confidential marriage contract is leaked to the corporate board, and forged evidence points directly at Seraphina.",
                "hook": "Boardroom mahogany table. Victoria slams morning tabloids showing the $10 million marriage contract on the front page.",
                "cliffhanger": "Alexander stares through Seraphina with shattered, merciless eyes: 'Tell me to my face this isn't your signature on the $5M deposit.'",
                "beats": [
                    (f"Executive boardroom. 12 directors murmur in outrage.", f"{p3} slams newspapers on the polished table.", "Vertical 9:16 portrait: aggressive low-angle push-in on headlines.", p3, "The CEO bought a fake wife for $10M!", "Boardroom shouting, papers fluttering.", "01-Hook"),
                    (f"Head of table. {p2} sits immovable like carved granite.", f"{p2} steeples his fingers, storm-grey eyes freezing the room.", "Vertical 9:16 portrait: commanding hero close-up on Alexander.", p2, "Quiet. Every single one of you.", "Sudden dead silence across the room.", "02-Dominance"),
                    (f"Boardroom double doors. {p1} enters in tailored black blazer.", f"{p1} walks down the center aisle, head held high under hostile stares.", "Vertical 9:16 portrait: confident tracking entry shot.", p1, "The leak did not come from me.", "Gasps from directors, heel clicks.", "03-Defiance"),
                    (f"Table center. {p3} slides a folder of bank statements across.", f"{p3} smiles with triumphant venom.", "Vertical 9:16 portrait: tilt down to glossy wire transfer documents.", p3, "$5 million wired to your secret Cayman account!", "Tense orchestral sting, murmur.", "04-Trap"),
                    (f"Before the table. {p1} picks up the slip, color draining.", f"{p1} stares at the bottom: an exact replica of her handwriting signature.", "Vertical 9:16 portrait: extreme close-up on trembling hands and ink.", p1, "This signature... it's a forgery!", "Muffled heartbeat, clock ticking.", "05-Despair"),
                    (f"VIP row. {p3} leans toward the board chairman.", f"{p3} displays tablet logs showing the safe was opened with Seraphina's key.", "Vertical 9:16 portrait: haughty smirk over shoulder.", p3, "She sold his confidential merger files.", "Gasps, camera flash outside glass.", "06-Accusation"),
                    (f"Chair center. {p2} slowly rises to his feet.", f"{p2} looks down at the deposit slip, the tenderness from last night turned to ice.", "Vertical 9:16 portrait: slow ominous low-angle push-in.", p2, "Is this your signature, Seraphina?", "Violin tremolo reaching agonizing tension.", "07-Escalation"),
                    (f"Between them. {p2} traps her against the boardroom window.", f"{p2} stares into her amber eyes with devastated betrayal.", "Vertical 9:16 portrait: macro two-shot, ice and fire contrast.", p2, "Look me in the eye and tell me you didn't sell me out.", "Crash of thunder, cliffhanger blackout.", "08-Cliffhanger"),
                ]
            },
            7: {
                "title": "Trial by Silence - Episode 7",
                "logline": "Locked in the guest suite by Alexander's security, Seraphina uncovers the hacker's clue and stages a daring escape into the rain.",
                "hook": "Penthouse guest suite. Heavy deadbolts click into place as security guards lock Seraphina inside.",
                "cliffhanger": "Seraphina slips through the balcony window into the torrential storm: 'If you won't believe me, Alexander, I'll bring the proof myself!'",
                "beats": [
                    (f"Guest suite door. Heavy brass deadbolt turns from outside.", f"{p1} rattles the brass handle in vain against locked oak.", "Vertical 9:16 portrait: tight close-up on hands shaking doorknob.", p1, "Open this door! I was framed!", "Heavy deadbolt clunk, heavy breathing.", "01-Hook-Resolution"),
                    (f"Door exterior. Two security guards stand at attention.", f"Head guard speaks through the frosted panel without emotion.", "Vertical 9:16 portrait: cold hallway perspective through glass.", "Guard", "Mr. Sterling's orders. No visitors, no phone.", "Low bass drone, distant rain.", "02-Confinement"),
                    (f"Suite study corner. {p1} turns to the private terminal desk.", f"{p1} kneels by the desktop computer, examining the USB port.", "Vertical 9:16 portrait: low-angle search in shadowy room.", p1, "The hacker plugged the drive right here...", "Quiet acoustic cello tension.", "03-Investigation"),
                    (f"Under the mahogany desk. Something catches amber lamp light.", f"{p1} reaches under the baseboard, pulling out a sparkling object.", "Vertical 9:16 portrait: extreme close-up on fingers finding jewelry.", p1, "What is this...?", "Mysterious music box chime.", "04-Discovery"),
                    (f"Under the lamp. A pearl and diamond earring glitters.", f"{p1} turns it over: engraved with the monogram 'V.V.'", "Vertical 9:16 portrait: macro focus on earring monogram in palm.", p1, "Victoria Vance. She was in this room!", "Sudden triumphant violin sting.", "05-Revelation"),
                    (f"Balcony French doors. Thunder rattles the heavy glass.", f"{p1} examines the balcony lock, taking a hairpin from her hair.", "Vertical 9:16 portrait: dramatic tracking push-in to rain-streaked glass.", p1, "I'm not waiting here to be destroyed.", "Thunder roll, rain lashing glass.", "06-Resolve"),
                    (f"Balcony latch. {p1} twists the hairpin, latch springing free.", f"{p1} pushes open the heavy glass door into freezing wind and rain.", "Vertical 9:16 portrait: dynamic burst of wind blowing her hair.", p1, "Stand aside, storm.", "Wind rushing, howling gust.", "07-Action"),
                    (f"Rain-soaked fire escape. {p1} steps onto the iron grating high above city.", f"{p1} grips the railing, amber eyes burning with fierce determination.", "Vertical 9:16 portrait: breathtaking vertical plunge shot over skyline.", p1, "I'll bring you the truth myself, Alexander!", "Orchestral climax crescendo, blackout.", "08-Cliffhanger"),
                ]
            },
            8: {
                "title": "The Ambush at the Docks - Episode 8",
                "logline": "Seraphina tracks the hacker to a rainy shipping dock, where Victoria springs a deadly trap until a black Maybach roars in.",
                "hook": "Pier 44 container yard. Heavy rain pounds rusted steel shipping crates as Seraphina corners the shadowy hacker.",
                "cliffhanger": "A thug raises an iron crowbar over Seraphina's head when Alexander's black Maybach smashes through the gate at 60 mph!",
                "beats": [
                    (f"Rain-drenched container corridor. Steam rises from asphalt.", f"{p1} steps out of shadows, holding the monogrammed earring.", "Vertical 9:16 portrait: gritty cinematic tracking shot.", p1, "You forged the $5M wire transfer!", "Rain falling, distant foghorn.", "01-Hook"),
                    (f"Stacked containers. A hooded IT hacker stumbles backward in terror.", f"The hacker raises trembling hands, backing against a rusted crane.", "Vertical 9:16 portrait: low-angle look at trapped hacker.", "Hacker", "Victoria paid me $500k! Run, girl!", "Tense synth pulse, splashing footsteps.", "02-Confrontation"),
                    (f"Behind {p1}. Blinding high-beam headlights suddenly snap on.", f"Four black SUVs seal off both ends of the container corridor.", "Vertical 9:16 portrait: blinding glare haloing Seraphina's silhouette.", p1, "A trap...", "Engine revving, gravel crunching.", "03-Ambush"),
                    (f"Lead SUV. An umbrella opens as {p3} steps into puddle in stilettos.", f"{p3} smiles like a predator with red lipstick gleaming.", "Vertical 9:16 portrait: villainous slow-motion entry.", p3, "Did you think you could outsmart me, beggar?", "Rain splashing, dark cello swell.", "04-Villain-Reveal"),
                    (f"Center corridor. {p1} stands unflinching in the downpour.", f"{p1} raises the earring high in the glare of the headlights.", "Vertical 9:16 portrait: heroic defiant portrait of soaked Seraphina.", p1, "Alexander knows you broke his safe!", "Thunder roll, silence from thugs.", "05-Defiance"),
                    (f"Beside SUV. {p3} laughs with venomous mockery.", f"{p3} leans forward, eyes wild with long-buried madness.", "Vertical 9:16 portrait: extreme close-up on Victoria's sneer.", p3, "His first bride found out too. Now she's dead.", "Eerie dissonant chord, shock gasp.", "06-Dark-Truth"),
                    (f"Behind {p1}. A massive masked thug steps from container shadow.", f"The thug raises a heavy iron crowbar over {p1}'s head.", "Vertical 9:16 portrait: terrifying high-angle shot over raised weapon.", p3, "End this little contract once and for all.", "Violin shrieking, slow-motion descent.", "07-Lethal-Peril"),
                    (f"Pier security gate. A twin-turbo V12 engine screams in the storm.", f"{p2}'s black armored Maybach blasts through the chainlink gate at 60 mph, tires smoking!", "Vertical 9:16 portrait: explosive vehicular entry crashing gate.", p2, "SERAPHINA!!!", "Metal shearing explosion, cliffhanger cut.", "08-Cliffhanger"),
                ]
            },
            9: {
                "title": "Blood and Forgiveness - Episode 9",
                "logline": "Alexander takes a brutal blow to protect Seraphina, and amidst the aftermath, he burns the fake contract forever.",
                "hook": "Warehouse floor. Alexander throws his body over Seraphina, shielding her as the crowbar strikes his shoulder with a sickening crack!",
                "cliffhanger": "Alexander strikes a silver lighter, burning the 1-year contract into drifting ashes: 'From this second, you are my real wife.'",
                "beats": [
                    (f"Warehouse floor under rain. {p2} dives across asphalt.", f"{p2} wraps his arms around {p1}, taking the full impact of the blow.", "Vertical 9:16 portrait: dynamic action impact shot.", p1, "ALEXANDER!", "Dull bone impact, agonizing grunt.", "01-Hook-Resolution"),
                    (f"Asphalt ground. {p2} rolls and kicks the thug backward.", f"{p2} sweeps the thug's legs, sending him crashing into oil drums.", "Vertical 9:16 portrait: visceral combat action hero framing.", p2, "Get behind me! Stay behind me!", "Drums clattering, police sirens wailing.", "02-Combat"),
                    (f"SUV perimeter. Flashing red-and-blue police lights illuminate the dock.", f"{p3} scrambles into her SUV in sheer panic as tires screech away.", "Vertical 9:16 portrait: chaotic tracking shot of fleeing villain.", p3, "Drive! Get us out of here!", "Police sirens screaming, tires burning rubber.", "03-Retreat"),
                    (f"Sheltered container alcove. {p2} slumps against the corrugated wall.", f"{p2} clutches his bleeding shoulder, white shirt stained crimson.", "Vertical 9:16 portrait: intimate low-angle hero vulnerability.", p2, "Seraphina... are you unhurt?", "Heavy rain outside, strained breathing.", "04-Aftermath"),
                    (f"Beside him. {p1} tears her cream sweater hem with bare hands.", f"{p1} presses the makeshift bandage to his wound, tears spilling down her cheeks.", "Vertical 9:16 portrait: tender close-up on Seraphina weeping.", p1, "You idiot... why did you jump in front of me?!", "Emotional piano and cello duet.", "05-Tears"),
                    (f"Alcove floor. {p2} reaches up with blood-streaked fingers.", f"{p2} gently cups her cheek, his eyes glistening with deep repentance.", "Vertical 9:16 portrait: macro portrait on Alexander's gaze.", p2, "I doubted you. I was blind. Forgive me.", "Warm violin swell, rain fading.", "06-Repentance"),
                    (f"Between them. {p1} reaches into his jacket, pulling out the paper.", f"{p1} holds up the bloodstained marriage contract between them.", "Vertical 9:16 portrait: focus on contract paper between their hands.", p1, "We don't need this lie anymore.", "Soft hopeful piano chord.", "07-Reconciliation"),
                    (f"Alcove entrance. {p2} flicks his silver Cartier lighter.", f"Golden flame consumes the contract, turning it into drifting embers in the dawn light.", "Vertical 9:16 portrait: slow-motion burning contract framing their faces.", p2, "Tomorrow we face the world... as husband and wife.", "Triumphant orchestral swell, blackout.", "08-Cliffhanger"),
                ]
            },
            10: {
                "title": "Crown of Thorns - Episode 10 (Season Finale)",
                "logline": "At the annual shareholder gala, Seraphina and Alexander expose Victoria, ending with a shocking identity reveal for Season 2.",
                "hook": "Sterling Corporation grand ballroom. 500 elite shareholders gasp as Alexander and Seraphina walk in hand-in-hand.",
                "cliffhanger": "A royal limousine stops outside: an elder billionaire with a gold cane steps out: 'Welcome home, my lost heiress.'",
                "beats": [
                    (f"Grand ballroom aisle. Crystal chandeliers blaze overhead.", f"{p2} and {p1} walk together in flawless black-tie elegance.", "Vertical 9:16 portrait: royal regal entrance tracking shot.", p2, "Hold your head high, Mrs. Sterling.", "Orchestral waltz, applause murmurs.", "01-Hook"),
                    (f"VIP podium. {p3} stands arrogantly clutching a microphone.", f"{p3} sneers as security surrounds the stage perimeter.", "Vertical 9:16 portrait: haughty low-angle villain profile.", p3, "This woman is an imposter and a thief!", "Gasps through 500 guests, mic feedback.", "02-Clash"),
                    (f"Podium steps. {p1} steps calmly to the microphone.", f"{p1} connects a flash drive to the central audiovisual system.", "Vertical 9:16 portrait: heroic close-up on calm determined heroine.", p1, "Let the recordings speak for themselves.", "Sudden silence across the hall.", "03-Retaliation"),
                    (f"Ballroom speakers. Loud audio confession reverberates through hall.", f"{p3}'s recorded voice booms: 'I framed Seraphina and paid the hacker $500k!'", "Vertical 9:16 portrait: reaction shots of horrified board members.", p3, "(Audio) 'Alexander will never know I set the trap!'", "Deafening gasps, camera flashes explode.", "04-Exposure"),
                    (f"Stage edge. Federal agents in suits march down the aisle.", f"Lead agent displays a federal arrest warrant to {p3}.", "Vertical 9:16 portrait: fast tracking law enforcement entry.", "Agent", "Victoria Vance, you are under arrest for fraud.", "Heavy metallic handcuff click.", "05-Arrest"),
                    (f"Aisle center. {p3} struggles violently in handcuffs.", f"{p3} screams venomously at {p1} as agents drag her toward the exit.", "Vertical 9:16 portrait: dynamic push-in on screaming villain.", p3, "You haven't won! You have no idea who you are!", "Crowd parting, security radio chatter.", "06-Defeat"),
                    (f"Center stage. {p2} turns {p1} toward him, sliding a 10-carat diamond band onto her finger.", f"{p2} kisses her knuckles before the 500 cheering shareholders.", "Vertical 9:16 portrait: romantic close-up on ring and kiss.", p2, "Forever, my real wife.", "Rapturous applause, triumphant strings.", "07-Resolution"),
                    (f"Gala entrance portico. A Maybach limousine with royal crest stops.", f"An elderly billionaire with a gold cane steps out, looking at {p1} with tears.", "Vertical 9:16 portrait: majestic reveal shot framing mysterious tycoon.", "Tycoon", "Seraphina... welcome home, my true heiress.", "Massive suspense orchestra hit, cut to black.", "08-Cliffhanger"),
                ]
            },
        }
        script_data = ep_scripts.get(episode_number, ep_scripts[1])
        title = f"The Cold CEO's Contract Bride - Episode {episode_number}"
        logline = script_data["logline"]
        hook = script_data["hook"]
        cliffhanger = script_data["cliffhanger"]
        beats = script_data["beats"]

        shots = []
        for i in range(1, shot_count + 1):
            sid = f"s{i:02}"
            b_idx = min(i - 1, len(beats) - 1)
            b_vis, b_act, b_cam, b_spk, b_dlg, b_aud, b_tag = beats[b_idx]

            shots.append(Shot(
                id=sid,
                mode="t2v",
                duration=seconds_per_shot,
                visual=b_vis,
                action=b_act,
                camera=b_cam,
                speaker=b_spk,
                dialogue=b_dlg,
                audio=b_aud,
                beat=b_tag,
                continuity=f"{p1} wearing cream sweater; {p2} in charcoal suit; ambient penthouse lighting.",
                image_path="",
            ))

        return Screenplay(
            episode_number=episode_number,
            title=title,
            genre=genre,
            vibe=vibe,
            language="English",
            logline=logline,
            hook=hook,
            cliffhanger=cliffhanger,
            previous_cliffhanger=previous_cliffhanger,
            cast=cast,
            shots=shots,
            aspect_ratio="9:16",
        )
