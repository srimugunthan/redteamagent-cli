# LangGraph Removal — Phased Implementation Plan

Each phase is independently testable. Phases 1–5 are the core migration.
Phase 6 is an optional follow-up that improves error handling.

Complete analysis behind this plan: `no_langgraph_imple.md`

---

## Phase 1 — Add `_merge()` helper

**Goal:** lay the mechanical groundwork with zero behaviour change. Every existing
test must still pass at the end of this phase.

> **Note — why annotation changes moved to Phase 4:**
> LangGraph inspects the `config` parameter's type annotation at node-registration time.
> When annotated `RunnableConfig`, LangGraph auto-injects the config dict as the second
> argument. When annotated `dict`, LangGraph omits the injection, causing
> `TypeError: <node>() missing 1 required positional argument: 'config'` in the
> graph-coupled tests. The `RunnableConfig → dict` change must therefore happen in
> Phase 4, immediately after `graph.py` is deleted and before those tests are rewritten.

### Files changed

| File | Change |
|---|---|
| `redteamagentloop/cli.py` | Add `_merge()` helper (9 lines) |

### What to implement

**`cli.py` — add `_merge` before `_run_target`:**

```python
_APPEND_FIELDS = {"attack_history", "successful_attacks"}
_UNION_FIELDS  = {"failed_strategies"}

def _merge(state: dict, updates: dict) -> None:
    for key, value in updates.items():
        if key in _APPEND_FIELDS:
            state[key] = state.get(key, []) + value
        elif key in _UNION_FIELDS:
            state[key] = state.get(key, set()) | value
        else:
            state[key] = value
```

### Verification

```bash
# All existing tests pass — nothing changed except cli.py
uv run pytest --tb=short -q

# _merge is importable
python -c "from redteamagentloop.cli import _merge; print('ok')"
```

---

## Phase 2 — Write the plain loop alongside the existing graph path

**Goal:** implement the new execution path without removing anything. Both paths
coexist so the new loop can be tested in isolation before being switched on.

### Files changed

| File | Change |
|---|---|
| `redteamagentloop/cli.py` | Add `_run_target_loop()` (new function, existing `_run_target` untouched) |

### What to implement

Add `_run_target_loop()` as a standalone async function in `cli.py`. It takes the same
arguments as `_run_target()` minus the `graph` parameter:

```python
async def _run_target_loop(
    initial_state: dict,
    app_config,
    target,
    output_dir: Path,
    run_config: dict,
    dashboard,
    storage,
) -> dict:
    from redteamagentloop.agent.nodes.attacker import attacker_node
    from redteamagentloop.agent.nodes.target_caller import target_caller_node
    from redteamagentloop.agent.nodes.judge import judge_node
    from redteamagentloop.agent.nodes.rag_judge import rag_judge_node
    from redteamagentloop.agent.nodes.loop_controller import loop_controller_node, route_after_judge
    from redteamagentloop.agent.nodes.vuln_logger import vuln_logger_node
    from redteamagentloop.agent.nodes.mutation_engine import mutation_engine_node

    judge_fn = rag_judge_node if target.target_type == "rag" else judge_node
    state = dict(initial_state)

    while True:
        updates = await attacker_node(state, run_config)
        _merge(state, updates)
        if state.get("error"):
            break

        _merge(state, await target_caller_node(state, run_config))
        _merge(state, await judge_fn(state, run_config))
        _merge(state, await loop_controller_node(state, run_config))

        if state["attack_history"]:
            dashboard.update(state["attack_history"][-1])

        route = route_after_judge(state)
        if route == "END":
            break
        if route == "vuln_logger":
            _merge(state, await vuln_logger_node(state, run_config))
            _merge(state, await mutation_engine_node(state, run_config))
        elif route == "mutation_engine":
            _merge(state, await mutation_engine_node(state, run_config))

    return state
```

### New test file: `tests/unit/test_loop.py`

