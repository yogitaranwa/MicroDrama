"""DramaBench-style automated quality judge for microdrama screenplays."""

from typing import List
from ..models import Screenplay, QualityScore


class MicrodramaJudge:
    """Evaluates screenplays on viral microdrama metrics."""

    @staticmethod
    def evaluate(screenplay: Screenplay) -> QualityScore:
        """Run rule-based heuristic evaluation on screenplay."""
        feedback_notes: List[str] = []
        
        # 1. Hook evaluation (Shot 1)
        hook_shot = screenplay.shots[0]
        hook_score = 5
        hook_action_lower = hook_shot.action.lower()
        boring_keywords = ["walks slowly", "looks out the window", "wakes up", "sips tea", "thinks about"]
        if any(w in hook_action_lower for w in boring_keywords):
            hook_score = 2
            feedback_notes.append("Hook is too slow. Start in media res with an immediate crisis.")

        # 2. Cliffhanger evaluation (Final Shot)
        final_shot = screenplay.shots[-1]
        cliffhanger_score = 5
        final_action_lower = final_shot.action.lower()
        resolving_keywords = ["smiles happily", "walks off into the sunset", "they hug", "everything is fine"]
        if any(w in final_action_lower for w in resolving_keywords):
            cliffhanger_score = 1
            feedback_notes.append("Ending resolves the conflict! Microdramas MUST end on a sharp cliffhanger.")

        # 3. Dialogue snappiness
        dialogue_score = 5
        max_words = 0
        for s in screenplay.shots:
            if s.dialogue:
                wc = len(s.dialogue.split())
                if wc > max_words:
                    max_words = wc
        if max_words > 15:
            dialogue_score = 3
            feedback_notes.append(f"Longest dialogue line has {max_words} words. Keep lines under 12-15 words.")

        # 4. Continuity check
        continuity_score = 5
        for s in screenplay.shots:
            if not s.continuity or len(s.continuity) < 10:
                continuity_score = 3
                feedback_notes.append(f"Shot {s.id} is missing detailed continuity markers.")
                break

        # 5. Shootability & Vertical framing
        shootability_score = 5
        for s in screenplay.shots:
            cam_lower = s.camera.lower()
            if "vertical" not in cam_lower and "9:16" not in cam_lower and "portrait" not in cam_lower:
                shootability_score = 3
                feedback_notes.append(f"Shot {s.id} camera instructions lack explicit 9:16 vertical portrait framing.")
                break

        # 6. Escalation
        escalation_score = 4 if len(screenplay.shots) >= 4 else 2

        is_approved = (
            hook_score >= 3
            and cliffhanger_score >= 3
            and dialogue_score >= 3
            and shootability_score >= 3
            and continuity_score >= 3
        )

        return QualityScore(
            hook_score=hook_score,
            escalation_score=escalation_score,
            cliffhanger_score=cliffhanger_score,
            dialogue_score=dialogue_score,
            continuity_score=continuity_score,
            shootability_score=shootability_score,
            feedback="; ".join(feedback_notes) if feedback_notes else "Screenplay passes all microdrama quality metrics.",
            is_approved=is_approved,
        )
