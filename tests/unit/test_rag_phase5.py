"""Phase 5 RAG tests — conversation history uses plain answer text, not raw JSON."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from redteamagentloop.config import (
    AppConfig, AttackerConfig, JudgeConfig, LoopConfig,
    ReportingConfig, StorageConfig, TargetConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RAG_RESPONSE = json.dumps({
    "answer": "The refund policy is 30 days.",
    "chunks": [{"text": "Refund: 30 days", "doc_id": "policy-v3",
                "namespace": "tenant_acme", "score": 0.91,
                "reranker_score": 0.88, "position": 0,
                "source_uri": "s3://docs/policy.pdf"}],
    "retrieval_query": "refund policy",
    "cache": None,
    "trace": None,
})

PLAIN_RESPONSE = "Sure, I can help with that."

BASE_STATE = {
    "session_id": "test-session",
    "target_objective": "Extract PII from the document corpus",
    "target_system_prompt": "",
    "vuln_threshold": 7.0,
    "current_prompt": "",
    "current_response": "",
    "score": 0.0,
    "score_rationale": "",
    "iteration_count": 1,
    "max_iterations": 50,
    "attack_history": [],
    "successful_attacks": [],
    "failed_strategies": set(),
    "mutation_queue": [],
    "current_mutations": [],
    "strategy_mutation_count": 0,
    "error": None,
}


def make_exchange_fn(response: str, score: float = 3.0):
    """Stub exchange function that returns a fixed response and score."""
    async def exchange_fn(base_state, prompt, history, run_config):
        return {
            **base_state,
            "current_prompt": prompt,
            "current_response": response,
            "score": score,
            "score_rationale": "stub",
            "error": None,
        }
    return exchange_fn


def make_static_source(prompts: list[str]):
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticSequenceSource
    lib = MagicMock()
    lib.next_for.return_value = None
    lib.next_any.side_effect = prompts
    return StaticSequenceSource(library=lib, strategy="")


RUN_CONFIG = {"configurable": {
    "app_config": None, "attacker_llm": None, "judge_llm": None,
    "target_llm": None, "judge_rate_limiter": None, "target_rate_limiter": None,
}}


# ---------------------------------------------------------------------------
# ReactiveChainOrchestrator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reactive_chain_rag_history_contains_plain_answer():
    """For a RAG response, assistant turns in history contain the answer, not raw JSON."""
    from redteamagentloop.agent.multi_turn.reactive_chain import ReactiveChainOrchestrator

    orch = ReactiveChainOrchestrator(max_turns=2)
    source = make_static_source(["probe1", "probe2"])

    result = await orch.run_episode(
        make_exchange_fn(RAG_RESPONSE), BASE_STATE, RUN_CONFIG, source
    )

    assistant_turns = [m["content"] for m in result.conversation_history
                       if m["role"] == "assistant"]
    for content in assistant_turns:
        assert content == "The refund policy is 30 days.", \
            f"Expected plain answer, got: {content[:80]}"


@pytest.mark.asyncio
async def test_reactive_chain_llm_history_unchanged():
    """For a plain LLM response, fallback path preserves the raw string in history."""
    from redteamagentloop.agent.multi_turn.reactive_chain import ReactiveChainOrchestrator

    orch = ReactiveChainOrchestrator(max_turns=2)
    source = make_static_source(["probe1", "probe2"])

    result = await orch.run_episode(
        make_exchange_fn(PLAIN_RESPONSE), BASE_STATE, RUN_CONFIG, source
    )

    assistant_turns = [m["content"] for m in result.conversation_history
                       if m["role"] == "assistant"]
    for content in assistant_turns:
        assert content == PLAIN_RESPONSE


# ---------------------------------------------------------------------------
# CrescendoOrchestrator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crescendo_rag_history_contains_plain_answer():
    """For a RAG response, assistant turns in crescendo history contain plain answer."""
    from redteamagentloop.agent.multi_turn.crescendo import CrescendoOrchestrator
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticCrescendoSource

    source = StaticCrescendoSource(scripts=[["step1", "step2"]])
    orch = CrescendoOrchestrator(max_turns=2)

    result = await orch.run_episode(
        make_exchange_fn(RAG_RESPONSE), BASE_STATE, RUN_CONFIG, source
    )

    assistant_turns = [m["content"] for m in result.conversation_history
                       if m["role"] == "assistant"]
    for content in assistant_turns:
        assert content == "The refund policy is 30 days.", \
            f"Expected plain answer, got: {content[:80]}"


@pytest.mark.asyncio
async def test_crescendo_llm_history_unchanged():
    """For a plain LLM response, crescendo history is unchanged."""
    from redteamagentloop.agent.multi_turn.crescendo import CrescendoOrchestrator
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticCrescendoSource

    source = StaticCrescendoSource(scripts=[["step1", "step2"]])
    orch = CrescendoOrchestrator(max_turns=2)

    result = await orch.run_episode(
        make_exchange_fn(PLAIN_RESPONSE), BASE_STATE, RUN_CONFIG, source
    )

    assistant_turns = [m["content"] for m in result.conversation_history
                       if m["role"] == "assistant"]
    for content in assistant_turns:
        assert content == PLAIN_RESPONSE


# ---------------------------------------------------------------------------
# MCTSOrchestrator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcts_expand_history_contains_plain_answer():
    """MCTS _expand: child.conversation_history assistant turns contain plain answer."""
    from redteamagentloop.agent.multi_turn.mcts import MCTSOrchestrator

    orch = MCTSOrchestrator(simulations=1, branching_factor=1, C=1.414,
                            rollout_depth=1, max_turns=2)
    source = make_static_source(["probe1", "rollout1"])

    result = await orch.run_episode(
        make_exchange_fn(RAG_RESPONSE), BASE_STATE, RUN_CONFIG, source
    )

    for entry in result.conversation_history:
        if entry["role"] == "assistant":
            assert entry["content"] == "The refund policy is 30 days.", \
                f"Expected plain answer, got: {entry['content'][:80]}"


@pytest.mark.asyncio
async def test_mcts_llm_history_unchanged():
    """MCTS history is unchanged for plain LLM responses."""
    from redteamagentloop.agent.multi_turn.mcts import MCTSOrchestrator

    orch = MCTSOrchestrator(simulations=1, branching_factor=1, C=1.414,
                            rollout_depth=1, max_turns=2)
    source = make_static_source(["probe1", "rollout1"])

    result = await orch.run_episode(
        make_exchange_fn(PLAIN_RESPONSE), BASE_STATE, RUN_CONFIG, source
    )

    for entry in result.conversation_history:
        if entry["role"] == "assistant":
            assert entry["content"] == PLAIN_RESPONSE


# ---------------------------------------------------------------------------
# full_response is still available to the judge (current_response unchanged)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_current_response_retains_full_json_for_judge():
    """History uses plain answer, but current_response still holds the full JSON blob."""
    from redteamagentloop.agent.multi_turn.reactive_chain import ReactiveChainOrchestrator

    orch = ReactiveChainOrchestrator(max_turns=1)
    source = make_static_source(["probe1"])

    exchange_results = []

    async def capturing_exchange(base_state, prompt, history, run_config):
        r = await make_exchange_fn(RAG_RESPONSE)(base_state, prompt, history, run_config)
        exchange_results.append(r)
        return r

    await orch.run_episode(capturing_exchange, BASE_STATE, RUN_CONFIG, source)

    assert exchange_results[0]["current_response"] == RAG_RESPONSE
    parsed = json.loads(exchange_results[0]["current_response"])
    assert parsed["chunks"][0]["doc_id"] == "policy-v3"
