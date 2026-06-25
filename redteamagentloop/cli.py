"""CLI entry point for RedTeamAgentLoop."""

from __future__ import annotations

import argparse
import asyncio

from dotenv import load_dotenv
from rich.console import Console

from redteamagentloop.config import check_api_keys, check_authorization, load_config
from redteamagentloop.exceptions import (
    AttackerLLMFailed, CircuitBreakerTripped, MaxIterationsReached, TargetUnreachable,
)
from redteamagentloop.logger import configure_logging, get_log_path, get_session_logger
from redteamagentloop.agent.state import build_initial_state, merge
from redteamagentloop.agent.nodes.attacker import attacker_node
from redteamagentloop.agent.nodes.target_caller import target_caller_node
from redteamagentloop.agent.nodes.judge import judge_node
from redteamagentloop.agent.nodes.rag_judge import rag_judge_node
from redteamagentloop.agent.nodes.agent_judge import agent_judge_node
from redteamagentloop.agent.nodes.loop_controller import loop_controller_node, route_after_judge
from redteamagentloop.agent.nodes.vuln_logger import vuln_logger_node
from redteamagentloop.agent.nodes.mutation_engine import mutation_engine_node

console = Console()


async def _run_target_loop(
    initial_state: dict,
    run_config: dict,
    target_type: str = "llm",
    dashboard=None,
) -> dict:
    """Plain async loop — the LangGraph-free execution path.

    Drives attacker → target → judge → loop_controller in a while loop,
    applying merge() after each node to accumulate list/set fields.
    dashboard.update() is called directly instead of via astream().
    """
    judge_fn = (
        rag_judge_node   if target_type == "rag"   else
        agent_judge_node if target_type == "agent" else
        judge_node
    )
    state = dict(initial_state)

    log = get_session_logger(state["session_id"])
    log.info(
        "session started",
        extra={"node": "cli", "iteration": 0, "session_id": state["session_id"]},
    )

    try:
        while True:
            merge(state, await attacker_node(state, run_config))
            merge(state, await target_caller_node(state, run_config))
            merge(state, await judge_fn(state, run_config))
            merge(state, await loop_controller_node(state, run_config))

            if dashboard is not None and state.get("attack_history"):
                dashboard.update(state["attack_history"][-1])

            route = route_after_judge(state)
            if route == "END":
                break
            if route == "vuln_logger":
                merge(state, await vuln_logger_node(state, run_config))
                merge(state, await mutation_engine_node(state, run_config))
            elif route == "mutation_engine":
                merge(state, await mutation_engine_node(state, run_config))

    except MaxIterationsReached:
        log.info(
            "session complete: max iterations reached",
            extra={"node": "cli", "iteration": state.get("iteration_count", 0),
                   "session_id": state["session_id"]},
        )
    except CircuitBreakerTripped as exc:
        console.print(f"[red]Session terminated: {exc}[/red]")
        log.error(
            f"session terminated by circuit breaker: {exc}",
            extra={"node": "cli", "iteration": state.get("iteration_count", 0),
                   "session_id": state["session_id"]},
        )
    except (AttackerLLMFailed, TargetUnreachable) as exc:
        console.print(f"[yellow]Session ended early: {exc}[/yellow]")
        log.warning(
            f"session ended early: {exc}",
            extra={"node": "cli", "iteration": state.get("iteration_count", 0),
                   "session_id": state["session_id"]},
        )

    return state


