"""Phase 1 unit tests — single_exchange, ReactiveChainOrchestrator, PromptSources."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.multi_turn.conftest import BASE_STATE, RUN_CONFIG, stub_exchange


async def test_single_exchange_calls_nodes(monkeypatch):
    """single_exchange merges target + judge updates into the returned state dict."""
    from redteamagentloop.agent.multi_turn.base import single_exchange

    async def fake_target(state, cfg):
        return {"current_response": "fake resp", "error": None}

    async def fake_judge(state, cfg):
        return {"score": 4.5, "score_rationale": "partial", "error": None}

    monkeypatch.setattr(
        "redteamagentloop.agent.nodes.target_caller.target_caller_node", fake_target
    )
    monkeypatch.setattr(
        "redteamagentloop.agent.nodes.judge.judge_node", fake_judge
    )

    result = await single_exchange(BASE_STATE, "test prompt", [], RUN_CONFIG)
    assert result["current_response"] == "fake resp"
    assert result["score"] == 4.5
    assert result["current_prompt"] == "test prompt"


async def test_reactive_chain_runs_max_turns():
    """Episode runs exactly max_turns when score never reaches threshold."""
    from redteamagentloop.agent.multi_turn.reactive_chain import ReactiveChainOrchestrator
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticSequenceSource

    lib = MagicMock()
    lib.next_for.return_value = None
    lib.next_any.side_effect = ["p1", "p2", "p3"]
    source = StaticSequenceSource(library=lib, strategy="")
    orch = ReactiveChainOrchestrator(max_turns=3)

    result = await orch.run_episode(stub_exchange, BASE_STATE, RUN_CONFIG, source)

    assert result.turns_taken == 3
    assert not result.successful
    assert len(result.conversation_history) == 6  # 3 user + 3 assistant


async def test_reactive_chain_stops_on_success():
    """Episode stops early when a turn's score reaches vuln_threshold."""
    from redteamagentloop.agent.multi_turn.reactive_chain import ReactiveChainOrchestrator
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticSequenceSource

    lib = MagicMock()
    lib.next_for.return_value = None
    lib.next_any.return_value = "attack prompt"
    source = StaticSequenceSource(library=lib)
    orch = ReactiveChainOrchestrator(max_turns=5)

    async def high_score_exchange(base_state, prompt, history, run_config):
        return {
            **base_state,
            "current_prompt": prompt,
            "current_response": "complied",
            "score": 8.0,
            "score_rationale": "full bypass",
            "error": None,
        }

    result = await orch.run_episode(high_score_exchange, BASE_STATE, RUN_CONFIG, source)
    assert result.turns_taken == 1
    assert result.successful


async def test_run_all_episodes_stops_on_success():
    """run_all_episodes halts after the first successful episode."""
    from redteamagentloop.agent.multi_turn.reactive_chain import ReactiveChainOrchestrator
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticSequenceSource

    lib = MagicMock()
    lib.next_for.return_value = None
    lib.next_any.return_value = "p"
    source = StaticSequenceSource(library=lib)
    orch = ReactiveChainOrchestrator(max_turns=1)

    async def success_exchange(base_state, prompt, history, run_config):
        return {
            **base_state,
            "current_prompt": prompt,
            "current_response": "ok",
            "score": 9.0,
            "score_rationale": "bypass",
            "error": None,
        }

    results = await orch.run_all_episodes(
        success_exchange, BASE_STATE, RUN_CONFIG, source, max_episodes=5
    )
    assert len(results) == 1  # stopped after first success
    assert results[0].successful