```python
"""Tests for the plain _run_target_loop() — Phase 2 verification."""
import asyncio, pytest
from redteamagentloop.cli import _run_target_loop
from tests.helpers import (
    make_mock_run_config, make_initial_state,
    make_mock_attacker, make_refusing_target, make_mock_judge,
)

@pytest.mark.asyncio
async def test_loop_terminates_at_max_iterations():
    state = make_initial_state(max_iterations=2)
    run_config = make_mock_run_config(
        attacker=make_mock_attacker(),
        target=make_refusing_target(),
        judge=make_mock_judge(score=1.0),
    )
    final = await _run_target_loop(state, ...)
    assert final["iteration_count"] <= 2

@pytest.mark.asyncio
async def test_loop_routes_to_vuln_logger_on_high_score():
    state = make_initial_state(max_iterations=1)
    run_config = make_mock_run_config(
        attacker=make_mock_attacker(),
        target=make_exploitable_target(),
        judge=make_mock_judge(score=9.0),
    )
    final = await _run_target_loop(state, ...)
    assert len(final["successful_attacks"]) == 1

@pytest.mark.asyncio
async def test_loop_accumulates_attack_history():
    state = make_initial_state(max_iterations=3)
    final = await _run_target_loop(state, ...)
    assert len(final["attack_history"]) == 3

@pytest.mark.asyncio
async def test_loop_rag_target_uses_rag_judge(monkeypatch):
    calls = []
    async def spy_rag_judge(state, config):
        calls.append(True)
        return {"score": 1.0, "score_rationale": "", "error": None}
    monkeypatch.setattr("redteamagentloop.cli.rag_judge_node", spy_rag_judge)
    state = make_initial_state(max_iterations=1, target_type="rag")
    await _run_target_loop(state, ...)
    assert calls, "rag_judge_node was not called"
```

### Verification

```bash
# New loop tests pass
uv run pytest tests/unit/test_loop.py -v

# Existing graph tests still pass (graph path untouched)
uv run pytest tests/unit/test_graph.py tests/integration/test_graph_integration.py -v

# Full suite still green
uv run pytest --tb=short -q
```

---

## Phase 3 — Switch traffic to the plain loop; retire the graph path

**Goal:** make `_run_target_loop()` the live execution path. The graph is still
present on disk but is no longer called from `run_all()`.

### Files changed

| File | Change |
|---|---|
| `redteamagentloop/cli.py` | Remove `graph` parameter from `run_all()`, call `_run_target_loop()` instead of `_run_target()` |

### What to implement

**`run_all()` before:**

```python
async def run_all():
    ...
    graph = build_graph(app_config)
    ...
    for target in app_config.targets:
        await _run_target(graph, initial_state, app_config, target, ...)
```

**`run_all()` after:**

```python
async def run_all():
    ...
    # build_graph() call removed
    ...
    for target in app_config.targets:
        initial_state = build_initial_state(app_config, target, objective)
        await _run_target_loop(initial_state, app_config, target, ...)
```

`build_initial_state()` is moved from `graph.py` into `cli.py` (or a new
`redteamagentloop/agent/state_builder.py`) so `graph.py` is no longer imported.

### Verification

```bash
# Full suite still passes — all behaviour-level tests now exercise the plain loop
uv run pytest --tb=short -q

# Confirm graph is no longer invoked during a live (mock) run
uv run redteamagentloop --mock --objective "test" --config config.yaml --target mock
# → should complete without touching build_graph

# Confirm build_graph is no longer imported at runtime
python -c "
import sys
import redteamagentloop.cli
mods = [m for m in sys.modules if 'graph' in m and 'langgraph' not in m]
print(mods)   # should NOT contain 'redteamagentloop.agent.graph'
"
```

---

## Phase 4 — Delete `graph.py`, update type annotations, strip reducers, remove dependency

**Goal:** remove all LangGraph artefacts from the codebase and dependency tree.
The `RunnableConfig → dict` annotation changes that were deferred from Phase 1 happen
here, immediately after `graph.py` is deleted so there is no graph left to break.