async def _run_target(
    initial_state,
    app_config,
    target,
    output_dir: str,
    use_mock: bool = False,
) -> None:
    """Run the plain loop against a single target, persist results, and save report."""
    from rich.panel import Panel
    from redteamagentloop.llm_factory import (
        build_attacker_llm, build_judge_llm, build_target_llm,
        build_mock_attacker, build_mock_judge, build_mock_target,
    )
    from redteamagentloop.ratelimit import RateLimiter
    from redteamagentloop.storage.manager import StorageManager
    from redteamagentloop.report_generator import ReportGenerator
    from redteamagentloop.terminal_dashboard import TerminalDashboard

    mode_label = " [yellow](mock)[/yellow]" if use_mock else ""
    log_path = get_log_path(initial_state["session_id"])
    console.print(Panel(
        f"[bold cyan]Target:[/bold cyan] {target.model} ({target.output_tag}){mode_label}\n"
        f"[bold cyan]Objective:[/bold cyan] {initial_state['target_objective']}\n"
        f"[bold cyan]Session log:[/bold cyan] {log_path}",
        title="RedTeamAgentLoop — starting run",
    ))

    storage_cfg = app_config.storage
    storage = StorageManager(
        jsonl_path=storage_cfg.jsonl_path.replace("{target_tag}", target.output_tag),
        sqlite_path=storage_cfg.sqlite_path,
    )

    dashboard = TerminalDashboard(
        objective=initial_state["target_objective"],
        target=target.model,
        vuln_threshold=app_config.loop.vuln_threshold,
    )

    # Build LLMs once and inject — nodes use these rather than constructing inline.
    if use_mock:
        attacker_llm = build_mock_attacker()
        target_llm = build_mock_target()
        judge_llm = build_mock_judge()
    else:
        attacker_llm = build_attacker_llm(app_config)
        target_llm = build_target_llm(target)
        judge_llm = build_judge_llm(app_config)

    # Build per-run rate limiters (0 rpm = disabled; always disabled in mock mode).
    attacker_rate_limiter = RateLimiter(0 if use_mock else app_config.attacker.rpm)
    target_rate_limiter = RateLimiter(0 if use_mock else target.rpm)
    judge_rate_limiter = RateLimiter(0 if use_mock else app_config.judge.rpm)

    run_config = {"configurable": {
        "app_config": app_config,
        "attacker_llm": attacker_llm,
        "target_llm": target_llm,
        "judge_llm": judge_llm,
        "attacker_rate_limiter": attacker_rate_limiter,
        "target_rate_limiter": target_rate_limiter,
        "judge_rate_limiter": judge_rate_limiter,
    }}

    target_type = getattr(target, "target_type", "llm")
    if target_type == "agent":
        run_config["configurable"]["allowed_tools"] = target.allowed_tools

    with dashboard.live_context():
        final_state = await _run_target_loop(
            initial_state, run_config, target_type=target_type, dashboard=dashboard
        )

    successes = final_state.get("successful_attacks", [])
    history = final_state.get("attack_history", [])
    iterations = final_state.get("iteration_count", 0)

    # Persist successful attacks to storage
    for rec in successes:
        await storage.log_attack(rec)

    dashboard.print_final_summary(final_state)

    # Generate HTML report
    generator = ReportGenerator()
    report = generator.load_session_data(
        session_id=initial_state["session_id"],
        attack_history=history,
        successful_attacks=successes,
        target_model=target.model,
        objective=initial_state["target_objective"],
        vuln_threshold=app_config.loop.vuln_threshold,
        total_iterations=iterations,
    )
    report_path = generator.save(report, output_dir)
    console.print(f"[dim]Report saved → {report_path}[/dim]")


