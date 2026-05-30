"""RAG judge node — scores RAG system responses for policy violations.

Expects state["current_response"] to be a JSON string produced by HttpTargetAdapter:
  {"answer": "...", "chunks": [...], "retrieval_query": ..., "cache": ..., "trace": ...}

Returns the same fields as judge_node: score, score_rationale, error.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Template
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from redteamagentloop.logger import get_session_logger

if TYPE_CHECKING:
    from redteamagentloop.agent.state import RedTeamState

_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "prompts" / "rag_judge_template.j2"
_RAG_JUDGE_TEMPLATE: Template = Template(_TEMPLATE_PATH.read_text())


class RagJudgeOutput(BaseModel):
    score: float = Field(ge=0.0, le=10.0)
    violated_policy: str
    reasoning: str
    attack_succeeded: bool


async def rag_judge_node(state: "RedTeamState", config: dict) -> dict:
    raw_response = state.get("current_response", "")
    if not raw_response:
        return {"score": 0.0, "score_rationale": "No response from RAG endpoint."}

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        # Fallback: treat as plain text (black-box endpoint returning raw string).
        parsed = {"answer": raw_response, "chunks": []}

    answer = parsed.get("answer", "")
    chunks = parsed.get("chunks", [])
    retrieval_query = parsed.get("retrieval_query")
    cache = parsed.get("cache")
    trace = parsed.get("trace")

    cfg = config.get("configurable", {})
    session_id = state["session_id"]
    log = get_session_logger(session_id)
    rate_limiter = cfg.get("judge_rate_limiter")

    judge_llm = cfg.get("judge_llm")
    if judge_llm is None:
        from redteamagentloop.llm_factory import build_judge_llm
        judge_llm = build_judge_llm(cfg.get("app_config"))

    prompt_text = _RAG_JUDGE_TEMPLATE.render(
        target_objective=state["target_objective"],
        adversarial_prompt=state["current_prompt"],
        answer=answer,
        chunks=chunks,
        retrieval_query=retrieval_query,
        cache=cache,
        trace=trace,
    )

    log.debug(
        "rag_judge node started",
        extra={"node": "rag_judge", "iteration": state["iteration_count"], "session_id": session_id},
    )

    if rate_limiter is not None:
        await rate_limiter.acquire()

    structured_llm = judge_llm.with_structured_output(RagJudgeOutput, method="json_mode")

    for attempt in range(2):
        try:
            result: RagJudgeOutput = await structured_llm.ainvoke(
                [HumanMessage(content=prompt_text)]
            )
            score = max(0.0, min(10.0, result.score))
            log.debug(
                f"rag_judge scored {score}",
                extra={"node": "rag_judge", "iteration": state["iteration_count"], "session_id": session_id},
            )
            return {"score": score, "score_rationale": result.reasoning}
        except Exception:
            if attempt == 1:
                log.error(
                    "RAG judge parsing failed on both attempts",
                    exc_info=True,
                    extra={"node": "rag_judge", "iteration": state["iteration_count"], "session_id": session_id},
                )
                return {"score": 0.0, "score_rationale": "RAG judge parsing failed."}

    return {"score": 0.0, "score_rationale": "RAG judge failed."}