### Files changed

| File | Change |
|---|---|
| `redteamagentloop/agent/graph.py` | **Delete** |
| `redteamagentloop/agent/nodes/attacker.py` | `RunnableConfig` → `dict` (import removed) |
| `redteamagentloop/agent/nodes/target_caller.py` | `RunnableConfig` → `dict` (import removed) |
| `redteamagentloop/agent/nodes/judge.py` | `RunnableConfig` → `dict` (import removed) |
| `redteamagentloop/agent/nodes/rag_judge.py` | `RunnableConfig` → `dict` (import removed) |
| `redteamagentloop/agent/nodes/loop_controller.py` | `RunnableConfig` → `dict` (import removed) |
| `redteamagentloop/agent/nodes/vuln_logger.py` | `RunnableConfig` → `dict` (import removed) |
| `redteamagentloop/agent/nodes/mutation_engine.py` | `RunnableConfig` → `dict` (import removed) |
| `redteamagentloop/agent/state.py` | Remove `Annotated` reducers, `append_to_list`, `union_sets`, `operator` import |
| `pyproject.toml` | Remove `langgraph>=0.2` from `dependencies` |

### What to implement

**`state.py` before:**

```python
from typing import Annotated, TypedDict
import operator

def append_to_list(existing, new): return existing + new
def union_sets(existing, new): return existing | new

class RedTeamState(TypedDict):
    attack_history: Annotated[list[AttackRecord], append_to_list]
    successful_attacks: Annotated[list[AttackRecord], append_to_list]
    failed_strategies: Annotated[set[str], union_sets]
```

**`state.py` after:**

```python
from typing import TypedDict

class RedTeamState(TypedDict):
    attack_history: list[AttackRecord]
    successful_attacks: list[AttackRecord]
    failed_strategies: set[str]
```

**`pyproject.toml`:** remove the `langgraph>=0.2` line, then run `uv sync`.

### Verification

```bash
# Dependency is gone from the lockfile
uv sync
python -c "import langgraph" 2>&1 | grep "ModuleNotFoundError"
# → ModuleNotFoundError: No module named 'langgraph'

# graph.py is gone
ls redteamagentloop/agent/graph.py 2>&1 | grep "No such file"

# No remaining langgraph imports anywhere in the package
grep -r "langgraph" redteamagentloop/
# → no output

# No remaining RunnableConfig references
grep -r "RunnableConfig" redteamagentloop/
# → no output

# Full test suite (excluding the now-broken graph test files) passes
uv run pytest --ignore=tests/unit/test_graph.py \
              --ignore=tests/integration/test_graph_integration.py \
              --ignore=tests/unit/test_rag_phase3.py \
              --ignore=tests/test_graph.py \
              --tb=short -q
```

---

## Phase 5 — Modernise the test suite

**Goal:** replace the four LangGraph-coupled test files so the full `pytest` suite
passes again without any `--ignore` flags.

### Files changed

| Old file | Action | New file |
|---|---|---|
| `tests/unit/test_graph.py` (271 lines) | Delete | `tests/unit/test_loop.py` (from Phase 2, already written) |
| `tests/integration/test_graph_integration.py` (320 lines) | Rename + edit ~15 lines | `tests/integration/test_loop_integration.py` |
| `tests/unit/test_rag_phase3.py` (225 lines) | Full rewrite (~60 lines) | same filename |
| `tests/test_graph.py` (223 lines) | Delete | `tests/run_mock_loop.py` |
| *(new)* | Add | `tests/benchmarks/test_loop_speed.py` |

### `tests/integration/test_loop_integration.py`

Copy `test_graph_integration.py`, then for every `graph.ainvoke` call apply this
mechanical substitution:

```python
# BEFORE (every test)
graph = build_graph(config)
final = await graph.ainvoke(initial_state, config=run_config)

# AFTER
from redteamagentloop.cli import _run_target_loop
final = await _run_target_loop(initial_state, app_config, target, ...)
```

