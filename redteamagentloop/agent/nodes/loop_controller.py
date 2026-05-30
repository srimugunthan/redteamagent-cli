"""Loop controller node and routing function."""

from __future__ import annotations

from datetime import datetime, timezone

from redteamagentloop.agent.state import AttackRecord, RedTeamState
from redteamagentloop.logger import get_session_logger


def route_after_judge(state: RedTeamState) -> str:
    """Conditional edge function — returns the name of the next node."""
    if state["score"] >= state["vuln_threshold"]:
        return "vuln_logger"
    if len(state["mutation_queue"]) > 0:
        return "attacker"
    return "mutation_engine"


async def loop_controller_node(state: RedTeamState, config: dict) -> dict:
    """Records every completed attempt to attack_history, then routing happens via route_after_judge."""
    if not state.get("current_prompt"):
        return {}

    session_id = state["session_id"]
    log = get_session_logger(session_id)

    record: AttackRecord = {
        "session_id": session_id,
        "iteration": state["iteration_count"],
        "episode": 0,
        "strategy": state["current_strategy"],
        "prompt": state["current_prompt"],
        "response": state["current_response"],
        "score": state["score"],
        "score_rationale": state["score_rationale"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "was_successful": state["score"] >= state["vuln_threshold"],
        "mutation_depth": len(state.get("current_mutations", [])),
    }

    log.debug(
        f"iteration {state['iteration_count']} complete: "
        f"strategy={state['current_strategy']} score={state['score']:.1f} "
        f"route={route_after_judge(state)}",
        extra={"node": "loop_controller", "iteration": state["iteration_count"],
               "session_id": session_id},
    )

    updates: dict = {"attack_history": [record]}

    cfg = config.get("configurable", {})
    app_config = cfg.get("app_config")
    loop_cfg = app_config.loop if app_config else None

    if (
        loop_cfg
        and loop_cfg.strategy_rotation
        and state.get("strategy_mutation_count", 0) >= loop_cfg.max_mutations_per_strategy
    ):
        log.warning(
            f"strategy '{state['current_strategy']}' exhausted "
            f"({state.get('strategy_mutation_count', 0)} mutation cycles) — rotating",
            extra={"node": "loop_controller", "iteration": state["iteration_count"],
                   "session_id": session_id},
        )
        updates["failed_strategies"] = {state["current_strategy"]}

    return updates
