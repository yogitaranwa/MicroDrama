"""Archetype sanitization and genre taxonomy engine.

Translates copyrighted IP names into original, compelling archetypes (Option B)
and provides standardized genre definitions for Netflix/Kuku FM style metadata.
"""

import re
from typing import Any, Dict, List, Optional


# IP translation lookup dictionary (case-insensitive key matching)
IP_REPLACEMENTS = {
    # Harry Potter Universe
    r"\bharry potter\b": "Henry Ashford",
    r"\bharrys?\b": "Henry",
    r"\bhermione granger\b": "Helena Vance",
    r"\bhermiones?\b": "Helena",
    r"\bron weasley\b": "Rowan Miller",
    r"\brons?\b": "Rowan",
    r"\bdraco malfoy\b": "Julian Sterling",
    r"\bdracos?\b": "Julian",
    r"\blord voldemort\b": "Malakor",
    r"\bvoldemorts?\b": "Malakor",
    r"\bseverus snape\b": "Professor Damian Vane",
    r"\bsnapes?\b": "Professor Vane",
    r"\balbus dumbledore\b": "Archmage Aurelius",
    r"\bdumbledores?\b": "Archmage Aurelius",
    r"\bhogwarts\b": "Aethelgard Arcane Academy",
    r"\bgryffindors?\b": "House Solaris",
    r"\bslytherins?\b": "House Obsidian",
    r"\bravenclaws?\b": "House Lunaris",
    r"\bhufflepuffs?\b": "House Terra",
    r"\bdeath eaters?\b": "Shadow Syndicate",
    r"\bquidditch\b": "Skyblade Duel",
    r"\bministry of magic\b": "High Magisterium",

    # Twilight Universe
    r"\bella swan\b": "Isla Ward",
    r"\bedward cullen\b": "Lucien Thorne",
    r"\bjacob black\b": "Jaxon Cruz",
    r"\bforks\b": "Blackwood Cove",
    r"\bvolturis?\b": "The Sanguine Coven",

    # Superhero / Pop IP
    r"\bbatman\b": "Night Sentinel",
    r"\bbruce wayne\b": "Kaelen Drake",
    r"\bjoker\b": "The Harlequin",
}