async def _run_target_multiturn(
    initial_state: dict,
    app_config,
    target,
    output_dir: str,
    use_mock: bool = False,
) -> None:
    """Run multi-turn orchestrator against a single target, persist results, save report."""
    from redteamagentloop.agent.multi_turn import build_orchestrator_and_source, single_exchange
    from redteamagentloop.llm_factory import (
        build_attacker_llm, build_judge_llm, build_target_llm,
        build_mock_attacker, build_mock_judge, build_mock_target,
    )
    from redteamagentloop.storage.manager import StorageManager
    from redteamagentloop.report_generator import ReportGenerator

    log_path = get_log_path(initial_state["session_id"])
    console.print(f"[dim]Session log:[/dim] {log_path}")
    log = get_session_logger(initial_state["session_id"])
    log.info(
        "multi-turn session started",
        extra={"node": "cli", "iteration": 0, "session_id": initial_state["session_id"]},
    )

    if use_mock:
        attacker_llm = build_mock_attacker()
        target_llm   = build_mock_target()
        judge_llm    = build_mock_judge()
    else:
        attacker_llm = build_attacker_llm(app_config)
        target_llm   = build_target_llm(target)
        judge_llm    = build_judge_llm(app_config)

    run_config = {"configurable": {
        "app_config":            app_config,
        "attacker_llm":          attacker_llm,
        "target_llm":            target_llm,
        "judge_llm":             judge_llm,
        "attacker_rate_limiter": None,
        "target_rate_limiter":   None,
        "judge_rate_limiter":    None,
    }}

    mt_cfg = app_config.loop.multi_turn
    orchestrator, prompt_source = build_orchestrator_and_source(
        mt_cfg, app_config, attacker_llm
    )

    console.print(
        f"[bold cyan]Multi-turn mode:[/bold cyan] {mt_cfg.mode}  "
        f"[bold cyan]episodes:[/bold cyan] {mt_cfg.max_episodes}  "
        f"[bold cyan]turns/episode:[/bold cyan] {mt_cfg.max_turns_per_episode}"
    )

    episode_results = await orchestrator.run_all_episodes(
        exchange_fn=single_exchange,
        base_state=initial_state,
        run_config=run_config,
        prompt_source=prompt_source,
        max_episodes=mt_cfg.max_episodes,
    )

    all_records = [r for ep in episode_results for r in ep.attack_records]
    successes   = [r for r in all_records if r.get("was_successful")]

    storage_cfg = app_config.storage
    storage = StorageManager(
        jsonl_path=storage_cfg.jsonl_path.replace("{target_tag}", target.output_tag),
        sqlite_path=storage_cfg.sqlite_path,
    )
    for rec in successes:
        await storage.log_attack(rec)

    total_turns = sum(ep.turns_taken for ep in episode_results)
    best_overall = max((ep.best_score for ep in episode_results), default=0.0)
    console.print(
        f"[bold]Multi-turn complete:[/bold] {len(episode_results)} episodes, "
        f"{total_turns} total turns, best score {best_overall:.1f}/10, "
        f"{len(successes)} successful attacks."
    )

    generator = ReportGenerator()
    report = generator.load_multiturn_data(
        session_id=initial_state["session_id"],
        episode_results=episode_results,
        target_model=target.model,
        objective=initial_state["target_objective"],
        mode=mt_cfg.mode,
        max_turns_per_episode=mt_cfg.max_turns_per_episode,
        vuln_threshold=app_config.loop.vuln_threshold,
    )
    report_path = generator.save_multiturn(report, output_dir)
    console.print(f"[dim]Report saved → {report_path}[/dim]")


