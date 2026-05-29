"""ReactiveChainOrchestrator — single-path multi-turn attacker with judge feedback."""

from __future__ import annotations

from datetime import datetime, timezone

from redteamagentloop.agent.state import AttackRecord

from .base import EpisodeResult, MultiTurnOrchestrator, PromptSource, register_orchestrator


def _build_record(result: dict, session_id: str, turn: int) -> AttackRecord:
    return AttackRecord(
        session_id=session_id,
        iteration=turn,
        strategy="multi_turn_reactive_chain",
        prompt=result.get("current_prompt", ""),
        response=result.get("current_response", ""),
        score=result.get("score", 0.0),
        score_rationale=result.get("score_rationale", ""),
        timestamp=datetime.now(timezone.utc).isoformat(),
        was_successful=result.get("score", 0.0) >= result.get("vuln_threshold", 7.0),
        mutation_depth=0,
    )


@register_orchestrator
class ReactiveChainOrchestrator(MultiTurnOrchestrator):
    name = "reactive_chain"

    def __init__(self, max_turns: int) -> None:
        self.max_turns = max_turns

    async def run_episode(
        self,
        exchange_fn,
        base_state: dict,
        run_config: dict,
        prompt_source: PromptSource,
    ) -> EpisodeResult:
        conversation_history: list[dict] = []
        attack_records: list[AttackRecord] = []
        last_score = 0.0
        last_rationale = ""
        attacker_llm = run_config.get("configurable", {}).get("attacker_llm")

        for turn in range(self.max_turns):
            prompt = await prompt_source.next_prompt(
                turn,
                conversation_history,
                base_state["target_objective"],
                last_score,
                last_rationale,
                attacker_llm,
            )
            result = await exchange_fn(base_state, prompt, conversation_history, run_config)
            conversation_history += [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": result.get("current_response", "")},
            ]
            last_score = result.get("score", 0.0)
            last_rationale = result.get("score_rationale", "")
            attack_records.append(_build_record(result, base_state["session_id"], turn))
            if last_score >= base_state["vuln_threshold"]:
                break

        best_score = max((r["score"] for r in attack_records), default=0.0)
        return EpisodeResult(
            attack_records=attack_records,
            conversation_history=conversation_history,
            best_score=best_score,
            successful=best_score >= base_state["vuln_threshold"],
            turns_taken=len(attack_records),
        )
