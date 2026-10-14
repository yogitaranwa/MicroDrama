"""Registry for microdrama templates."""

from typing import Dict, List, Optional
from ..models import GenreTemplate
from .billionaire import BILLIONAIRE_TEMPLATE
from .revenge import REVENGE_TEMPLATE
from .contract_marriage import CONTRACT_MARRIAGE_TEMPLATE
from .werewolf_mafia import WEREWOLF_MAFIA_TEMPLATE
from .thriller_loop import THRILLER_LOOP_TEMPLATE

TEMPLATE_REGISTRY: Dict[str, GenreTemplate] = {
    BILLIONAIRE_TEMPLATE.id: BILLIONAIRE_TEMPLATE,
    REVENGE_TEMPLATE.id: REVENGE_TEMPLATE,
    CONTRACT_MARRIAGE_TEMPLATE.id: CONTRACT_MARRIAGE_TEMPLATE,
    WEREWOLF_MAFIA_TEMPLATE.id: WEREWOLF_MAFIA_TEMPLATE,
    THRILLER_LOOP_TEMPLATE.id: THRILLER_LOOP_TEMPLATE,
}


def get_template(template_id: str) -> Optional[GenreTemplate]:
    """Retrieve template by ID or slug."""
    if not template_id:
        return None
    cleaned = template_id.strip().lower()
    return TEMPLATE_REGISTRY.get(cleaned)


def list_templates() -> List[GenreTemplate]:
    """List all registered genre templates."""
    return list(TEMPLATE_REGISTRY.values())
