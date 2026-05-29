"""Multi-turn attack package — factory entry point."""

from __future__ import annotations

from .base import ORCHESTRATOR_REGISTRY, PromptSource, single_exchange
from .crescendo import CrescendoOrchestrator, CrescendoScriptLibrary
from .mcts import MCTSOrchestrator
from .prompt_sources import (
    DynamicCrescendoSource,
    DynamicMCTSSource,
    DynamicReactiveSource,
    StaticCrescendoSource,
    StaticMCTSSource,
    StaticSequenceSource,
)
from .reactive_chain import ReactiveChainOrchestrator


def build_orchestrator_and_source(multi_turn_cfg, app_config, attacker_llm=None):
    mode = multi_turn_cfg.mode
    max_turns = multi_turn_cfg.max_turns_per_episode
    prompt_file = getattr(getattr(app_config, "attacker", None), "prompt_file", None)

    if mode == "reactive_chain":
        orchestrator = ReactiveChainOrchestrator(max_turns=max_turns)
        if prompt_file:
            from redteamagentloop.agent.strategies.static_file import configure
            source = StaticSequenceSource(library=configure(prompt_file))
        else:
            source = DynamicReactiveSource()
        return orchestrator, source

    if mode == "crescendo":
        orchestrator = CrescendoOrchestrator(max_turns=max_turns)
        script_file = multi_turn_cfg.crescendo_script_file
        if script_file:
            lib = CrescendoScriptLibrary(script_file)
            source = StaticCrescendoSource(scripts=lib.all_scripts())
        else:
            source = DynamicCrescendoSource(max_turns=max_turns)
        return orchestrator, source

    if mode == "mcts":
        orchestrator = MCTSOrchestrator(
            simulations=multi_turn_cfg.mcts_simulations,
            branching_factor=multi_turn_cfg.mcts_branching_factor,
            C=multi_turn_cfg.mcts_exploration_constant,
            rollout_depth=multi_turn_cfg.mcts_rollout_depth,
            max_turns=max_turns,
        )
        if prompt_file:
            from redteamagentloop.agent.strategies.static_file import configure
            source = StaticMCTSSource(
                library=configure(prompt_file),
                branching_factor=multi_turn_cfg.mcts_branching_factor,
            )
        else:
            source = DynamicMCTSSource()
        return orchestrator, source

    raise ValueError(
        f"Unknown multi-turn mode: {mode!r}. Available: reactive_chain, crescendo, mcts"
    )
