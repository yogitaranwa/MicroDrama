"""Pydantic data models for MicroDrama generator."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class Character(BaseModel):
    """Character model defining appearance, voice, role, and visual reference."""
    name: str = Field(..., description="Unique character name (e.g. 'Maya', 'Julian')")
    role: str = Field("Protagonist", description="Role in drama: Protagonist, Antagonist, Ally, Rival")
    look: str = Field(..., description="Detailed visual appearance, facial features, hairstyle, clothing, distinctive accessories")
    voice: str = Field("Natural, expressive", description="Voice tone, pitch, cadence, and accent")
    reference_image_path: Optional[str] = Field(None, description="Local path or URL to character reference image")
    api_asset_path: Optional[str] = Field(None, description="Magic Hour uploaded asset path (e.g. api-assets/...)")


class Beat(BaseModel):
    """Dramatic beat in a microdrama episode."""
    id: int = Field(..., description="Beat index 1..N")
    beat_type: str = Field("conflict_escalation", description="Category of dramatic beat")
    summary: str = Field(..., description="Concise description of the dramatic action")
    emotional_stakes: str = Field(..., description="Tension shift or emotional charge (e.g. Suspicion -> Dread)")
    duration_seconds: int = Field(8, description="Target duration in seconds for this beat")


class BeatSheet(BaseModel):
    """Outline plan for a microdrama episode before full scriptwriting."""
    episode_number: int = Field(1, ge=1, description="Episode number in the series")
    title: str = Field("Untitled Microdrama", description="Episode title")
    genre: str = Field("Suspense", description="Genre of the drama")
    logline: str = Field(..., description="One-sentence hook and premise")
    hook_promise: str = Field(..., description="What hooks the audience in the first 3 seconds (resolves prior cliffhanger if ep > 1)")
    cliffhanger_promise: str = Field(..., description="The unresolvable cliffhanger or shocking twist ending for this episode")
    beats: List[Beat] = Field(..., description="Sequence of 4 to 12 dramatic beats")
    previous_cliffhanger: Optional[str] = Field(None, description="Cliffhanger from previous episode that must be resolved")


class Shot(BaseModel):
    """Individual filmable shot for video generation."""
    id: str = Field(..., description="Shot ID formatted as 's01', 's02', etc.")
    mode: Literal["t2v", "i2v"] = Field("t2v", description="Text-to-video or Image-to-video")
    duration: int = Field(8, ge=1, le=60, description="Duration in seconds (typically 5 to 10s)")
    visual: str = Field(..., description="Filmic description of the environment, lighting, and subjects")
    action: str = Field(..., description="Specific physical motion: slap, grab, sprint, slam door, gasp")
    camera: str = Field(..., description="Portrait 9:16 camera motion, framing, angle (close-up, push-in, low angle)")
    speaker: str = Field("", description="Character speaking or empty string if no dialogue")
    dialogue: str = Field("", description="Punchy spoken line, strictly under 15 words, or empty string")
    audio: str = Field("Dramatic score and room ambience", description="Sound design, foley, stings, acoustic beats")
    beat: str = Field("", description="Dramatic purpose (e.g. '01-Hook', '08-Cliffhanger')")
    continuity: str = Field("", description="Wardrobe, props, wounds, and lighting continuity constraints")
    image_path: str = Field("", description="Image path for I2V mode, or empty for T2V")

    @field_validator("dialogue")
    @classmethod
    def validate_dialogue_length(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) > 20:
            raise ValueError(f"Dialogue is too long for a microdrama shot ({len(words)} words > 20 words max). Keep lines punchy and fast.")
        return v


class Screenplay(BaseModel):
    """Complete microdrama episode screenplay."""
    episode_number: int = Field(1, ge=1, description="Episode number in the series")
    title: str = Field("Untitled Episode", description="Episode title")
    genre: str = Field("Suspense", description="Drama genre")
    vibe: str = Field("Tense, thrilling", description="Atmospheric vibe")
    language: str = Field("English", description="Spoken language")
    logline: str = Field("", description="Core premise summary")
    hook: str = Field("", description="0-3s hook description (resolves prior cliffhanger if ep > 1)")
    cliffhanger: str = Field("", description="Episode ending cliffhanger description")
    previous_cliffhanger: Optional[str] = Field(None, description="Previous episode cliffhanger resolved in shot 1")
    series_context: Optional[str] = Field(None, description="Cumulative canon context from earlier episodes")
    cast: List[Character] = Field(..., min_length=1, max_length=4, description="1 to 4 main characters")
    shots: List[Shot] = Field(..., min_length=1, max_length=12, description="1 to 12 consecutive shots")
    aspect_ratio: str = Field("9:16", description="Video aspect ratio, default 9:16 vertical")


class SeriesBible(BaseModel):
    """Running series continuity tracker across multiple episodes."""
    title: str = Field("Untitled Series", description="Series title")
    template_id: str = Field("contract_marriage", description="Genre template ID")
    cast: List[Character] = Field(default_factory=list, description="Canonical cast with persistent looks and assets")
    episodes: List[Screenplay] = Field(default_factory=list, description="List of generated screenplays in sequence")
    canon_events: List[str] = Field(default_factory=list, description="Running established facts and secrets revealed")
    last_cliffhanger: str = Field("", description="Cliffhanger ending of the latest episode")


class GenreTemplate(BaseModel):
    """Template capturing microdrama genre conventions, tropes, and formulas."""
    id: str = Field(..., description="Unique slug for the template")
    name: str = Field(..., description="Display title (e.g. 'The Hidden Billionaire')")
    genre: str = Field(..., description="Parent genre")
    vibe: str = Field(..., description="Emotional tone and aesthetic")
    description: str = Field(..., description="Overview of the trope and story dynamics")
    signature_hook: str = Field(..., description="Typical opening hook pattern")
    climax_tropes: List[str] = Field(default_factory=list, description="Common mid-episode conflict moments")
    cliffhanger_formulas: List[str] = Field(default_factory=list, description="High-impact ending patterns")
    default_cast: List[Character] = Field(default_factory=list, description="Starter archetypes")
    pacing_rules: str = Field(..., description="Pacing and dialogue tempo instructions")
    suggested_shots: int = Field(8, description="Ideal shot count")
    seconds_per_shot: int = Field(8, description="Ideal shot duration")


class QualityScore(BaseModel):
    """Evaluation score based on DramaBench & microdrama metrics."""
    hook_score: int = Field(..., ge=1, le=5, description="Hook intensity (1-5)")
    escalation_score: int = Field(..., ge=1, le=5, description="Pacing and conflict escalation (1-5)")
    cliffhanger_score: int = Field(..., ge=1, le=5, description="Cliffhanger dopamine punch (1-5)")
    dialogue_score: int = Field(..., ge=1, le=5, description="Dialogue snappiness & voice distinction (1-5)")
    continuity_score: int = Field(..., ge=1, le=5, description="Entity, wardrobe, and logic consistency (1-5)")
    shootability_score: int = Field(..., ge=1, le=5, description="Filmability in vertical 9:16 (1-5)")
    feedback: str = Field("", description="Critique and specific repair instructions")
    is_approved: bool = Field(False, description="Whether script passes production gate")
