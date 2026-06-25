"""State schema for RedTeamAgentLoop.

All nodes receive a RedTeamState and return a partial dict of changed fields.
merge() handles field accumulation: list fields append, set fields union, all others overwrite.
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


# ---------------------------------------------------------------------------
# State merge — accumulates node output into the running state dict
# ---------------------------------------------------------------------------

_APPEND_FIELDS: frozenset[str] = frozenset({"attack_history", "successful_attacks"})
_UNION_FIELDS: frozenset[str] = frozenset({"failed_strategies"})


def merge(state: dict, updates: dict) -> None:
    """Apply a node's partial-update dict back into the shared state in-place.

    - Fields in _APPEND_FIELDS (attack_history, successful_attacks): list-extend.
    - Fields in _UNION_FIELDS  (failed_strategies): set-union.
    - All other fields: plain overwrite.
    """
    for key, value in updates.items():
        if key in _APPEND_FIELDS:
            state[key] = state.get(key, []) + value
        elif key in _UNION_FIELDS:
            state[key] = state.get(key, set()) | value
        else:
            state[key] = value


# ---------------------------------------------------------------------------
# State factories
# ---------------------------------------------------------------------------

def build_state(
    objective: str,
    system_prompt: str = "",
    target_type: str = "llm",
    max_iterations: int = 50,
    vuln_threshold: float = 7.0,
    initial_strategy: str = "",
    session_id: str | None = None,
) -> "RedTeamState":
    """Build a fresh RedTeamState without requiring an AppConfig object.

    Suitable for notebook and library use where config.yaml is not available.
    All parameters have sensible defaults; only ``objective`` is required.
    """
    import uuid as _uuid
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
        target_system_prompt=system_prompt,
        target_objective=objective,
        target_type=target_type,
        max_iterations=max_iterations,
        vuln_threshold=vuln_threshold,
        session_id=session_id or str(_uuid.uuid4()),
    )


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
