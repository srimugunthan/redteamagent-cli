"""State schema for RedTeamAgentLoop.

All nodes receive a RedTeamState and return a partial dict of changed fields.
_merge() in cli.py handles field accumulation (lists append, sets union).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from redteamagentloop.config import AppConfig


# ---------------------------------------------------------------------------
# AttackRecord — one completed attack attempt
# ---------------------------------------------------------------------------

class AttackRecord(TypedDict):
    """Snapshot of a single attack iteration."""
    session_id: str
    iteration: int
    episode: int            # 0 for single-turn; episode index for multi-turn
    strategy: str
    prompt: str
    response: str
    score: float
    score_rationale: str
    timestamp: str          # ISO-8601
    was_successful: bool    # True if score >= vuln_threshold
    mutation_depth: int     # 0 = original prompt, N = Nth mutation


# ---------------------------------------------------------------------------
# RedTeamState — full live state of one agent run
# ---------------------------------------------------------------------------

class RedTeamState(TypedDict):
    # --- Current turn ---
    current_strategy: str
    current_prompt: str
    current_response: str
    score: float
    score_rationale: str
    iteration_count: int

    # --- Memory (accumulated by _merge() in cli.py) ---
    attack_history: list[AttackRecord]
    successful_attacks: list[AttackRecord]
    failed_strategies: set[str]

    # --- Mutation pipeline ---
    mutation_queue: list[str]       # prompts queued for retry with mutations
    current_mutations: list[str]    # mutations generated in this cycle

    # --- Run configuration (set once at start, never mutated) ---
    target_system_prompt: str
    target_objective: str           # what the target must NOT do
    target_type: str                # "llm" | "rag" | "agent" — controls strategy filtering
    max_iterations: int
    vuln_threshold: float
    session_id: str

    # --- Strategy rotation ---
    strategy_mutation_count: int  # mutation engine cycles on current strategy; resets on strategy change


def build_initial_state(
    config: "AppConfig",
    target_objective: str,
    target_system_prompt: str = "",
    target_type: str = "llm",
    initial_strategy: str = "",
) -> RedTeamState:
    """Construct a fresh RedTeamState from config and a run objective."""
    return RedTeamState(
        current_strategy=initial_strategy,
        current_prompt="",
        current_response="",
        score=0.0,
        score_rationale="",
        iteration_count=0,
        attack_history=[],
        successful_attacks=[],
        failed_strategies=set(),
        mutation_queue=[],
        current_mutations=[],
        strategy_mutation_count=0,
        target_system_prompt=target_system_prompt,
        target_objective=target_objective,
        target_type=target_type,
        max_iterations=config.loop.max_iterations,
        vuln_threshold=config.loop.vuln_threshold,
        session_id=str(uuid.uuid4()),
    )
