"""Phase 3 unit tests — MCTSNode, MCTSOrchestrator tree operations."""

from __future__ import annotations

import math

from tests.multi_turn.conftest import BASE_STATE, RUN_CONFIG, stub_exchange


def make_node(score=0.0, depth=0, parent=None, visits=0, total=0.0):
    from redteamagentloop.agent.multi_turn.mcts import MCTSNode
    n = MCTSNode([], "", "", score, depth, parent)
    n.visits = visits
    n.total_value = total
    return n


def make_orch(**kwargs):
    from redteamagentloop.agent.multi_turn.mcts import MCTSOrchestrator
    defaults = dict(simulations=1, branching_factor=2, C=1.414, rollout_depth=1, max_turns=3)
    defaults.update(kwargs)
    return MCTSOrchestrator(**defaults)


# --- Pure synchronous tree logic (no async, no LLMs) ---

def test_uct_unvisited_is_inf():
    root = make_node(visits=1)
    child = make_node(parent=root)
    assert child.uct(1.414) == float("inf")


def test_uct_formula():
    root = make_node(visits=10)
    child = make_node(parent=root, visits=4, total=2.0)
    exploitation = 2.0 / 4
    exploration = 1.414 * math.sqrt(math.log(10) / 4)
    assert abs(child.uct(1.414) - (exploitation + exploration)) < 1e-9


def test_select_returns_highest_uct_child():
    orch = make_orch()
    root = make_node(visits=4)
    c1 = make_node(parent=root, visits=2, total=0.5)
    c2 = make_node(parent=root, visits=2, total=1.5)
    root.children = [c1, c2]
    assert orch._select(root) is c2


def test_backprop_updates_all_ancestors():
    orch = make_orch()
    root = make_node()
    child = make_node(parent=root)
    grandchild = make_node(parent=child)
    orch._backprop(grandchild, 0.8)
    assert grandchild.visits == 1 and grandchild.total_value == 0.8
    assert child.visits == 1     and child.total_value == 0.8
    assert root.visits == 1      and root.total_value == 0.8


def test_best_leaf_finds_highest_score():
    orch = make_orch()
    root = make_node(score=0.0, depth=0)
    c1 = make_node(score=3.0, depth=1, parent=root)
    c2 = make_node(score=7.5, depth=1, parent=root)
    c3 = make_node(score=5.0, depth=2, parent=c1)
    root.children = [c1, c2]
    c1.children = [c3]
    assert orch._best_leaf(root) is c2


def test_is_terminal_on_depth():
    orch = make_orch(max_turns=3)
    node = make_node(depth=3)
    assert orch._is_terminal(node, {"vuln_threshold": 7.0})


def test_is_terminal_on_score():
    orch = make_orch()
    node = make_node(score=8.0)
    assert orch._is_terminal(node, {"vuln_threshold": 7.0})


# --- Async integration test (stub exchange, no LLMs) ---

async def test_mcts_episode_produces_records():
    from unittest.mock import MagicMock
    from redteamagentloop.agent.multi_turn.mcts import MCTSOrchestrator
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticMCTSSource

    lib = MagicMock()
    lib.next_any.return_value = "attack prompt"
    source = StaticMCTSSource(library=lib, branching_factor=2)
    orch = MCTSOrchestrator(
        simulations=3, branching_factor=2, C=1.414, rollout_depth=1, max_turns=2
    )

    result = await orch.run_episode(stub_exchange, BASE_STATE, RUN_CONFIG, source)
    assert len(result.attack_records) > 0
    assert result.best_score >= 0.0
    assert isinstance(result.conversation_history, list)
