from functools import lru_cache
from pathlib import Path

from agno.skills import Skills
from agno.skills.loaders import LocalSkills


@lru_cache
def get_skills() -> Skills:
    """Carrega (uma única vez) todas as skills desta pasta.

    Cada subpasta com um SKILL.md é uma skill; pastas sem SKILL.md são
    ignoradas pelo loader.
    """
    return Skills(loaders=[LocalSkills(str(Path(__file__).parent))])


__all__ = ["get_skills"]
