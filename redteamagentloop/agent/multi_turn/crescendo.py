"""CrescendoOrchestrator — gradual escalation multi-turn attack."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from redteamagentloop.agent.state import AttackRecord

from .base import EpisodeResult, MultiTurnOrchestrator, register_orchestrator
from .prompt_sources import DynamicCrescendoSource, StaticCrescendoSource


def _build_record(result: dict, session_id: str, turn: int, strategy: str) -> AttackRecord:
    return AttackRecord(
        session_id=session_id,
        iteration=turn,
        strategy=strategy,
        prompt=result.get("current_prompt", ""),
        response=result.get("current_response", ""),
        score=result.get("score", 0.0),
        score_rationale=result.get("score_rationale", ""),
        timestamp=datetime.now(timezone.utc).isoformat(),
        was_successful=result.get("score", 0.0) >= result.get("vuln_threshold", 7.0),
        mutation_depth=0,
    )


class CrescendoScriptLibrary:
    """Reads a JSONL file where each line has a 'turns' array."""

    def __init__(self, path: str) -> None:
        self._scripts: list[list[str]] = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if "turns" in rec and rec["turns"]:
                    self._scripts.append(rec["turns"])

    def all_scripts(self) -> list[list[str]]:
        return self._scripts


@register_orchestrator
class CrescendoOrchestrator(MultiTurnOrchestrator):
    name = "crescendo"

    def __init__(self, max_turns: int) -> None:
        self.max_turns = max_turns

    async def run_episode(
        self,
        exchange_fn,
        base_state: dict,
        run_config: dict,
        prompt_source,
    ) -> EpisodeResult:
        attacker_llm = run_config.get("configurable", {}).get("attacker_llm")

        if isinstance(prompt_source, StaticCrescendoSource):
            prompt_source.start_episode()
        elif isinstance(prompt_source, DynamicCrescendoSource):
            await prompt_source.generate_script(
                base_state["target_objective"], self.max_turns, attacker_llm
            )

        conversation_history: list[dict] = []
        attack_records: list[AttackRecord] = []

        for turn in range(self.max_turns):
            prompt = await prompt_source.next_prompt(
                turn, conversation_history, base_state["target_objective"],
                0.0, "", attacker_llm,
            )
            result = await exchange_fn(base_state, prompt, conversation_history, run_config)
            conversation_history += [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": result.get("current_response", "")},
            ]
            attack_records.append(
                _build_record(result, base_state["session_id"], turn, "crescendo")
            )
            if result.get("score", 0.0) >= base_state["vuln_threshold"]:
                break

        best_score = max((r["score"] for r in attack_records), default=0.0)
        return EpisodeResult(
            attack_records=attack_records,
            conversation_history=conversation_history,
            best_score=best_score,
            successful=best_score >= base_state["vuln_threshold"],
            turns_taken=len(attack_records),
        )
