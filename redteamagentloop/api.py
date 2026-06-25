"""Public API for redteamagentloop.

Single-turn usage::

    from redteamagentloop.api import (
        attacker_node, target_caller_node, judge_node,
        loop_controller_node, route_after_judge,
        build_state, build_run_config, merge,
    )

    state  = build_state(objective="Test for PII leakage", system_prompt="...")
    config = build_run_config(attacker_llm=..., target_llm=..., judge_llm=...)

    while True:
        merge(state, await attacker_node(state, config))
        merge(state, await target_caller_node(state, config))
        merge(state, await judge_node(state, config))
        merge(state, await loop_controller_node(state, config))
        if route_after_judge(state) == "END":
            break

Custom target (replace target_caller_node with your own callable)::

    class MyTarget:
        async def ainvoke(self, messages):
            prompt = messages[-1].content
            response = await my_system.query(prompt)
            from langchain_core.messages import AIMessage
            return AIMessage(content=response)

    config = build_run_config(target_llm=MyTarget(), attacker_llm=..., judge_llm=...)

Custom judge (replace judge_node with a regex-based scorer, no LLM needed)::

    import re

    async def regex_judge(state, config):
        if re.search(r"buy.*stock", state["current_response"], re.I):
            return {"score": 9.0, "score_rationale": "direct buy instruction"}
        return {"score": 1.0, "score_rationale": "compliant"}

Multi-turn usage::

    from redteamagentloop.api import (
        ReactiveChainOrchestrator, DynamicReactiveSource,
        single_exchange, EpisodeResult, PromptSource,
        build_state, build_run_config,
    )

    orchestrator = ReactiveChainOrchestrator(max_turns=5)
    source = DynamicReactiveSource()
    results = await orchestrator.run_all_episodes(
        exchange_fn=single_exchange,
        base_state=base_state,
        run_config=run_config,
        prompt_source=source,
        max_episodes=3,
    )

Note:
    attacker_node shares a module-level strategy rotation counter across all runs
    in the same process. For parallel campaigns start a separate process per run.
"""

# --- Single-turn nodes ---
from redteamagentloop.agent.nodes.attacker        import attacker_node
from redteamagentloop.agent.nodes.target_caller   import target_caller_node
from redteamagentloop.agent.nodes.judge           import judge_node
from redteamagentloop.agent.nodes.loop_controller import loop_controller_node, route_after_judge
from redteamagentloop.agent.nodes.vuln_logger     import vuln_logger_node
from redteamagentloop.agent.nodes.mutation_engine import mutation_engine_node

# --- State helpers ---
from redteamagentloop.agent.state import build_state, build_initial_state, merge

# --- Run-config + LLM factories ---
from redteamagentloop.llm_factory import (
    build_run_config,
    build_attacker_llm,
    build_judge_llm,
    build_target_llm,
)

# --- Multi-turn orchestrators ---
from redteamagentloop.agent.multi_turn.reactive_chain import ReactiveChainOrchestrator
from redteamagentloop.agent.multi_turn.crescendo      import CrescendoOrchestrator
from redteamagentloop.agent.multi_turn.mcts           import MCTSOrchestrator

# --- Multi-turn prompt sources ---
from redteamagentloop.agent.multi_turn.prompt_sources import (
    DynamicReactiveSource,
    DynamicCrescendoSource,
    DynamicMCTSSource,
    StaticSequenceSource,
    StaticCrescendoSource,
    StaticMCTSSource,
)

# --- Multi-turn base types + exchange helper ---
from redteamagentloop.agent.multi_turn.base import (
    single_exchange,
    EpisodeResult,
    PromptSource,
)

# --- Multi-turn factory (requires MultiTurnConfig + AppConfig) ---
from redteamagentloop.agent.multi_turn import build_orchestrator_and_source

__all__ = [
    # single-turn nodes
    "attacker_node",
    "target_caller_node",
    "judge_node",
    "loop_controller_node",
    "route_after_judge",
    "vuln_logger_node",
    "mutation_engine_node",
    # state
    "build_state",
    "build_initial_state",
    "merge",
    # config + LLM factories
    "build_run_config",
    "build_attacker_llm",
    "build_judge_llm",
    "build_target_llm",
    # multi-turn orchestrators
    "ReactiveChainOrchestrator",
    "CrescendoOrchestrator",
    "MCTSOrchestrator",
    # multi-turn prompt sources
    "DynamicReactiveSource",
    "DynamicCrescendoSource",
    "DynamicMCTSSource",
    "StaticSequenceSource",
    "StaticCrescendoSource",
    "StaticMCTSSource",
    # multi-turn base
    "single_exchange",
    "EpisodeResult",
    "PromptSource",
    # multi-turn factory
    "build_orchestrator_and_source",
]
