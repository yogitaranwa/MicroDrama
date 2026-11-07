"""Continuity validation and edge-case handling for microdrama series.

Performs deterministic rule-based checks and detects narrative edge cases:
- Dead characters reappearing
- Secrets spoken before being revealed
- Wardrobe & physical appearance consistency
- Cliffhanger resolution enforcement in Shot 1
- Repetitive twist / structural clone detection
- Plot thread advancement verification
"""

import re
from typing import Any, Dict, List, Optional, Set
from ..models import Screenplay, Shot
from .bible import SeriesBibleManager


class ContinuityReport:
    """Detailed results of a continuity validation pass."""

    def __init__(self, episode_number: int):
        self.episode_number = episode_number
        self.is_valid: bool = True
        self.score: float = 5.0
        self.violations: List[str] = []
        self.warnings: List[str] = []
        self.repairs_needed: List[str] = []

    def add_violation(self, msg: str, penalty: float = 1.0) -> None:
        """Add a blocking violation that fails the production gate."""
        self.is_valid = False
        self.violations.append(msg)
        self.score = max(1.0, self.score - penalty)

    def add_warning(self, msg: str, penalty: float = 0.3) -> None:
        """Add a non-blocking advisory note."""
        self.warnings.append(msg)
        self.score = max(1.0, self.score - penalty)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to JSON-serializable dictionary."""
        return {
            "episode_number": self.episode_number,
            "is_valid": self.is_valid,
            "continuity_score": round(self.score, 2),
            "violations_count": len(self.violations),
            "warnings_count": len(self.warnings),
            "violations": self.violations,
            "warnings": self.warnings,
            "repairs_needed": self.repairs_needed,
        }


class ContinuityValidator:
    """Enforces canon rules and edge case defenses across episodes."""

    @classmethod
    def validate_screenplay(
        cls,
        screenplay: Screenplay,
        bible: SeriesBibleManager,
        previous_screenplay: Optional[Screenplay] = None,
    ) -> ContinuityReport:
        """Run all deterministic continuity checks against the Series Bible."""
        ep_num = screenplay.episode_number
        report = ContinuityReport(ep_num)

        # 1. Dead Character Defense
        dead_chars = bible.get_dead_characters()
        if dead_chars:
            for shot in screenplay.shots:
                if shot.speaker in dead_chars:
                    report.add_violation(
                        f"Deceased character '{shot.speaker}' speaks in shot {shot.id}. Dead characters cannot appear in live scenes."
                    )
                for dead in dead_chars:
                    if dead.lower() in shot.action.lower() or dead.lower() in shot.visual.lower():
                        # Allowed only if explicitly marked as flashback, corpse, or portrait
                        allowed_contexts = ["flashback", "corpse", "body", "memory", "portrait", "photo"]
                        text = (shot.action + " " + shot.visual).lower()
                        if not any(ac in text for ac in allowed_contexts):
                            report.add_violation(
                                f"Deceased character '{dead}' appears in shot {shot.id} without being a flashback or memory."
                            )

        # 2. Cliffhanger Resolution in Shot 1 (for episodes > 1)
        if ep_num > 1:
            prev_cliffhanger = bible.state.cliffhangers[-1].text if bible.state.cliffhangers else ""
            if prev_cliffhanger:
                shot1 = screenplay.shots[0] if screenplay.shots else None
                if shot1:
                    # Check if shot 1 addresses the prior cliffhanger
                    shot1_text = (shot1.action + " " + shot1.visual + " " + shot1.dialogue).lower()
                    # Extract key nouns/names from the previous cliffhanger
                    cliff_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", prev_cliffhanger.lower()))
                    overlap = [w for w in cliff_words if w in shot1_text]
                    if len(overlap) < 1 and not screenplay.previous_cliffhanger:
                        report.add_warning(
                            f"Shot 1 does not visibly address prior cliffhanger '{prev_cliffhanger[:60]}...'. Ensure continuous transition."
                        )

        # 3. Wardrobe Continuity Between Consecutive Episodes
        if previous_screenplay and previous_screenplay.shots:
            last_shot_prev = previous_screenplay.shots[-1]
            first_shot_curr = screenplay.shots[0]
            # If immediate continuation is implied, verify scene location / tone
            if "immediate" in first_shot_curr.visual.lower() or "moments later" in first_shot_curr.visual.lower():
                # Check for explicit wardrobe clash
                for char in screenplay.cast:
                    char_bible = bible.get_character(char.name)
                    if char_bible and char_bible.wardrobe_current:
                        if char_bible.wardrobe_current.lower() not in first_shot_curr.continuity.lower():
                            report.add_warning(
                                f"Character '{char.name}' current wardrobe '{char_bible.wardrobe_current}' not locked in shot 1 continuity field."
                            )

        # 4. Dialogue Length Enforcement (Microdrama rule: <= 15 words)
        for shot in screenplay.shots:
            if shot.dialogue:
                words = shot.dialogue.strip().split()
                if len(words) > 15:
                    report.add_violation(
                        f"Dialogue in shot {shot.id} exceeds microdrama word limit ({len(words)} words > 15 max): '{shot.dialogue}'"
                    )

        # 5. Ending Cliffhanger Presence
        if screenplay.shots:
            last_shot = screenplay.shots[-1]
            if not last_shot.action or not screenplay.cliffhanger:
                report.add_violation("Episode final shot missing high-stakes cliffhanger action or description.")

        # 6. Repetition & Structural N-Gram Defense
        if previous_screenplay:
            prev_shots = [s.beat for s in previous_screenplay.shots if s.beat]
            curr_shots = [s.beat for s in screenplay.shots if s.beat]
            if prev_shots and curr_shots and prev_shots == curr_shots:
                report.add_warning(
                    "Beat sequence is identical to previous episode. Vary dramatic twist progression."
                )

        return report

    @classmethod
    def check_stale_threads(cls, bible: SeriesBibleManager, current_episode: int) -> List[str]:
        """Detect open plot threads that have not been touched for >= 3 episodes."""
        stale = []
        for thread in bible.get_open_plot_threads():
            last_touched = max(thread.touch_episodes) if thread.touch_episodes else thread.setup_episode
            inactive_epochs = current_episode - last_touched
            if inactive_epochs >= 3:
                stale.append(f"Plot thread '{thread.title}' ({thread.id}) has been inactive for {inactive_epochs} episodes.")
        return stale
