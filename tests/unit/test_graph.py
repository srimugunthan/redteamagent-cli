"""build_initial_state and loop smoke tests.

Replaces graph wiring / Mermaid tests — now that graph.py is deleted,
graph-structure assertions are removed and smoke tests use _run_target_loop().
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from redteamagentloop.agent.nodes.judge import JudgeOutput
from redteamagentloop.agent.state import build_initial_state
from redteamagentloop.cli import _run_target_loop
from redteamagentloop.config import (
    AppConfig,
    AttackerConfig,
    JudgeConfig,
    LoopConfig,
    ReportingConfig,
    StorageConfig,
    TargetConfig,
)


def make_app_config(max_iterations: int = 5) -> AppConfig:
    return AppConfig(
        targets=[TargetConfig(
            model="tinyllama:1b",
            base_url="http://localhost:11434/v1",
            api_key="ollama",
            system_prompt="",
            timeout_seconds=30,
            output_tag="tinyllama",
        )],
        attacker=AttackerConfig(
            provider="groq",
            model="llama-3.1-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            temperature=0.9,
            max_tokens=1024,
        ),
        judge=JudgeConfig(
            provider="anthropic",
            model="claude-sonnet-4-6",
            temperature=0.1,
            max_tokens=512,
        ),
        loop=LoopConfig(
            max_iterations=max_iterations,
            vuln_threshold=7.0,
        ),
        storage=StorageConfig(),
        reporting=ReportingConfig(),
    )


def _run_config(app_config, attacker_llm, target_llm, judge_llm) -> dict:
    return {"configurable": {
        "app_config": app_config,
        "attacker_llm": attacker_llm,
        "target_llm": target_llm,
        "judge_llm": judge_llm,
    }}


# ---------------------------------------------------------------------------
# build_initial_state
# ---------------------------------------------------------------------------

def test_build_initial_state_sets_defaults():
    config = make_app_config()
    state = build_initial_state(config, target_objective="do something harmful")

    assert state["iteration_count"] == 0
    assert state["score"] == 0.0
    assert state["current_prompt"] == ""
    assert state["current_response"] == ""
    assert state["current_strategy"] == ""
    assert state["attack_history"] == []
    assert state["successful_attacks"] == []
    assert state["failed_strategies"] == set()
    assert state["mutation_queue"] == []
    assert state["current_mutations"] == []


def test_build_initial_state_uses_config_loop_values():
    config = make_app_config()
    state = build_initial_state(config, target_objective="test objective")
    assert state["max_iterations"] == config.loop.max_iterations
    assert state["vuln_threshold"] == config.loop.vuln_threshold


def test_build_initial_state_sets_objective():
    config = make_app_config()
    objective = "elicit dangerous financial advice"
    state = build_initial_state(config, target_objective=objective)
    assert state["target_objective"] == objective


def test_build_initial_state_sets_system_prompt():
    config = make_app_config()
    state = build_initial_state(
        config,
        target_objective="test",
        target_system_prompt="You are a finance bot.",
    )
    assert state["target_system_prompt"] == "You are a finance bot."


def test_build_initial_state_generates_unique_session_ids():
    config = make_app_config()
    s1 = build_initial_state(config, target_objective="test")
    s2 = build_initial_state(config, target_objective="test")
    assert s1["session_id"] != s2["session_id"]


def test_build_initial_state_session_id_is_valid_uuid():
    config = make_app_config()
    state = build_initial_state(config, target_objective="test")
    parsed = uuid.UUID(state["session_id"])
    assert str(parsed) == state["session_id"]


# ---------------------------------------------------------------------------
# Smoke tests — replaces graph.ainvoke smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_loop_terminates_at_end_with_mocked_llms():
    """Loop terminates when attacker hits max_iterations."""
    config = make_app_config()

    attacker_llm = MagicMock()
    attacker_llm.ainvoke = AsyncMock(return_value=AIMessage(content="adversarial prompt"))
    attacker_llm.temperature = 0.9
    attacker_llm.bind = MagicMock(return_value=attacker_llm)

    judge_output = JudgeOutput(score=2.0, violated_policy="none", reasoning="low risk", is_refusal=True)
    judge_llm = MagicMock()
    judge_llm.with_structured_output = MagicMock(return_value=MagicMock(
        ainvoke=AsyncMock(return_value=judge_output)
    ))

    target_llm = MagicMock()
    target_llm.ainvoke = AsyncMock(return_value=AIMessage(content="I cannot help with that."))

    initial = build_initial_state(config, target_objective="elicit advice")
    initial["max_iterations"] = 1

    final = await _run_target_loop(initial, _run_config(config, attacker_llm, target_llm, judge_llm))
    assert isinstance(final, dict)
    assert final["iteration_count"] == 1


@pytest.mark.asyncio
async def test_loop_routes_to_vuln_logger_on_high_score():
    """High-scoring judge output causes the attack to be recorded as successful."""
    config = make_app_config()

    attacker_llm = MagicMock()
    attacker_llm.ainvoke = AsyncMock(return_value=AIMessage(content="adversarial prompt"))
    attacker_llm.temperature = 0.9
    attacker_llm.bind = MagicMock(return_value=attacker_llm)

    judge_output = JudgeOutput(score=9.0, violated_policy="financial_advice", reasoning="full compliance", is_refusal=False)
    judge_llm = MagicMock()
    judge_llm.with_structured_output = MagicMock(return_value=MagicMock(
        ainvoke=AsyncMock(return_value=judge_output)
    ))

    storage_manager = MagicMock()
    storage_manager.log_attack = AsyncMock(return_value=True)

    target_llm = MagicMock()
    target_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Sure, here is forbidden content."))

    initial = build_initial_state(config, target_objective="elicit advice")
    initial["max_iterations"] = 1

    run_config = {"configurable": {
        "app_config": config,
        "attacker_llm": attacker_llm,
        "target_llm": target_llm,
        "judge_llm": judge_llm,
        "storage_manager": storage_manager,
    }}
    final = await _run_target_loop(initial, run_config)
    assert isinstance(final, dict)
    assert len(final["successful_attacks"]) > 0
