"""10-Episode Arc Planner for AI MicroDrama Series Generator.

Generates the dramatic master blueprint for a 10-episode series
(with full architectural structure to scale to 50 episodes).

Divides the series into:
- Act I: The Trap (Episodes 1-3)
- Act II-A: The Thaw & The Threat (Episodes 4-6)
- Act II-B: The Crisis (Episodes 7-9)
- Season 1 Finale: The Climax & True Identity (Episode 10)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EpisodeArcBeat(BaseModel):
    """Dramatic master plan for a single episode within the 10-episode arc."""
    episode_number: int
    title: str
    act_phase: str
    core_objective: str
    hook_type: str
    escalation_twist: str
    cliffhanger_type: str
    cliffhanger_prompt: str
    active_characters: List[str] = Field(default_factory=list)
    thread_to_open: Optional[str] = None
    thread_to_advance: Optional[str] = None
    thread_to_resolve: Optional[str] = None


class SeriesArcPlan(BaseModel):
    """Complete 10-episode structural arc plan."""
    series_title: str
    genre: str
    total_episodes: int = 10
    logline: str
    episodes: List[EpisodeArcBeat] = Field(default_factory=list)


class ArcPlanner:
    """Creates dramatic multi-episode skeletons based on genre and premise."""

    @classmethod
    def plan_contract_marriage_10(cls, title: str = "The Cold CEO's Contract Bride") -> SeriesArcPlan:
        """Create the canonical 10-episode arc for 'The Cold CEO's Contract Bride'."""
        plan = SeriesArcPlan(
            series_title=title,
            genre="contract_marriage",
            total_episodes=10,
            logline="To save her family from bankruptcy, Seraphina signs a 1-year contract marriage with Alexander, a ruthless CEO who vowed never to love, only to find herself trapped in a web of corporate jealousy, deadly secrets, and dangerous passion.",
        )

        beats_data = [
            # ACT I: THE TRAP (Episodes 1-3)
            {
                "episode_number": 1,
                "title": "The Price of Blood",
                "act_phase": "Act I: The Trap",
                "core_objective": "Establish the ruthless marriage contract and publicly humiliate Seraphina",
                "hook_type": "Public Humiliation & Contract Forced",
                "escalation_twist": "Alexander signs the paper without looking her in the eye and coldly lays down 3 rules",
                "cliffhanger_type": "Ultimatum / Doorway Ambush",
                "cliffhanger_prompt": "Alexander grabs Seraphina's wrist at the penthouse threshold: 'Rule number one: you will never ask for my heart, and you will never leave this room without my permission.'",
                "active_characters": ["Seraphina", "Alexander"],
                "thread_to_open": "debt_contract_terms",
            },
            {
                "episode_number": 2,
                "title": "A Bed of Thorns",
                "act_phase": "Act I: The Trap",
                "core_objective": "Enforce forced proximity in the penthouse and reveal Alexander's hidden wound",
                "hook_type": "Direct Resolution of Wrist Grab",
                "escalation_twist": "Seraphina finds Alexander shaking from a nightmare in his study; he reacts with icy fury",
                "cliffhanger_type": "Physical Confrontation / Stare-down",
                "cliffhanger_prompt": "Alexander pins Seraphina against the frosted glass bookcase, breath trembling: 'Did anyone tell you what happened to my last bride?'",
                "active_characters": ["Seraphina", "Alexander"],
                "thread_to_advance": "debt_contract_terms",
                "thread_to_open": "previous_bride_mystery",
            },
            {
                "episode_number": 3,
                "title": "The Viper's Banquet",
                "act_phase": "Act I: The Trap",
                "core_objective": "First high-society public appearance where rival heiress Victoria ambushes Seraphina",
                "hook_type": "High Society Gala Entry",
                "escalation_twist": "Victoria spills champagne on Seraphina's gown, demanding she show her wedding ring",
                "cliffhanger_type": "Public Humiliation Defense",
                "cliffhanger_prompt": "Before Victoria can slap Seraphina, Alexander's hand clamps down on Victoria's wrist in front of 200 photographers: 'Touch my wife again, Victoria, and your family's empire falls by midnight.'",
                "active_characters": ["Seraphina", "Alexander", "Victoria"],
                "thread_to_open": "victoria_rivalry",
            },
            # ACT II-A: THE THAW & THE THREAT (Episodes 4-6)
            {
                "episode_number": 4,
                "title": "Shield of Ice",
                "act_phase": "Act II-A: The Thaw & The Threat",
                "core_objective": "Aftermath of the gala protection; Alexander tends to Seraphina's sprained ankle",
                "hook_type": "Intimate Penthouse Dressing",
                "escalation_twist": "Victoria contacts a tabloid editor with stolen photos of Seraphina's destitute father",
                "cliffhanger_type": "Tabloid Threat Cut",
                "cliffhanger_prompt": "Seraphina's phone buzzes with a photo of her father in an ICU bed: 'Sign the annulment, or his life support gets disconnected tomorrow.'",
                "active_characters": ["Seraphina", "Alexander", "Victoria"],
                "thread_to_advance": "victoria_rivalry",
            },
            {
                "episode_number": 5,
                "title": "The Near Kiss",
                "act_phase": "Act II-A: The Thaw & The Threat",
                "core_objective": "A late-night rain storm traps them in the office; walls crumble between them",
                "hook_type": "Thunderstorm Confinement",
                "escalation_twist": "Alexander confesses why he never trusts anyone, inches from Seraphina's lips",
                "cliffhanger_type": "Interrupted Intimacy Freeze",
                "cliffhanger_prompt": "Alexander leans down, his lips brushing hers, when the security alarm blares: Alexander's private safe has been cracked.",
                "active_characters": ["Seraphina", "Alexander"],
                "thread_to_advance": "previous_bride_mystery",
                "thread_to_open": "safe_breakin_sabotage",
            },
            {
                "episode_number": 6,
                "title": "The Leak",
                "act_phase": "Act II-A: The Thaw & The Threat",
                "core_objective": "The marriage contract is leaked to the board; Victoria claims Seraphina sold it",
                "hook_type": "Boardroom Scandal Confrontation",
                "escalation_twist": "Bank deposit records show $5 million transferred to Seraphina's secret account",
                "cliffhanger_type": "False Accusation Freeze",
                "cliffhanger_prompt": "Alexander looks at Seraphina with shattered, merciless eyes: 'Tell me to my face this isn't your signature on the deposit slip.'",
                "active_characters": ["Seraphina", "Alexander", "Victoria"],
                "thread_to_advance": "safe_breakin_sabotage",
                "thread_to_advance": "victoria_rivalry",
            },
            # ACT II-B: THE CRISIS (Episodes 7-9)
            {
                "episode_number": 7,
                "title": "Trial by Silence",
                "act_phase": "Act II-B: The Crisis",
                "core_objective": "Seraphina is locked in the guest suite; she discovers who actually set her up",
                "hook_type": "Imprisonment & Search",
                "escalation_twist": "Seraphina finds Victoria's monogrammed earring near the hacked computer",
                "cliffhanger_type": "Daring Escape",
                "cliffhanger_prompt": "Seraphina cuts her palm on broken glass to pick the balcony latch, slipping into the pouring rain: 'If you won't believe me, Alexander, I'll bring you the truth myself.'",
                "active_characters": ["Seraphina", "Victoria"],
                "thread_to_advance": "safe_breakin_sabotage",
            },
            {
                "episode_number": 8,
                "title": "The Ambush at the Docks",
                "act_phase": "Act II-B: The Crisis",
                "core_objective": "Seraphina tracks the hacker to a container yard; Victoria's thugs corner her",
                "hook_type": "Rainy Alley Pursuit",
                "escalation_twist": "The hacker reveals that Alexander's previous bride was Victoria's sister",
                "cliffhanger_type": "Life or Death Peril",
                "cliffhanger_prompt": "A thug raises an iron crowbar over Seraphina's head; tires screech as Alexander's black Maybach smashes through the warehouse gate at 60 mph!",
                "active_characters": ["Seraphina", "Alexander", "Victoria"],
                "thread_to_resolve": "safe_breakin_sabotage",
                "thread_to_advance": "previous_bride_mystery",
            },
            {
                "episode_number": 9,
                "title": "Blood and Forgiveness",
                "act_phase": "Act II-B: The Crisis",
                "core_objective": "Alexander shields Seraphina, taking a blow for her; truth is revealed between them",
                "hook_type": "Direct Rescue & Gunshot Cut",
                "escalation_twist": "Alexander bandages her hands with tears in his eyes, begging for forgiveness",
                "cliffhanger_type": "Season Climax Teaser",
                "cliffhanger_prompt": "Alexander burns the contract into ashes before her: 'Tomorrow morning, we face the board not as fake partners, but as husband and wife.'",
                "active_characters": ["Seraphina", "Alexander"],
                "thread_to_resolve": "debt_contract_terms",
            },
            # SEASON 1 FINALE (Episode 10)
            {
                "episode_number": 10,
                "title": "Crown of Thorns (Season Finale)",
                "act_phase": "Season 1 Finale",
                "core_objective": "Grand boardroom confrontation; Victoria exposed; shocking identity reveal & cliffhanger for Season 2",
                "hook_type": "Boardroom Showdown Entry",
                "escalation_twist": "Seraphina plays the audio confession exposing Victoria's embezzlement to police",
                "cliffhanger_type": "Season Finale Massive Cliffhanger",
                "cliffhanger_prompt": "As Victoria is led away in handcuffs, a luxury limousine stops: an older gentleman with a golden cane steps out, looking straight at Seraphina: 'Welcome home, my true heiress.'",
                "active_characters": ["Seraphina", "Alexander", "Victoria"],
                "thread_to_resolve": "victoria_rivalry",
                "thread_to_open": "true_heiress_mystery",
            },
        ]

        plan.episodes = [EpisodeArcBeat(**b) for b in beats_data]
        return plan

    @classmethod
    def plan_custom_series(
        cls,
        title: str,
        genre: str,
        protagonist: str,
        deuteragonist: str,
        antagonist: str,
        episodes_count: int = 10,
    ) -> SeriesArcPlan:
        """Create a dynamic 10-episode arc plan for any custom series."""
        plan = SeriesArcPlan(
            series_title=title,
            genre=genre,
            total_episodes=episodes_count,
            logline=f"{protagonist} is thrown into a high-stakes conflict with {deuteragonist} while battling {antagonist} across 10 escalating episodes.",
        )

        phases = [
            ("Act I: The Setup", "Establish status quo and trigger inciting confrontation"),
            ("Act I: The Bind", "Forced proximity or inescapable pact sealed"),
            ("Act I: First Ambush", "First clash with antagonist testing the fragile alliance"),
            ("Act II-A: The Thaw", "Protagonist and deuteragonist uncover shared vulnerability"),
            ("Act II-A: Near Intimacy", "Romantic or emotional climax interrupted by external threat"),
            ("Act II-A: The Frame-Up", "Antagonist plants damning evidence; trust is shattered"),
            ("Act II-B: The Severing", "Separation or daring escape to find the real truth"),
            ("Act II-B: The Ambush", "Deadly confrontation where deuteragonist intervenes"),
            ("Act II-B: Reconciliation", "Allies reunite with ironclad commitment to face enemy"),
            ("Season 1 Finale", "Public unmasking of antagonist + shocking secret lineage reveal"),
        ]

        for i in range(1, episodes_count + 1):
            phase_idx = min(i - 1, len(phases) - 1)
            act_phase, obj = phases[phase_idx]

            beat = EpisodeArcBeat(
                episode_number=i,
                title=f"Episode {i}: The Turning",
                act_phase=act_phase,
                core_objective=obj,
                hook_type="High-Impact Reversal" if i > 1 else "Inciting Incident Shock",
                escalation_twist=f"Stakes escalate for {protagonist.split()[0]} and {deuteragonist.split()[0]}",
                cliffhanger_type="Season Finale Reveal" if i == episodes_count else "High-Stakes Cliffhanger",
                cliffhanger_prompt=f"Shocking twist at the end of Episode {i} that alters the course of the story.",
                active_characters=[protagonist.split()[0], deuteragonist.split()[0], antagonist.split()[0]],
            )
            plan.episodes.append(beat)

        return plan