GENRE_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "contract_marriage": {
        "display_name": "Contract Marriage & Cold CEO",
        "category": "Romance & Power Struggle",
        "default_title": "The Cold CEO's Contract Bride",
        "mood": "Sultry, Possessive, Emotional Rollercoaster",
        "themes": ["Contractual love", "Billionaire possessiveness", "Class divide", "Hidden vulnerability"],
        "default_protagonist": {
            "name": "Seraphina",
            "role": "Protagonist",
            "archetype": "Trapped Heroine",
            "look": "Delicate features, dark auburn wavy hair, expressive amber eyes, wearing a simple cream cashmere sweater",
            "voice": "Soft-spoken, defiant under pressure, elegant",
        },
        "default_deuteragonist": {
            "name": "Alexander",
            "role": "Deuteragonist",
            "archetype": "Cold CEO",
            "look": "Tall athletic build, piercing hazel eyes, sculpted jaw, charcoal bespoke tailored Italian suit",
            "voice": "Deep, authoritative baritone, cold and measured",
        },
        "default_antagonist": {
            "name": "Victoria",
            "role": "Antagonist",
            "archetype": "Scheming Heiress",
            "look": "Glamorous crimson silk gown, diamond choker, sleek platinum blonde bob, haughty sharp gaze",
            "voice": "Silky, venomous, condescending",
        },
    },
    "revenge_comeback": {
        "display_name": "Revenge & Identity Reveal",
        "category": "Power Fantasy & Drama",
        "default_title": "The Queen's Rebirth",
        "mood": "Intense, Triumphant, High-Stakes",
        "themes": ["Scorned daughter returns", "Secret wealth", "Public payback", "Unmasking traitors"],
        "default_protagonist": {
            "name": "Evelyn Vance",
            "role": "Protagonist",
            "archetype": "Reborn Heiress",
            "look": "Sharp cheekbones, jet black sleek ponytail, emerald satin power suit, cold regal demeanor",
            "voice": "Crisp, unshakeable, razor-sharp",
        },
        "default_deuteragonist": {
            "name": "Caspian Stone",
            "role": "Deuteragonist",
            "archetype": "Shadow Protector",
            "look": "Rugged billionaire financier, dark trench coat, piercing grey eyes, scar across knuckles",
            "voice": "Low, protective, deliberate",
        },
        "default_antagonist": {
            "name": "Marcus Kane",
            "role": "Antagonist",
            "archetype": "Traitorous Ex-Fiancé",
            "look": "Smug handsome face, tailored navy blazer, gold watch, nervous fidget when cornered",
            "voice": "Arrogant, quickly faltering when challenged",
        },
    },
    "arcane_academy": {
        "display_name": "Arcane Academy & Bloodline Prodigy",
        "category": "Fantasy & Supernatural",
        "default_title": "The Banished Prodigy of Aethelgard",
        "mood": "Mysterious, High-Tension, Epic",
        "themes": ["Hidden lineage", "Forbidden sorcery", "Academy rivalry", "Ancient threat returning"],
        "default_protagonist": {
            "name": "Henry Ashford",
            "role": "Protagonist",
            "archetype": "Marked Prodigy",
            "look": "Ruffled dark hair, silver rune mark on left wrist, dark academic uniform with silver trim",
            "voice": "Earnest, determined, quiet intensity",
        },
        "default_deuteragonist": {
            "name": "Helena Vance",
            "role": "Deuteragonist",
            "archetype": "Sharp-witted Scholar",
            "look": "Curly amber hair, wire-frame glasses, satchel filled with ancient grimoires",
            "voice": "Fast-paced, incisive, intellectually fierce",
        },
        "default_antagonist": {
            "name": "Julian Sterling",
            "role": "Antagonist",
            "archetype": "Obsidian Aristocrat",
            "look": "Sleek silver-blond hair, high collar obsidian coat, smirk holding an engraved wand",
            "voice": "Condescending, aristocratic, cold drawl",
        },
    },
    "hidden_billionaire": {
        "display_name": "Hidden Billionaire Undercover",
        "category": "Power Fantasy & Comeback",
        "default_title": "The Janitor is the Chairman",
        "mood": "Satisfying, Fast-Paced, Dramatic",
        "themes": ["Disguised boss", "Public humiliation turned triumph", "Corporate retribution"],
        "default_protagonist": {
            "name": "Marcus Cole",
            "role": "Protagonist",
            "archetype": "Hidden Chairman",
            "look": "Faded denim jacket, worn work boots, disarmingly calm gaze hiding supreme authority",
            "voice": "Understated, humble until the command switch",
        },
        "default_deuteragonist": {
            "name": "Chloe Lin",
            "role": "Deuteragonist",
            "archetype": "Honest Manager",
            "look": "Neat white blouse, ponytail, clipboard in hand, warm and fair expression",
            "voice": "Professional, empathetic, righteous",
        },
        "default_antagonist": {
            "name": "Bradford Vance",
            "role": "Antagonist",
            "archetype": "Nepo Branch Director",
            "look": "Flashy checked suit, slicked back hair, cigar, obnoxious sneer",
            "voice": "Loud, boisterous, abusive to service staff",
        },
    },
}


class ArchetypeSanitizer:
    """Detects and replaces protected IP names with legally safe original archetypes."""

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Replace known IP character and world names with original archetypes."""
        sanitized = text
        for pattern, replacement in IP_REPLACEMENTS.items():
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize string values in a dictionary."""
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = cls.sanitize_text(v)
            elif isinstance(v, dict):
                result[k] = cls.sanitize_dict(v)
            elif isinstance(v, list):
                result[k] = [
                    cls.sanitize_text(item) if isinstance(item, str)
                    else (cls.sanitize_dict(item) if isinstance(item, dict) else item)
                    for item in v
                ]
            else:
                result[k] = v
        return result

    @classmethod
    def get_genre_info(cls, genre_key: str) -> Dict[str, Any]:
        """Get canonical genre info, falling back to contract_marriage."""
        key = genre_key.lower().replace(" ", "_")
        return GENRE_TAXONOMY.get(key, GENRE_TAXONOMY["contract_marriage"])

    @classmethod
    def list_available_genres(cls) -> List[str]:
        """Return list of supported genre keys."""
        return list(GENRE_TAXONOMY.keys())
