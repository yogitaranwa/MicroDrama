"""Series Bible Engine for 10-episode (and 50-episode) continuous microdrama arcs.

Persists full narrative memory to plain JSON at the series root:
outputs/{series_slug}/series_bible.json

Tracks:
- Characters & wardrobe state
- Status (alive, dead, missing)
- Secrets visibility matrix
- Cliffhanger ledger with TTL enforcement (1-3 episodes)
- Open & advancing plot threads
- Canonical world events
- Compact context generator for LLM prompts (~4k-6k tokens)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class BibleCharacter(BaseModel):
    """Rich character state preserved across episodes."""
    name: str
    role: str = "Protagonist"
    archetype: str = "Heroine"
    look: str
    voice: str = "Natural, expressive"
    wardrobe_current: str = ""
    status: str = "alive"  # alive, deceased, missing, transformed
    reference_image_path: Optional[str] = None
    api_asset_path: Optional[str] = None
    secrets_known: List[str] = Field(default_factory=list)
    secrets_hidden: List[str] = Field(default_factory=list)
    appearances: List[int] = Field(default_factory=list)


class Relationship(BaseModel):
    """Dynamic relationship edge between two characters."""
    char_a: str
    char_b: str
    relation_type: str  # rival, contract_spouse, lover, boss, enemy
    status: str = "active"  # active, strained, broken, allied
    since_episode: int = 1


class CliffhangerRecord(BaseModel):
    """Unresolved dramatic ending with strict TTL tracking."""
    episode_num: int
    text: str
    resolved: bool = False
    resolved_in_episode: Optional[int] = None
    ttl_episodes: int = 3  # Must be resolved within 1 to 3 episodes


class PlotThread(BaseModel):
    """Running narrative promise tracked across the series."""
    id: str
    title: str
    setup_episode: int
    target_resolution_episode: int
    status: str = "open"  # open, advanced, resolved, abandoned
    touch_episodes: List[int] = Field(default_factory=list)


class CanonEvent(BaseModel):
    """Irreversible established fact or revelation."""
    id: int
    episode_num: int
    event: str
    revealed_to: List[str] = Field(default_factory=list)


class SeriesBibleState(BaseModel):
    """Full serialized state for series_bible.json."""
    series_title: str = "Untitled Series"
    genre: str = "contract_marriage"
    target_episodes: int = 10
    logline: str = ""
    characters: Dict[str, BibleCharacter] = Field(default_factory=dict)
    relationships: List[Relationship] = Field(default_factory=list)
    cliffhangers: List[CliffhangerRecord] = Field(default_factory=list)
    plot_threads: List[PlotThread] = Field(default_factory=list)
    canon_events: List[CanonEvent] = Field(default_factory=list)
    episode_recaps: Dict[int, str] = Field(default_factory=dict)


class SeriesBibleManager:
    """Manages reading, mutating, and persisting the Series Bible JSON."""

    def __init__(self, bible_path: Path):
        self.bible_path = Path(bible_path)
        self.state = SeriesBibleState()
        if self.bible_path.exists():
            self.load()

    def load(self) -> None:
        """Load Bible state from disk."""
        with open(self.bible_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.state = SeriesBibleState.model_validate(data)

    def commit(self) -> None:
        """Commit current Bible state to disk in human-readable JSON."""
        self.bible_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.bible_path, "w", encoding="utf-8") as f:
            json.dump(self.state.model_dump(), f, indent=2, ensure_ascii=False)

    def initialize_series(
        self,
        title: str,
        genre: str,
        logline: str,
        target_episodes: int = 10,
        initial_characters: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Initialize a new Series Bible with foundational metadata and cast."""
        self.state.series_title = title
        self.state.genre = genre
        self.state.logline = logline
        self.state.target_episodes = target_episodes

        if initial_characters:
            for char_data in initial_characters:
                char_obj = BibleCharacter(**char_data)
                self.state.characters[char_obj.name] = char_obj

        self.commit()

    def get_character(self, name: str) -> Optional[BibleCharacter]:
        """Get character state by name."""
        return self.state.characters.get(name)

    def add_or_update_character(self, character: BibleCharacter) -> None:
        """Add or update a character in the Bible."""
        self.state.characters[character.name] = character

    def get_dead_characters(self) -> Set[str]:
        """Return names of all characters marked as deceased."""
        return {
            name for name, c in self.state.characters.items()
            if c.status.lower() in ("dead", "deceased")
        }

    def record_episode_appearance(self, episode_num: int, character_names: List[str]) -> None:
        """Mark characters as having appeared in a specific episode."""
        for name in character_names:
            if name in self.state.characters:
                if episode_num not in self.state.characters[name].appearances:
                    self.state.characters[name].appearances.append(episode_num)

    def record_cliffhanger(self, episode_num: int, text: str) -> None:
        """Record the ending cliffhanger of an episode with TTL counter."""
        record = CliffhangerRecord(
            episode_num=episode_num,
            text=text,
            resolved=False,
            ttl_episodes=3,
        )
        self.state.cliffhangers.append(record)

    def resolve_cliffhanger(self, episode_num: int, resolving_episode: int) -> bool:
        """Mark a previous episode cliffhanger as resolved."""
        for ch in self.state.cliffhangers:
            if ch.episode_num == episode_num and not ch.resolved:
                ch.resolved = True
                ch.resolved_in_episode = resolving_episode
                return True
        return False

    def get_last_cliffhanger(self) -> Optional[CliffhangerRecord]:
        """Get the most recent cliffhanger recorded."""
        if not self.state.cliffhangers:
            return None
        return self.state.cliffhangers[-1]

    def get_unresolved_cliffhangers(self) -> List[CliffhangerRecord]:
        """Get all unresolved cliffhangers currently open."""
        return [ch for ch in self.state.cliffhangers if not ch.resolved]

    def get_overdue_cliffhangers(self, current_episode: int) -> List[CliffhangerRecord]:
        """Find cliffhangers that are at or near their TTL expiration (>= 2 episodes old)."""
        overdue = []
        for ch in self.state.cliffhangers:
            if not ch.resolved:
                age = current_episode - ch.episode_num
                if age >= 2:
                    overdue.append(ch)
        return overdue

    def add_plot_thread(
        self,
        thread_id: str,
        title: str,
        setup_episode: int,
        target_resolution_episode: int,
    ) -> None:
        """Register a new overarching plot thread."""
        thread = PlotThread(
            id=thread_id,
            title=title,
            setup_episode=setup_episode,
            target_resolution_episode=target_resolution_episode,
            status="open",
            touch_episodes=[setup_episode],
        )
        self.state.plot_threads.append(thread)

    def touch_plot_thread(
        self,
        thread_id: str,
        current_episode: int,
        new_status: Optional[str] = None,
    ) -> None:
        """Record that a plot thread was advanced or resolved in an episode."""
        for t in self.state.plot_threads:
            if t.id == thread_id:
                if current_episode not in t.touch_episodes:
                    t.touch_episodes.append(current_episode)
                if new_status:
                    t.status = new_status
                elif t.status == "open":
                    t.status = "advanced"

    def get_open_plot_threads(self) -> List[PlotThread]:
        """Get all active, unresolved plot threads."""
        return [t for t in self.state.plot_threads if t.status in ("open", "advanced")]

    def record_canon_event(
        self,
        episode_num: int,
        event: str,
        revealed_to: Optional[List[str]] = None,
    ) -> None:
        """Record a permanent story fact established in an episode."""
        next_id = len(self.state.canon_events) + 1
        self.state.canon_events.append(
            CanonEvent(
                id=next_id,
                episode_num=episode_num,
                event=event,
                revealed_to=revealed_to or [],
            )
        )

    def record_episode_recap(self, episode_num: int, summary: str) -> None:
        """Store concise 2-sentence summary of an episode for rolling context."""
        self.state.episode_recaps[episode_num] = summary

    def get_compact_context_pack(self, target_episode: int) -> str:
        """Generate a compact, token-efficient context pack for Gemini screenwriting (~3-5k chars)."""
        lines = []
        lines.append(f"=== SERIES BIBLE CONTEXT PACK (Target: Episode {target_episode}) ===")
        lines.append(f"Series: {self.state.series_title} | Genre: {self.state.genre}")
        lines.append(f"Premise: {self.state.logline}\n")

        # Prior Cliffhanger that MUST be addressed in Shot 1
        if target_episode > 1:
            prev_ep = target_episode - 1
            matching_ch = next(
                (ch for ch in self.state.cliffhangers if ch.episode_num == prev_ep),
                None
            )
            if matching_ch:
                lines.append(f"MANDATORY HOOK REQUIREMENT:")
                lines.append(f"Episode {prev_ep} Cliffhanger to resolve in Shot 1:")
                lines.append(f"\"{matching_ch.text}\"\n")

        # Overdue cliffhangers requiring emergency resolution
        overdue = self.get_overdue_cliffhangers(target_episode)
        if overdue:
            lines.append("OVERDUE CLIFFHANGERS (Force resolve immediately):")
            for od in overdue:
                lines.append(f"- From Episode {od.episode_num}: {od.text}")
            lines.append("")

        # Rolling 3-episode recaps
        recaps = []
        for ep in range(max(1, target_episode - 3), target_episode):
            if ep in self.state.episode_recaps:
                recaps.append(f"- Ep {ep}: {self.state.episode_recaps[ep]}")
        if recaps:
            lines.append("RECENT EPISODE RECAPS:")
            lines.extend(recaps)
            lines.append("")

        # Active Plot Threads
        open_threads = self.get_open_plot_threads()
        if open_threads:
            lines.append("ACTIVE PLOT THREADS (Advance at least one):")
            for t in open_threads:
                lines.append(f"- [{t.id}] {t.title} (Target finale: Ep {t.target_resolution_episode})")
            lines.append("")

        # Cast States
        lines.append("CANONICAL CAST & CURRENT STATES:")
        for name, char in self.state.characters.items():
            status_str = f" [{char.status.upper()}]" if char.status != "alive" else ""
            wardrobe_str = f" | Wardrobe: {char.wardrobe_current}" if char.wardrobe_current else ""
            lines.append(f"- {name} ({char.role} - {char.archetype}){status_str}: {char.look}{wardrobe_str}")
        lines.append("")

        # Recent Canon Facts (last 5)
        recent_facts = self.state.canon_events[-5:] if self.state.canon_events else []
        if recent_facts:
            lines.append("ESTABLISHED WORLD FACTS:")
            for f in recent_facts:
                lines.append(f"- (Ep {f.episode_num}) {f.event}")
            lines.append("")

        lines.append("=== END BIBLE CONTEXT ===")
        return "\n".join(lines)