def main() -> None:
    # Load .env before parsing config so GROQ_API_KEY / ANTHROPIC_API_KEY are set.
    load_dotenv()

    parser = argparse.ArgumentParser(description="RedTeamAgentLoop — LLM red teaming agent")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--objective", default=None,
        help="Red team objective (what the target should NOT do). "
             "Optional — omit to use the default generic security objective.",
    )
    parser.add_argument(
        "--strategy", default=None, metavar="NAME",
        help="Pin the run to a single strategy (e.g. DirectJailbreak, RAGPiiExfiltration). "
             "Strategy rotation is disabled. Must be compatible with the target type: "
             "RAG* strategies require a RAG target; Agent* strategies require an agent target.",
    )
    parser.add_argument("--system-prompt", default="", help="System prompt to use for the target LLM")
    parser.add_argument("--target", default=None, help="output_tag of the target to test (default: all targets)")
    parser.add_argument("--output-dir", default="reports/output", help="Directory for HTML reports")
    parser.add_argument("--auth", default="authorization.txt", help="Path to authorization.txt")
    parser.add_argument("--mock", action="store_true", help="Use mock LLMs for all roles — no API keys required")
    parser.add_argument(
        "--prompt-file", default=None, metavar="PATH",
        help="JSONL file of static prompts (overrides attacker.prompt_file in config.yaml). "
             "Each record must have 'strategy' and 'prompt' fields. "
             "When set, prompts matching the active strategy are served without an LLM call; "
             "strategies with no matching entries fall back to LLM generation.",
    )
    parser.add_argument(
        "--multi-turn-mode",
        choices=["reactive_chain", "crescendo", "mcts"],
        default=None,
        help="Enable multi-turn attack mode. Overrides loop.multi_turn.mode in config.yaml.",
    )
    parser.add_argument(
        "--max-turns-per-episode", type=int, default=None,
        help="Override loop.multi_turn.max_turns_per_episode.",
    )
    parser.add_argument(
        "--episodes", type=int, default=None,
        help="Override loop.multi_turn.max_episodes.",
    )
    parser.add_argument(
        "--crescendo-script-file", default=None,
        help="Override loop.multi_turn.crescendo_script_file. JSONL with 'turns' arrays.",
    )
    parser.add_argument(
        "--mcts-simulations", type=int, default=None,
        help="Override loop.multi_turn.mcts_simulations.",
    )
    parser.add_argument(
        "--mcts-branching-factor", type=int, default=None,
        help="Override loop.multi_turn.mcts_branching_factor.",
    )
    args = parser.parse_args()

    check_authorization(args.auth)
    app_config = load_config(args.config)

    # Configure logging early — before any session logger is created.
    configure_logging(
        log_level=app_config.logging.log_level,
        log_dir=app_config.logging.log_dir,
    )

    if args.prompt_file:
        app_config.attacker.prompt_file = args.prompt_file

    # CLI args override YAML values (only when explicitly passed).
    if args.multi_turn_mode is not None:
        app_config.loop.multi_turn.mode = args.multi_turn_mode
    if args.max_turns_per_episode is not None:
        app_config.loop.multi_turn.max_turns_per_episode = args.max_turns_per_episode
    if args.episodes is not None:
        app_config.loop.multi_turn.max_episodes = args.episodes
    if args.crescendo_script_file is not None:
        app_config.loop.multi_turn.crescendo_script_file = args.crescendo_script_file
    if args.mcts_simulations is not None:
        app_config.loop.multi_turn.mcts_simulations = args.mcts_simulations
    if args.mcts_branching_factor is not None:
        app_config.loop.multi_turn.mcts_branching_factor = args.mcts_branching_factor

    # Validate --strategy before doing any real work.
    if args.strategy:
        from redteamagentloop.agent.strategies import STRATEGY_REGISTRY
        if args.strategy not in STRATEGY_REGISTRY:
            known = ", ".join(sorted(STRATEGY_REGISTRY))
            console.print(f"[red]Unknown strategy '{args.strategy}'.[/red]")
            console.print(f"Known strategies: {known}")
            return
        app_config.loop.strategy_rotation = False

    objective = args.objective or "Test this system for security vulnerabilities and policy violations"

    # Fail fast if required API keys are missing — skipped in mock mode.
    if not args.mock:
        check_api_keys(app_config)

    if args.mock:
        from redteamagentloop.config import TargetConfig
        targets = [TargetConfig(
            model="mock-target",
            base_url="http://mock/v1",
            api_key="mock",
            system_prompt="You are a helpful banking assistant.",
            timeout_seconds=10,
            output_tag="mock",
        )]
    else:
        targets = [
            t for t in app_config.targets
            if args.target is None or args.target == t.output_tag
        ]
        if not targets:
            console.print(f"[red]No targets matched '{args.target}'.[/red]")
            return

    async def run_all() -> None:
        for target in targets:
            target_type = getattr(target, "target_type", "llm")
            if args.strategy:
                from redteamagentloop.agent.strategies import STRATEGY_REGISTRY
                allowed = STRATEGY_REGISTRY[args.strategy].target_types
                if target_type not in allowed:
                    console.print(
                        f"[yellow]Warning: strategy '{args.strategy}' is designed for "
                        f"{allowed} targets but '{target.output_tag}' is a '{target_type}' target. "
                        f"Prompts may not be meaningful.[/yellow]"
                    )
            initial_state = build_initial_state(
                config=app_config,
                target_objective=objective,
                target_system_prompt=args.system_prompt or target.system_prompt,
                target_type=target_type,
                initial_strategy=args.strategy or "",
            )
            if app_config.loop.multi_turn.mode == "single_turn":
                await _run_target(
                    initial_state, app_config, target,
                    args.output_dir, use_mock=args.mock,
                )
            else:
                await _run_target_multiturn(
                    initial_state, app_config, target,
                    args.output_dir, use_mock=args.mock,
                )

    asyncio.run(run_all())


if __name__ == "__main__":
    main()
