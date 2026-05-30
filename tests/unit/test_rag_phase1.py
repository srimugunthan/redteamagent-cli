"""Phase 1 RAG tests — HttpTargetAdapter and build_target_llm() dispatch."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from redteamagentloop.config import TargetConfig
from redteamagentloop.llm_factory import HttpTargetAdapter, build_target_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_rag_target(**kwargs) -> TargetConfig:
    defaults = dict(
        target_type="rag",
        endpoint_url="http://localhost:8000/query",
        output_tag="test-rag",
    )
    return TargetConfig(**{**defaults, **kwargs})


def make_llm_target(**kwargs) -> TargetConfig:
    defaults = dict(
        target_type="llm",
        model="tinyllama",
        base_url="http://localhost:11434/v1",
        output_tag="test-llm",
    )
    return TargetConfig(**{**defaults, **kwargs})


def mock_httpx_client(response_json: dict) -> MagicMock:
    """Return a mock httpx.AsyncClient that responds with response_json."""
    mock_r = MagicMock()
    mock_r.json.return_value = response_json
    mock_r.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_r)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


# ---------------------------------------------------------------------------
# build_target_llm() dispatch
# ---------------------------------------------------------------------------

def test_build_target_llm_returns_adapter_for_rag():
    target = make_rag_target()
    result = build_target_llm(target)
    assert isinstance(result, HttpTargetAdapter)


def test_build_target_llm_returns_chat_openai_for_llm():
    from langchain_openai import ChatOpenAI
    target = make_llm_target()
    result = build_target_llm(target)
    assert isinstance(result, ChatOpenAI)


def test_build_target_llm_defaults_to_llm_when_target_type_absent():
    """TargetConfig with no target_type (defaults to 'llm') returns ChatOpenAI."""
    from langchain_openai import ChatOpenAI
    target = make_llm_target()
    assert target.target_type == "llm"
    result = build_target_llm(target)
    assert isinstance(result, ChatOpenAI)


# ---------------------------------------------------------------------------
# HttpTargetAdapter.ainvoke() — full schema response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adapter_ainvoke_full_schema(monkeypatch):
    """Adapter normalises a full RAG response with all optional fields present."""
    full_response = {
        "answer": "The refund policy is 30 days.",
        "chunks": [
            {
                "text": "Refund policy: 30 days from purchase.",
                "doc_id": "doc_policy_v3",
                "namespace": "tenant_acme",
                "score": 0.92,
                "reranker_score": 0.87,
                "position": 0,
                "source_uri": "s3://docs/policy.pdf",
            }
        ],
        "retrieval_query": "refund policy duration",
        "cache": {"hit": False, "key": "sha256:abc", "age_seconds": None},
        "trace": {
            "assembled_prompt": "System: ...\nUser: what is the refund policy?",
            "reasoning_steps": ["Chunk 1 is relevant."],
            "tool_calls": [],
            "rewrite_steps": ["refund policy duration"],
        },
        "debug": {},
    }

    monkeypatch.setattr("httpx.AsyncClient", lambda **_: mock_httpx_client(full_response))

    adapter = HttpTargetAdapter(make_rag_target())
    result = await adapter.ainvoke([HumanMessage(content="what is the refund policy?")])

    parsed = json.loads(result.content)
    assert parsed["answer"] == "The refund policy is 30 days."
    assert len(parsed["chunks"]) == 1
    chunk = parsed["chunks"][0]
    assert chunk["text"] == "Refund policy: 30 days from purchase."
    assert chunk["doc_id"] == "doc_policy_v3"
    assert chunk["namespace"] == "tenant_acme"
    assert chunk["score"] == 0.92
    assert chunk["reranker_score"] == 0.87
    assert chunk["position"] == 0
    assert chunk["source_uri"] == "s3://docs/policy.pdf"
    assert parsed["retrieval_query"] == "refund policy duration"
    assert parsed["cache"]["hit"] is False
    assert parsed["trace"]["assembled_prompt"].startswith("System:")


@pytest.mark.asyncio
async def test_adapter_ainvoke_optional_fields_absent_are_null(monkeypatch):
    """When optional fields are missing, they appear as null in normalised output."""
    minimal_response = {
        "answer": "42.",
        "chunks": [],
    }

    monkeypatch.setattr("httpx.AsyncClient", lambda **_: mock_httpx_client(minimal_response))

    adapter = HttpTargetAdapter(make_rag_target())
    result = await adapter.ainvoke([HumanMessage(content="what is the answer?")])

    parsed = json.loads(result.content)
    assert parsed["answer"] == "42."
    assert parsed["chunks"] == []
    assert parsed["retrieval_query"] is None
    assert parsed["cache"] is None
    assert parsed["trace"] is None
    assert parsed["debug"] is None


@pytest.mark.asyncio
async def test_adapter_ainvoke_plain_string_chunks_are_normalised(monkeypatch):
    """Chunks that are plain strings are wrapped into {'text': ...} dicts."""
    response = {
        "answer": "Some answer.",
        "chunks": ["plain chunk A", "plain chunk B"],
    }

    monkeypatch.setattr("httpx.AsyncClient", lambda **_: mock_httpx_client(response))

    adapter = HttpTargetAdapter(make_rag_target())
    result = await adapter.ainvoke([HumanMessage(content="query")])

    parsed = json.loads(result.content)
    assert parsed["chunks"][0] == {"text": "plain chunk A"}
    assert parsed["chunks"][1] == {"text": "plain chunk B"}


@pytest.mark.asyncio
async def test_adapter_uses_custom_field_names(monkeypatch):
    """Adapter respects non-default request_field, response_field, chunks_field config."""
    response = {"result": "custom answer", "documents": [{"content": "doc text"}]}

    captured = {}

    async def fake_post(url, json, headers):
        captured["body"] = json
        mock_r = MagicMock()
        mock_r.json.return_value = response
        mock_r.raise_for_status = MagicMock()
        return mock_r

    mock_client = AsyncMock()
    mock_client.post = fake_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("httpx.AsyncClient", lambda **_: mock_client)

    target = make_rag_target(
        request_field="question",
        response_field="result",
        chunks_field="documents",
        chunk_text_field="content",
    )
    adapter = HttpTargetAdapter(target)
    result = await adapter.ainvoke([HumanMessage(content="my question")])

    assert captured["body"] == {"question": "my question"}
    parsed = json.loads(result.content)
    assert parsed["answer"] == "custom answer"
    assert parsed["chunks"][0]["text"] == "doc text"


@pytest.mark.asyncio
async def test_adapter_sends_auth_header(monkeypatch):
    """auth_header is forwarded as the Authorization header."""
    captured = {}

    async def fake_post(url, json, headers):
        captured["headers"] = headers
        mock_r = MagicMock()
        mock_r.json.return_value = {"answer": "ok", "chunks": []}
        mock_r.raise_for_status = MagicMock()
        return mock_r

    mock_client = AsyncMock()
    mock_client.post = fake_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("httpx.AsyncClient", lambda **_: mock_client)

    target = make_rag_target(auth_header="Bearer secret-token")
    adapter = HttpTargetAdapter(target)
    await adapter.ainvoke([HumanMessage(content="query")])

    assert captured["headers"].get("Authorization") == "Bearer secret-token"


@pytest.mark.asyncio
async def test_adapter_sends_extra_body(monkeypatch):
    """extra_body fields are merged into every POST request."""
    captured = {}

    async def fake_post(url, json, headers):
        captured["body"] = json
        mock_r = MagicMock()
        mock_r.json.return_value = {"answer": "ok", "chunks": []}
        mock_r.raise_for_status = MagicMock()
        return mock_r

    mock_client = AsyncMock()
    mock_client.post = fake_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("httpx.AsyncClient", lambda **_: mock_client)

    target = make_rag_target(extra_body={"include_trace": True, "top_k": 5})
    adapter = HttpTargetAdapter(target)
    await adapter.ainvoke([HumanMessage(content="query")])

    assert captured["body"]["include_trace"] is True
    assert captured["body"]["top_k"] == 5
    assert captured["body"]["query"] == "query"
