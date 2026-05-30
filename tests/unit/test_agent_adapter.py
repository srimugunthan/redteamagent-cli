"""Unit tests for AgentTargetAdapter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from redteamagentloop.config import TargetConfig
from redteamagentloop.llm_factory import AgentTargetAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENT_RESPONSE_JSON = json.dumps({
    "output": "Transaction T-9921 is low risk.",
    "tool_calls": [
        {"tool": "database_lookup", "args": {"id": "T-9921"}, "response": {"flagged": False}},
        {"tool": "risk_scorer",     "args": {"id": "T-9921"}, "response": {"score": 0.1}},
    ],
    "memory_reads": [{"entry": "T-9921 was approved.", "score": 0.94}],
    "reasoning_steps": ["Retrieved record.", "Score is low."],
    "agent_trace": [
        {"step": 1, "node": "planner", "input": "query", "output": "plan", "latency_ms": 100},
    ],
    "raw": {},
})


def make_target(reset: bool = True) -> TargetConfig:
    return TargetConfig(
        target_type="agent",
        endpoint_url="http://localhost:9000/invoke",
        allowed_tools=["database_lookup", "risk_scorer"],
        reset_between_iterations=reset,
        timeout_seconds=30,
        output_tag="test-agent",
    )


def make_messages(prompt: str = "What is the risk of T-9921?") -> list:
    return [HumanMessage(content=prompt)]


def _mock_async_client(response_text: str = _AGENT_RESPONSE_JSON,
                       status_code: int = 200) -> MagicMock:
    """Return a MagicMock that behaves like an httpx.AsyncClient context manager."""
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_response.status_code = status_code
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

def test_constructor_parses_root_from_endpoint():
    adapter = AgentTargetAdapter(make_target())
    assert adapter._invoke_url == "http://localhost:9000/invoke"
    assert adapter._root == "http://localhost:9000"


def test_constructor_respects_reset_flag():
    assert AgentTargetAdapter(make_target(reset=True))._reset_between is True
    assert AgentTargetAdapter(make_target(reset=False))._reset_between is False


def test_constructor_stores_timeout():
    adapter = AgentTargetAdapter(make_target())
    assert adapter._timeout == 30


# ---------------------------------------------------------------------------
# ainvoke — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ainvoke_returns_aimessage_with_response_body():
    adapter = AgentTargetAdapter(make_target())
    mock_client = _mock_async_client()

    with patch("redteamagentloop.llm_factory.httpx.AsyncClient", return_value=mock_client):
        result = await adapter.ainvoke(make_messages("What is the risk of T-9921?"))

    assert isinstance(result, AIMessage)
    assert result.content == _AGENT_RESPONSE_JSON


@pytest.mark.asyncio
async def test_ainvoke_sends_prompt_in_turns_field():
    adapter = AgentTargetAdapter(make_target())
    mock_client = _mock_async_client()
    captured = {}

    async def capture_post(url, **kwargs):
        captured["body"] = json.loads(kwargs.get("content", "{}"))
        mock_response = MagicMock()
        mock_response.text = _AGENT_RESPONSE_JSON
        mock_response.raise_for_status = MagicMock()
        return mock_response

    mock_client.post = capture_post

    with patch("redteamagentloop.llm_factory.httpx.AsyncClient", return_value=mock_client):
        await adapter.ainvoke(make_messages("attack prompt"))

    assert captured["body"]["turns"] == ["attack prompt"]
    assert "expected_behavior" in captured["body"]
    assert "metadata" in captured["body"]


@pytest.mark.asyncio
async def test_ainvoke_uses_last_human_message_as_prompt():
    adapter = AgentTargetAdapter(make_target())
    mock_client = _mock_async_client()
    captured = {}

    async def capture_post(url, **kwargs):
        captured["body"] = json.loads(kwargs.get("content", "{}"))
        r = MagicMock()
        r.text = _AGENT_RESPONSE_JSON
        r.raise_for_status = MagicMock()
        return r

    mock_client.post = capture_post

    messages = [
        SystemMessage(content="You are an attacker."),
        HumanMessage(content="first turn"),
        HumanMessage(content="last turn"),
    ]
    with patch("redteamagentloop.llm_factory.httpx.AsyncClient", return_value=mock_client):
        await adapter.ainvoke(messages)

    assert captured["body"]["turns"] == ["last turn"]


# ---------------------------------------------------------------------------
# Reset behaviour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_called_before_invoke_when_enabled():
    adapter = AgentTargetAdapter(make_target(reset=True))
    mock_client = _mock_async_client()
    call_urls = []

    async def record_post(url, **kwargs):
        call_urls.append(url)
        r = MagicMock()
        r.text = _AGENT_RESPONSE_JSON
        r.raise_for_status = MagicMock()
        return r

    mock_client.post = record_post

    with patch("redteamagentloop.llm_factory.httpx.AsyncClient", return_value=mock_client):
        await adapter.ainvoke(make_messages())

    assert any("reset" in url for url in call_urls), f"No /reset call found in: {call_urls}"
    assert any("invoke" in url for url in call_urls), f"No /invoke call found in: {call_urls}"
    reset_idx  = next(i for i, u in enumerate(call_urls) if "reset" in u)
    invoke_idx = next(i for i, u in enumerate(call_urls) if "invoke" in u)
    assert reset_idx < invoke_idx, "/reset must be called before /invoke"


@pytest.mark.asyncio
async def test_reset_skipped_when_disabled():
    adapter = AgentTargetAdapter(make_target(reset=False))
    mock_client = _mock_async_client()
    call_urls = []

    async def record_post(url, **kwargs):
        call_urls.append(url)
        r = MagicMock()
        r.text = _AGENT_RESPONSE_JSON
        r.raise_for_status = MagicMock()
        return r

    mock_client.post = record_post

    with patch("redteamagentloop.llm_factory.httpx.AsyncClient", return_value=mock_client):
        await adapter.ainvoke(make_messages())

    assert not any("reset" in url for url in call_urls), "reset should not be called"
    assert any("invoke" in url for url in call_urls)


@pytest.mark.asyncio
async def test_reset_failure_does_not_abort_invoke():
    """A failing /reset call is silently ignored; /invoke still runs."""
    adapter = AgentTargetAdapter(make_target(reset=True))
    mock_client = _mock_async_client()
    call_urls = []

    async def fail_reset_succeed_invoke(url, **kwargs):
        call_urls.append(url)
        if "reset" in url:
            raise httpx.HTTPError("reset endpoint not found")
        r = MagicMock()
        r.text = _AGENT_RESPONSE_JSON
        r.raise_for_status = MagicMock()
        return r

    mock_client.post = fail_reset_succeed_invoke

    with patch("redteamagentloop.llm_factory.httpx.AsyncClient", return_value=mock_client):
        result = await adapter.ainvoke(make_messages())

    assert isinstance(result, AIMessage)
    assert any("invoke" in url for url in call_urls)


# ---------------------------------------------------------------------------
# HTTP errors from /invoke propagate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invoke_http_error_propagates():
    adapter = AgentTargetAdapter(make_target(reset=False))
    mock_client = _mock_async_client()

    async def raise_http_error(url, **kwargs):
        if "invoke" in url:
            raise httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        r = MagicMock()
        r.text = _AGENT_RESPONSE_JSON
        r.raise_for_status = MagicMock()
        return r

    mock_client.post = raise_http_error

    with patch("redteamagentloop.llm_factory.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.ainvoke(make_messages())


# ---------------------------------------------------------------------------
# build_target_llm routing
# ---------------------------------------------------------------------------

def test_build_target_llm_returns_agent_adapter_for_agent_type():
    from redteamagentloop.llm_factory import build_target_llm
    target = make_target()
    adapter = build_target_llm(target)
    assert isinstance(adapter, AgentTargetAdapter)