The 4 test classes and 15 test assertions are unchanged.

### `tests/unit/test_rag_phase3.py` rewrite

```python
"""Judge dispatch in the plain loop — replaces graph-wiring tests."""
import pytest
from redteamagentloop.agent.nodes.rag_judge import rag_judge_node
from redteamagentloop.agent.nodes.judge import judge_node

def test_rag_target_type_selects_rag_judge():
    target = make_rag_target_config()
    judge_fn = rag_judge_node if target.target_type == "rag" else judge_node
    assert judge_fn is rag_judge_node

def test_llm_target_type_selects_judge():
    target = make_llm_target_config()
    judge_fn = rag_judge_node if target.target_type == "rag" else judge_node
    assert judge_fn is judge_node

@pytest.mark.asyncio
async def test_rag_loop_calls_rag_judge_not_judge(monkeypatch):
    rag_calls, judge_calls = [], []
    async def spy_rag(state, cfg): rag_calls.append(1); return {"score": 1.0, "score_rationale": "", "error": None}
    async def spy_judge(state, cfg): judge_calls.append(1); return {"score": 1.0, "score_rationale": "", "error": None}
    monkeypatch.setattr("redteamagentloop.cli.rag_judge_node", spy_rag)
    monkeypatch.setattr("redteamagentloop.cli.judge_node", spy_judge)
    await _run_target_loop(make_initial_state(max_iterations=1, target_type="rag"), ...)
    assert rag_calls and not judge_calls

@pytest.mark.asyncio
async def test_llm_loop_calls_judge_not_rag_judge(monkeypatch):
    # mirror of above for llm target
    ...

@pytest.mark.asyncio
async def test_rag_judge_score_flows_to_attack_history():
    final = await _run_target_loop(make_initial_state(max_iterations=1, target_type="rag"), ...)
    assert final["attack_history"][0]["score"] == 9.0
```

### `tests/run_mock_loop.py`

```python
"""Manual end-to-end smoke script — replaces tests/test_graph.py."""
import asyncio
from redteamagentloop.cli import _run_target_loop, _merge
from tests.helpers import make_app_config, make_initial_state, make_mock_run_config

async def main():
    config = make_app_config(max_iterations=5)
    state = make_initial_state(config, "elicit unlicensed investment advice")
    run_config = make_mock_run_config(...)
    final = await _run_target_loop(state, config, ...)
    print(f"Iterations: {final['iteration_count']}")
    print(f"Successful attacks: {len(final['successful_attacks'])}")

if __name__ == "__main__":
    asyncio.run(main())
```

### `tests/benchmarks/test_loop_speed.py`

```python
"""Speed regression guard — ensures plain loop stays faster than LangGraph was."""
import asyncio, pytest

@pytest.mark.benchmark(group="loop")
def test_plain_loop_20_iterations_under_50ms(benchmark):
    """Plain loop with mocked LLMs must complete 20 iterations in < 50 ms."""
    result = benchmark(asyncio.run, _run_20_mock_iterations())
    assert result["iteration_count"] == 20

# Run with: uv run pytest tests/benchmarks/ --benchmark-compare
```

### Verification

```bash
# Full suite passes — no --ignore flags needed
uv run pytest --tb=short -q
# → same number of passing tests as before Phase 4 (minus the 3 deleted Mermaid tests)

# Coverage unchanged or improved
uv run pytest --cov=redteamagentloop --cov-report=term-missing -q

# Manual smoke script still works
uv run python tests/run_mock_loop.py
```

---

## Phase 6 — Replace error-as-state with exceptions (optional follow-up)

**Goal:** clean up the antipattern where errors are encoded as a `state["error"]`
string, forcing every downstream node to guard against it. Without LangGraph's node
return convention this restriction is gone.

This phase is independent of Phases 1–5 and can be deferred or skipped. It does not
affect observable behaviour — it improves code clarity only.

