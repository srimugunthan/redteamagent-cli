"""Vulnerability logger node — persists confirmed attacks and alerts the terminal."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from redteamagentloop.logger import get_session_logger

if TYPE_CHECKING:
    from redteamagentloop.agent.state import AttackRecord, RedTeamState

_console = Console()


async def vuln_logger_node(state: "RedTeamState", config: dict) -> dict:
    session_id = state["session_id"]
    log = get_session_logger(session_id)
    cfg = config.get("configurable", {})
    storage_manager = cfg.get("storage_manager")

    record: AttackRecord = {
        "session_id": session_id,
        "iteration": state["iteration_count"],
        "episode": 0,
        "strategy": state["current_strategy"],
        "prompt": state["current_prompt"],
        "response": state["current_response"],
        "score": state["score"],
        "score_rationale": state["score_rationale"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "was_successful": True,
        "mutation_depth": len(state.get("current_mutations", [])),
    }

    log.info(
        f"vulnerability confirmed: score={state['score']:.1f} "
        f"strategy={state['current_strategy']} iteration={state['iteration_count']}",
        extra={"node": "vuln_logger", "iteration": state["iteration_count"],
               "session_id": session_id},
    )

    if storage_manager is not None:
        logged = await storage_manager.log_attack(record)
        if not logged:
            _console.print(
                f"[yellow]⚠ Duplicate suppressed[/yellow] — "
                f"iteration {state['iteration_count']}, strategy {state['current_strategy']}"
            )
            log.warning(
                "duplicate attack record suppressed by storage",
                extra={"node": "vuln_logger", "iteration": state["iteration_count"],
                       "session_id": session_id},
            )

    # Rich terminal alert.
    score_color = "red" if state["score"] >= 7.0 else "yellow"
    label = Text(f"  Score: {state['score']:.1f}/10  ", style=f"bold {score_color}")
    body = (
        f"[bold]Strategy:[/bold] {state['current_strategy']}\n"
        f"[bold]Prompt:[/bold] {state['current_prompt']}\n"
        f"[bold]Response:[/bold] {state['current_response']}"
    )
    _console.print(Panel(body, title=f"[bold red]VULNERABILITY FOUND[/bold red] {label}"))

    return {"successful_attacks": [record]}
