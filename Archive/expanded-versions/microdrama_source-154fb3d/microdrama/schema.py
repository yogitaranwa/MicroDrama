from dataclasses import dataclass, field, asdict
from typing import List, Optional
import json

@dataclass
class Character:
    name: str
    description: str = ""
    ref_image: Optional[str] = None
    voice: str = ""

@dataclass
class Brief:
    prompt: str
    characters: List[Character] = field(default_factory=list)
    template: str = "hidden_identity"
    duration_s: int = 60
    language: str = "en"
    style: str = "cinematic vertical 9:16, glossy shortform drama look"
    scenes: List[str] = field(default_factory=list)
    episode_number: int = 1

@dataclass
class Shot:
    idx: int
    start_s: float
    dur_s: float
    beat: str
    visual: str
    camera: str
    characters: List[str]
    speaker: Optional[str]
    dialogue: str
    emotion: str
    sfx_music: str = ""

@dataclass
class Script:
    title: str
    logline: str
    cliffhanger: str
    next_episode_teaser: str
    shots: List[Shot]

    def to_json(self):
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @staticmethod
    def from_dict(d):
        shots = [Shot(**s) for s in d["shots"]]
        return Script(d["title"], d["logline"], d["cliffhanger"], d.get("next_episode_teaser", ""), shots)