### Files changed

| File | Change |
|---|---|
| `redteamagentloop/exceptions.py` | **New** — sentinel exception classes |
| `redteamagentloop/agent/nodes/attacker.py` | `return {"error": ...}` → `raise` |
| `redteamagentloop/agent/nodes/target_caller.py` | `return {"error": ...}` → `raise` |
| `redteamagentloop/agent/nodes/judge.py` | Remove `if state.get("error"): return {}` guard |
| `redteamagentloop/agent/nodes/rag_judge.py` | Same guard removal |
| `redteamagentloop/agent/nodes/loop_controller.py` | Same guard removal |
| `redteamagentloop/agent/nodes/vuln_logger.py` | Same guard removal |
| `redteamagentloop/agent/nodes/mutation_engine.py` | Same guard removal |
| `redteamagentloop/agent/state.py` | Remove `error: str \| None` field |
| `redteamagentloop/cli.py` | Replace `if state.get("error"): break` with `try/except` |

### What to implement

**`redteamagentloop/exceptions.py` (new file):**

```python
class MaxIterationsReached(Exception): pass
class AttackerLLMFailed(Exception): pass
class CircuitBreakerTripped(Exception): pass
class TargetUnreachable(Exception): pass
```

**`attacker_node` — before / after:**

```python
# BEFORE
if state["iteration_count"] >= state["max_iterations"]:
    return {"error": "max_iterations_reached"}

# AFTER
if state["iteration_count"] >= state["max_iterations"]:
    raise MaxIterationsReached(f"reached {state['max_iterations']} iterations")
```

**`_run_target_loop` — before / after:**

```python
# BEFORE
while True:
    updates = await attacker_node(state, run_config)
    _merge(state, updates)
    if state.get("error"):
        break
    ...

# AFTER
try:
    while True:
        _merge(state, await attacker_node(state, run_config))
        _merge(state, await target_caller_node(state, run_config))
        _merge(state, await judge_fn(state, run_config))
        _merge(state, await loop_controller_node(state, run_config))
        if state["attack_history"]:
            dashboard.update(state["attack_history"][-1])
        route = route_after_judge(state)
        if route == "END":
            break
        if route == "vuln_logger":
            _merge(state, await vuln_logger_node(state, run_config))
            _merge(state, await mutation_engine_node(state, run_config))
        elif route == "mutation_engine":
            _merge(state, await mutation_engine_node(state, run_config))
except MaxIterationsReached:
    pass
except CircuitBreakerTripped as e:
    console.print(f"[red]Session terminated: {e}[/red]")
```

### Verification

```bash
# All tests pass — exception paths are now exercised via pytest.raises
uv run pytest --tb=short -q

# No remaining error-as-state patterns
grep -r '"error"' redteamagentloop/agent/nodes/
# → no output (all replaced by raises)

grep -r 'state.get("error")' redteamagentloop/
# → no output
```

---

## Migration Checklist

| Phase | Description | Testable gate |
|---|---|---|
| **1** | Add `_merge()`, update type annotations | `uv run pytest -q` (all green, no change) |
| **2** | Write `_run_target_loop()` alongside old path | `uv run pytest tests/unit/test_loop.py -v` (new tests green) |
| **3** | Switch `run_all()` to plain loop | `uv run pytest -q` + mock CLI run |
| **4** | Delete `graph.py`, strip reducers, remove dependency | `import langgraph` fails; suite passes with `--ignore` |
| **5** | Rewrite LangGraph-coupled test files | `uv run pytest -q` (full suite, no `--ignore`) |
| **6** | Replace error-as-state with exceptions (optional) | `uv run pytest -q` + grep confirms no `state.get("error")` |

Each phase leaves the codebase in a working, deployable state. Phases 1–3 are
purely additive (nothing is deleted) and carry zero risk. Phase 4 is the first
destructive step and should be gated on Phase 3's tests all passing.
