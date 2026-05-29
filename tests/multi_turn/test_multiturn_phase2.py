"""Phase 2 unit tests — CrescendoOrchestrator, StaticCrescendoSource, CrescendoScriptLibrary."""

from __future__ import annotations

import json
import tempfile

from tests.multi_turn.conftest import BASE_STATE, RUN_CONFIG


async def test_static_crescendo_serves_script_in_order():
    """start_episode() picks first script; next_prompt() walks turns[turn]."""
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticCrescendoSource

    scripts = [["turn0", "turn1", "turn2"], ["alt0", "alt1"]]
    source = StaticCrescendoSource(scripts=scripts)
    source.start_episode()
    p0 = await source.next_prompt(0, [], "", 0, "", None)
    p1 = await source.next_prompt(1, [], "", 0, "", None)
    p2 = await source.next_prompt(2, [], "", 0, "", None)
    assert p0 == "turn0"
    assert p1 == "turn1"
    assert p2 == "turn2"


async def test_static_crescendo_advances_script_per_episode():
    """Each start_episode() call moves to the next script round-robin."""
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticCrescendoSource

    scripts = [["a0", "a1"], ["b0", "b1"]]
    source = StaticCrescendoSource(scripts=scripts)
    source.start_episode()
    first = await source.next_prompt(0, [], "", 0, "", None)
    source.start_episode()
    second = await source.next_prompt(0, [], "", 0, "", None)
    assert first == "a0"
    assert second == "b0"


async def test_crescendo_orchestrator_walks_all_turns():
    """All turns in the script are sent to exchange_fn in order."""
    from redteamagentloop.agent.multi_turn.crescendo import CrescendoOrchestrator
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticCrescendoSource

    scripts = [["opener", "follow-up", "direct ask"]]
    source = StaticCrescendoSource(scripts=scripts)
    orch = CrescendoOrchestrator(max_turns=3)
    seen_prompts: list[str] = []

    async def recording_exchange(base_state, prompt, history, run_config):
        seen_prompts.append(prompt)
        return {
            **base_state,
            "current_prompt": prompt,
            "current_response": "ok",
            "score": 2.0,
            "score_rationale": "low",
            "error": None,
        }

    result = await orch.run_episode(recording_exchange, BASE_STATE, RUN_CONFIG, source)
    assert seen_prompts == ["opener", "follow-up", "direct ask"]
    assert result.turns_taken == 3


async def test_crescendo_stops_early_on_success():
    """Episode halts as soon as a turn's score reaches vuln_threshold."""
    from redteamagentloop.agent.multi_turn.crescendo import CrescendoOrchestrator
    from redteamagentloop.agent.multi_turn.prompt_sources import StaticCrescendoSource

    source = StaticCrescendoSource(scripts=[["t0", "t1", "t2", "t3"]])
    orch = CrescendoOrchestrator(max_turns=4)

    async def succeed_on_second(base_state, prompt, history, run_config):
        score = 8.0 if len(history) >= 2 else 2.0
        return {
            **base_state,
            "current_prompt": prompt,
            "current_response": "ok",
            "score": score,
            "score_rationale": "",
            "error": None,
        }

    result = await orch.run_episode(succeed_on_second, BASE_STATE, RUN_CONFIG, source)
    assert result.turns_taken == 2
    assert result.successful


async def test_crescendo_script_library_reads_turns():
    """CrescendoScriptLibrary parses 'turns' arrays from a JSONL file."""
    from redteamagentloop.agent.multi_turn.crescendo import CrescendoScriptLibrary

    scripts = [{"turns": ["a", "b"]}, {"turns": ["c", "d", "e"]}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for s in scripts:
            f.write(json.dumps(s) + "\n")
        path = f.name

    lib = CrescendoScriptLibrary(path)
    assert len(lib.all_scripts()) == 2
    assert lib.all_scripts()[0] == ["a", "b"]
    assert lib.all_scripts()[1] == ["c", "d", "e"]
