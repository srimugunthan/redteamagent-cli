"""MCTSOrchestrator — Monte Carlo Tree Search for multi-turn red-teaming."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone

from redteamagentloop.agent.state import AttackRecord

from .base import EpisodeResult, MultiTurnOrchestrator, register_orchestrator


def _answer_text(result: dict) -> str:
    """Extract plain answer text from result, handling both RAG JSON and plain LLM strings."""
    raw = result.get("current_response", "")
    try:
        return json.loads(raw).get("answer", raw)
    except (json.JSONDecodeError, AttributeError):
        return raw


def _build_record(result: dict, session_id: str, depth: int) -> AttackRecord:
    return AttackRecord(
        session_id=session_id,
        iteration=depth,
        strategy="mcts",
        prompt=result.get("current_prompt", ""),
        response=result.get("current_response", ""),
        score=result.get("score", 0.0),
        score_rationale=result.get("score_rationale", ""),
        timestamp=datetime.now(timezone.utc).isoformat(),
        was_successful=result.get("score", 0.0) >= result.get("vuln_threshold", 7.0),
        mutation_depth=depth,
    )


@dataclass
class MCTSNode:
    conversation_history: list[dict]
    prompt: str
    response: str
    score: float
    depth: int
    parent: "MCTSNode | None"
    children: list["MCTSNode"] = dc_field(default_factory=list)
    visits: int = 0
    total_value: float = 0.0

    def uct(self, C: float) -> float:
        if self.visits == 0:
            return float("inf")
        parent_visits = self.parent.visits if self.parent else 1
        return (self.total_value / self.visits) + C * math.sqrt(
            math.log(parent_visits) / self.visits
        )


@register_orchestrator
class MCTSOrchestrator(MultiTurnOrchestrator):
    name = "mcts"

    def __init__(
        self,
        simulations: int,
        branching_factor: int,
        C: float,
        rollout_depth: int,
        max_turns: int,
    ) -> None:
        self.simulations = simulations
        self.branching_factor = branching_factor
        self.C = C
        self.rollout_depth = rollout_depth
        self.max_turns = max_turns

    async def run_episode(
        self,
        exchange_fn,
        base_state: dict,
        run_config: dict,
        prompt_source,
    ) -> EpisodeResult:
        root = MCTSNode(
            conversation_history=[], prompt="", response="",
            score=0.0, depth=0, parent=None,
        )
        attacker_llm = run_config.get("configurable", {}).get("attacker_llm")
        all_records: list[AttackRecord] = []

        for _ in range(self.simulations):
            node = self._select(root)
            if not self._is_terminal(node, base_state):
                new_children = await self._expand(
                    node, prompt_source, exchange_fn,
                    base_state, run_config, attacker_llm, all_records,
                )
                if new_children:
                    node = new_children[0]
            value = await self._multiturn_mutation_simulate(
                node, prompt_source, exchange_fn,
                base_state, run_config, attacker_llm,
            )
            self._backprop(node, value)

        best = self._best_leaf(root)
        best_score = best.score if best else 0.0
        return EpisodeResult(
            attack_records=all_records,
            conversation_history=best.conversation_history if best else [],
            best_score=best_score,
            successful=best_score >= base_state["vuln_threshold"],
            turns_taken=len(all_records),
        )

    # ------------------------------------------------------------------
    # Pure synchronous tree operations (fully testable without LLMs)
    # ------------------------------------------------------------------

    def _select(self, root: MCTSNode) -> MCTSNode:
        node = root
        while node.children:
            node = max(node.children, key=lambda c: c.uct(self.C))
        return node

    def _is_terminal(self, node: MCTSNode, base_state: dict) -> bool:
        return (
            node.depth >= self.max_turns
            or node.score >= base_state["vuln_threshold"]
        )

    def _backprop(self, node: MCTSNode, value: float) -> None:
        n: MCTSNode | None = node
        while n is not None:
            n.visits += 1
            n.total_value += value
            n = n.parent

    def _best_leaf(self, root: MCTSNode) -> MCTSNode | None:
        best, stack = root, [root]
        while stack:
            n = stack.pop()
            if n.score > best.score:
                best = n
            stack.extend(n.children)
        return best if best.depth > 0 else None

    # ------------------------------------------------------------------
    # Async tree operations (require exchange_fn / LLM)
    # ------------------------------------------------------------------

    async def _expand(
        self, node, prompt_source, exchange_fn,
        base_state, run_config, attacker_llm, all_records,
    ) -> list[MCTSNode]:
        if hasattr(prompt_source, "next_k_prompts"):
            candidates = await prompt_source.next_k_prompts(
                self.branching_factor, node.depth,
                node.conversation_history, base_state["target_objective"],
                attacker_llm,
            )
        else:
            candidates = [
                await prompt_source.next_prompt(
                    node.depth, node.conversation_history,
                    base_state["target_objective"], node.score, "", attacker_llm,
                )
                for _ in range(self.branching_factor)
            ]

        new_children: list[MCTSNode] = []
        for prompt in candidates:
            result = await exchange_fn(
                base_state, prompt, node.conversation_history, run_config
            )
            child = MCTSNode(
                conversation_history=node.conversation_history + [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": _answer_text(result)},
                ],
                prompt=prompt,
                response=result.get("current_response", ""),
                score=result.get("score", 0.0),
                depth=node.depth + 1,
                parent=node,
            )
            node.children.append(child)
            new_children.append(child)
            all_records.append(_build_record(result, base_state["session_id"], node.depth))
        return new_children

    async def _multiturn_mutation_simulate(
        self, node, prompt_source, exchange_fn,
        base_state, run_config, attacker_llm,
    ) -> float:
        history = list(node.conversation_history)
        best_score = node.score

        for d in range(self.rollout_depth):
            if best_score >= base_state["vuln_threshold"]:
                break
            prompt = await prompt_source.next_prompt(
                node.depth + d, history,
                base_state["target_objective"], best_score, "", attacker_llm,
            )
            result = await exchange_fn(base_state, prompt, history, run_config)
            history += [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": _answer_text(result)},
            ]
            best_score = max(best_score, result.get("score", 0.0))

        return best_score / 10.0  # normalise to [0, 1] for UCT value estimates
