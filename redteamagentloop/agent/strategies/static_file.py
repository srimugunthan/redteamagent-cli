"""StaticFileStrategy — serve adversarial prompts from a JSONL file, no LLM call.

Expected JSONL schema (one record per line):
  {"strategy": "<name>", "prompt": "<text>", ...}

Extra fields (response, human_score, etc.) are ignored.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from redteamagentloop.agent.strategies.base import STRATEGY_REGISTRY, AttackStrategy, register_strategy

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from redteamagentloop.agent.state import RedTeamState


# ---------------------------------------------------------------------------
# PromptLibrary — loaded once, shared across the session
# ---------------------------------------------------------------------------

class PromptLibrary:
    """Indexes prompts from a JSONL file by strategy name and serves them round-robin."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._by_strategy: dict[str, list[str]] = {}
        self._indices: dict[str, int] = {}
        self._all: list[str] = []
        self._all_index: int = 0
        self._load(path)

    def _load(self, path: str) -> None:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                strategy = rec.get("strategy", "")
                prompt = rec.get("prompt", "")
                if not prompt:
                    continue
                self._all.append(prompt)
                self._by_strategy.setdefault(strategy, []).append(prompt)

    def next_for(self, strategy_name: str) -> str | None:
        """Return the next prompt for the given strategy, cycling round-robin.

        Returns None if no prompts exist for that strategy name.
        """
        prompts = self._by_strategy.get(strategy_name)
        if not prompts:
            return None
        idx = self._indices.get(strategy_name, 0)
        prompt = prompts[idx % len(prompts)]
        self._indices[strategy_name] = idx + 1
        return prompt

    def next_any(self) -> str | None:
        """Return the next prompt from the full library, cycling through all strategies."""
        if not self._all:
            return None
        prompt = self._all[self._all_index % len(self._all)]
        self._all_index += 1
        return prompt

    def strategies(self) -> list[str]:
        """Return the strategy names present in the file."""
        return sorted(self._by_strategy.keys())

    def count_for(self, strategy_name: str) -> int:
        return len(self._by_strategy.get(strategy_name, []))

    def __repr__(self) -> str:
        counts = {s: len(p) for s, p in self._by_strategy.items()}
        return f"PromptLibrary(path={self.path!r}, strategies={counts})"


# ---------------------------------------------------------------------------
# Module-level singleton — set via configure(), read via get_library()
# ---------------------------------------------------------------------------

_library: PromptLibrary | None = None


def configure(path: str) -> PromptLibrary:
    """Load (or reload) the prompt library from path. Returns the library."""
    global _library
    resolved = str(Path(path).resolve())
    _library = PromptLibrary(resolved)
    return _library


def get_library() -> PromptLibrary | None:
    return _library


# ---------------------------------------------------------------------------
# StaticFileStrategy — registered strategy, uses the library directly
# ---------------------------------------------------------------------------

@register_strategy
class StaticFileStrategy(AttackStrategy):
    """Serves prompts from a pre-loaded JSONL file.  No LLM call is made.

    Cycles through all prompts in the file in order (wrapping around).
    Requires a prompt file to be configured:
      - attacker.prompt_file in config.yaml, or
      - --prompt-file on the CLI.
    """

    name = "StaticFile"
    description = (
        "Serves adversarial prompts from a pre-loaded JSONL file, "
        "cycling through them in order. No LLM call is made."
    )
    risk_level = "medium"

    async def generate_prompt(
        self,
        state: "RedTeamState",
        attacker_llm: "BaseChatModel",
    ) -> str:
        lib = get_library()
        if lib is None:
            raise RuntimeError(
                "StaticFileStrategy requires a prompt file. "
                "Set attacker.prompt_file in config.yaml or pass --prompt-file."
            )
        prompt = lib.next_any()
        if not prompt:
            raise RuntimeError("StaticFileStrategy: prompt library is empty.")
        return prompt
