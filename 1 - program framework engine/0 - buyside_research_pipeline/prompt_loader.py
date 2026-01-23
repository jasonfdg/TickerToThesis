"""
Prompt Loader
=============
Cached loading of all prompt files for the pipeline.
"""

from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

try:
    from .config import (
        ANALYST_ROLE_PATH,
        RD_REVIEW_ROLE_PATH,
        RD_SYNTHESIS_ROLE_PATH,
        MEMO_ENGINE_PATH,
        HUMAN_READABLE_ENGINE_PATH,
        SOURCE_SCOUT_AGENT_PATH,
        INVESTING_TYPES,
        get_investing_type_path,
    )
except ImportError:
    from config import (
        ANALYST_ROLE_PATH,
        RD_REVIEW_ROLE_PATH,
        RD_SYNTHESIS_ROLE_PATH,
        MEMO_ENGINE_PATH,
        HUMAN_READABLE_ENGINE_PATH,
        SOURCE_SCOUT_AGENT_PATH,
        INVESTING_TYPES,
        get_investing_type_path,
    )


class PromptLoader:
    """
    Cached loader for all prompt files used in the pipeline.

    All prompts are loaded lazily and cached after first access.
    """

    def __init__(self):
        self._cache: Dict[str, str] = {}

    def _load_file(self, path: Path, cache_key: str) -> str:
        """Load a file and cache its contents."""
        if cache_key not in self._cache:
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found: {path}")
            self._cache[cache_key] = path.read_text(encoding="utf-8")
        return self._cache[cache_key]

    @property
    def analyst_role(self) -> str:
        """Load the analyst role prompt."""
        return self._load_file(ANALYST_ROLE_PATH, "analyst_role")

    @property
    def rd_review_role(self) -> str:
        """Load the Research Director review role prompt."""
        return self._load_file(RD_REVIEW_ROLE_PATH, "rd_review_role")

    @property
    def rd_synthesis_role(self) -> str:
        """Load the Research Director synthesis role prompt."""
        return self._load_file(RD_SYNTHESIS_ROLE_PATH, "rd_synthesis_role")

    @property
    def memo_engine(self) -> str:
        """Load the buyside memo engine prompt."""
        return self._load_file(MEMO_ENGINE_PATH, "memo_engine")

    @property
    def human_readable_engine(self) -> str:
        """Load the human readable output engine prompt."""
        return self._load_file(HUMAN_READABLE_ENGINE_PATH, "human_readable_engine")

    @property
    def source_scout_agent(self) -> str:
        """Load the web research agent prompt."""
        return self._load_file(SOURCE_SCOUT_AGENT_PATH, "source_scout_agent")

    def investing_type(self, type_id: int) -> str:
        """
        Load an investing type prompt (1-6).

        Args:
            type_id: Investing type ID (1-6)

        Returns:
            The investing type prompt content

        Raises:
            ValueError: If type_id is not 1-6
        """
        if type_id not in INVESTING_TYPES:
            raise ValueError(f"Invalid investing type ID: {type_id}. Must be 1-6.")
        cache_key = f"investing_type_{type_id}"
        return self._load_file(get_investing_type_path(type_id), cache_key)

    def investing_type_name(self, type_id: int) -> str:
        """Get the human-readable name for an investing type."""
        if type_id not in INVESTING_TYPES:
            raise ValueError(f"Invalid investing type ID: {type_id}. Must be 1-6.")
        return INVESTING_TYPES[type_id]["name"]

    def investing_type_short_name(self, type_id: int) -> str:
        """Get the short name for an investing type (used in filenames)."""
        if type_id not in INVESTING_TYPES:
            raise ValueError(f"Invalid investing type ID: {type_id}. Must be 1-6.")
        return INVESTING_TYPES[type_id]["short_name"]

    def load_all(self) -> Dict[str, str]:
        """
        Pre-load all prompts into cache.

        Returns:
            Dict mapping prompt names to their content lengths (for verification)
        """
        prompts = {
            "analyst_role": self.analyst_role,
            "rd_review_role": self.rd_review_role,
            "rd_synthesis_role": self.rd_synthesis_role,
            "memo_engine": self.memo_engine,
            "human_readable_engine": self.human_readable_engine,
            "source_scout_agent": self.source_scout_agent,
        }

        # Load all investing types
        for type_id in range(1, 7):
            prompts[f"investing_type_{type_id}"] = self.investing_type(type_id)

        return {name: len(content) for name, content in prompts.items()}

    def clear_cache(self):
        """Clear the prompt cache."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about cached prompts."""
        return {
            "cached_prompts": len(self._cache),
            "total_chars": sum(len(v) for v in self._cache.values()),
        }


# Global singleton for convenience
_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get the global PromptLoader instance."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader
