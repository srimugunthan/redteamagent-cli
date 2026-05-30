"""Agent judge node — scores AgentResponse for policy violations.

Expects state["current_response"] to be the JSON string produced by AgentTargetAdapter:
  {"output": "...", "tool_calls": [...], "memory_reads": [...],
   "reasoning_steps": [...], "agent_trace": [...], "raw": {...}}

Returns the same fields as judge_node: score, score_rationale.
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

_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "prompts" / "agent_judge_template.j2"
_AGENT_JUDGE_TEMPLATE: Template = Template(_TEMPLATE_PATH.read_text())


class AgentJudgeOutput(BaseModel):
    score: float = Field(ge=0.0, le=10.0)
    violated_policy: str
    reasoning: str
    attack_succeeded: bool


async def agent_judge_node(state: "RedTeamState", config: dict) -> dict:
    raw_response = state.get("current_response", "")
    if not raw_response:
        return {"score": 0.0, "score_rationale": "No response from agent endpoint."}

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        parsed = {"output": raw_response}

    output = parsed.get("output", "")
    tool_calls = parsed.get("tool_calls", [])
    memory_reads = parsed.get("memory_reads", [])
    reasoning_steps = parsed.get("reasoning_steps", [])
    agent_trace = parsed.get("agent_trace", [])

    cfg = config.get("configurable", {})
    session_id = state["session_id"]
    log = get_session_logger(session_id)
    rate_limiter = cfg.get("judge_rate_limiter")
    allowed_tools = cfg.get("allowed_tools", [])

    judge_llm = cfg.get("judge_llm")
    if judge_llm is None:
        from redteamagentloop.llm_factory import build_judge_llm
        judge_llm = build_judge_llm(cfg.get("app_config"))

    prompt_text = _AGENT_JUDGE_TEMPLATE.render(
        target_objective=state["target_objective"],
        adversarial_prompt=state["current_prompt"],
        output=output,
        tool_calls=tool_calls,
        memory_reads=memory_reads,
        reasoning_steps=reasoning_steps,
        agent_trace=agent_trace,
        allowed_tools=allowed_tools,
    )

    log.debug(
        "agent_judge node started",
        extra={"node": "agent_judge", "iteration": state["iteration_count"], "session_id": session_id},
    )

    if rate_limiter is not None:
        await rate_limiter.acquire()

    structured_llm = judge_llm.with_structured_output(AgentJudgeOutput, method="json_mode")

    for attempt in range(2):
        try:
            result: AgentJudgeOutput = await structured_llm.ainvoke(
                [HumanMessage(content=prompt_text)]
            )
            score = max(0.0, min(10.0, result.score))
            log.debug(
                f"agent_judge scored {score}",
                extra={"node": "agent_judge", "iteration": state["iteration_count"], "session_id": session_id},
            )
            return {"score": score, "score_rationale": result.reasoning}
        except Exception:
            if attempt == 1:
                log.error(
                    "Agent judge parsing failed on both attempts",
                    exc_info=True,
                    extra={"node": "agent_judge", "iteration": state["iteration_count"], "session_id": session_id},
                )
                return {"score": 0.0, "score_rationale": "Agent judge parsing failed."}

    return {"score": 0.0, "score_rationale": "Agent judge failed."}
