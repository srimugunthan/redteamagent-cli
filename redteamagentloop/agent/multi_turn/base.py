"""Multi-turn attack infrastructure — shared ABCs, registry, and single_exchange helper."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from redteamagentloop.agent.state import AttackRecord

ORCHESTRATOR_REGISTRY: dict[str, type["MultiTurnOrchestrator"]] = {}


def register_orchestrator(cls: type) -> type:
    ORCHESTRATOR_REGISTRY[cls.name] = cls
    return cls


@dataclass
class EpisodeResult:
    attack_records: list[AttackRecord]
    conversation_history: list[dict]
    best_score: float
    successful: bool
    turns_taken: int


class PromptSource(ABC):
    @abstractmethod
    async def next_prompt(
        self,
        turn: int,
        conversation_history: list[dict],
        objective: str,
        last_score: float,
        last_rationale: str,
        attacker_llm,
    ) -> str: ...


class MultiTurnOrchestrator(ABC):
    name: str

    @abstractmethod
    async def run_episode(
        self,
        exchange_fn,
        base_state: dict,
        run_config: dict,
        prompt_source: PromptSource,
    ) -> EpisodeResult: ...

    async def run_all_episodes(
        self,
        exchange_fn,
        base_state: dict,
        run_config: dict,
        prompt_source: PromptSource,
        max_episodes: int,
    ) -> list[EpisodeResult]:
        results = []
        for _ in range(max_episodes):
            result = await self.run_episode(exchange_fn, base_state, run_config, prompt_source)
            results.append(result)
            if result.successful:
                break
        return results


async def single_exchange(
    base_state: dict,
    prompt: str,
    conversation_history: list[dict],
    run_config: dict,
) -> dict:
    """Call target_caller then judge for one prompt. Used by all orchestrators."""
    from redteamagentloop.agent.nodes.target_caller import target_caller_node

    cfg = run_config.get("configurable", {})
    app_config = cfg.get("app_config")
    target_type = getattr(getattr(app_config, "targets", [None])[0], "target_type", "llm")

    if target_type == "rag":
        from redteamagentloop.agent.nodes.rag_judge import rag_judge_node as judge_fn
    else:
        from redteamagentloop.agent.nodes.judge import judge_node as judge_fn

    state = {**base_state, "current_prompt": prompt, "conversation_history": conversation_history}
    state = {**state, **(await target_caller_node(state, run_config))}
    state = {**state, **(await judge_fn(state, run_config))}
    return state
