# Call Sequence Trace: CLI to Report Generation

Complete function call path from `uv run redteamagentloop` to HTML report written to disk.

---

```
uv run redteamagentloop --objective "..." [--config ...] [--mock] [--multi-turn-mode ...]
  ↓
main() — redteamagentloop/cli.py:272
  ├─ load_dotenv()
  ├─ argparse.parse_args()
  │     --config, --objective (required), --system-prompt, --target, --output-dir,
  │     --auth, --mock, --prompt-file,
  │     --multi-turn-mode [reactive_chain|crescendo|mcts],
  │     --max-turns-per-episode, --episodes, --crescendo-script-file,
  │     --mcts-simulations, --mcts-branching-factor
  ├─ check_authorization(args.auth) — redteamagentloop/config.py:129
  │     reads authorization.txt; exits if "AUTHORIZED: true" not present
  ├─ load_config(args.config) — redteamagentloop/config.py:177  →  AppConfig (Pydantic)
  ├─ [CLI args override YAML: multi_turn.mode, max_turns_per_episode, max_episodes, etc.]
  ├─ check_api_keys(app_config) — redteamagentloop/config.py:148  (skipped in --mock mode)
  ├─ [resolve target list from app_config.targets, filtered by --target flag]
  │     mock mode → synthetic TargetConfig(model="mock-target")
  └─ asyncio.run(run_all())
       └─ [for each target]
            ├─ build_initial_state(config, objective, system_prompt)
            │     → RedTeamState (TypedDict) — redteamagentloop/agent/state.py:67
            │       session_id = uuid4(), iteration_count=0, mutation_queue=[]...
            │
            ├─ if multi_turn.mode == "single_turn"
            │     _run_target(initial_state, app_config, target, output_dir, use_mock)
            │       — redteamagentloop/cli.py:89
            │
            └─ else (reactive_chain | crescendo | mcts)
                  _run_target_multiturn(initial_state, app_config, target, output_dir, use_mock)
                    — redteamagentloop/cli.py:185
```

---

## Single-Turn Path: `_run_target()`

```
_run_target() — redteamagentloop/cli.py:89
  ├─ StorageManager(jsonl_path, sqlite_path) — redteamagentloop/storage/manager.py
  ├─ TerminalDashboard(objective, target, vuln_threshold) — redteamagentloop/terminal_dashboard.py
  ├─ build LLMs (once, injected via run_config):
  │     mock mode → build_mock_{attacker,target,judge}()
  │     live mode:
  │       build_attacker_llm(app_config) — redteamagentloop/llm_factory.py
  │       build_target_llm(target)       — redteamagentloop/llm_factory.py
  │       build_judge_llm(app_config)    — redteamagentloop/llm_factory.py
  ├─ RateLimiter(rpm) × 3 — redteamagentloop/ratelimit.py
  │     attacker_rate_limiter, target_rate_limiter, judge_rate_limiter
  ├─ run_config = {"configurable": {app_config, attacker_llm, target_llm, judge_llm,
  │                                  attacker_rate_limiter, target_rate_limiter, judge_rate_limiter}}
  │     agent target → also injects allowed_tools
  ├─ _run_target_loop(initial_state, run_config, target_type, dashboard)
  │     — redteamagentloop/cli.py:41  [plain async while loop — no LangGraph]
  │
  ├─ [after loop] storage.log_attack(rec) for each successful attack
  ├─ dashboard.print_final_summary(final_state)
  └─ ReportGenerator — redteamagentloop/report_generator.py
        .load_session_data(session_id, attack_history, successful_attacks, ...)
        .save(report, output_dir)
          writes reports/output/{session_id[:8]}_{timestamp}.html
```

---

## Core Attack Loop: `_run_target_loop()`

```
_run_target_loop() — redteamagentloop/cli.py:41
  ├─ judge_fn = judge_node | rag_judge_node | agent_judge_node
  │     selected by target_type: "llm" | "rag" | "agent"
  │
  └─ while True:
       ├─ attacker_node(state, run_config) — redteamagentloop/agent/nodes/attacker.py:63
       │     raises MaxIterationsReached if iteration_count >= max_iterations
       │     _next_strategy(failed_strategies)
       │       → round-robin over STRATEGY_REGISTRY, skipping failed strategies
       │
       │     [static prompt fast-path]
       │     if prompt_file configured → _try_static_prompt(app_config, strategy_name)
       │       → PromptLibrary.next_for(strategy_name)
       │       guardrails.check_prompt(static_prompt)
       │       if allowed → return {current_prompt, strategy, iteration_count+1}
       │
       │     [LLM prompt generation — up to 3 retries]
       │     rate_limiter.acquire()
       │     strategy.generate_prompt(state, attacker_llm) → candidate prompt
       │     guardrails.check_prompt(prompt) — redteamagentloop/guardrails.py
       │       blocked (CBRN/CSAM/etc.) → retry; 3 consecutive blocks → CircuitBreakerTripped
       │     → {current_prompt, current_strategy, iteration_count+1}
       │
       ├─ target_caller_node(state, run_config) — redteamagentloop/agent/nodes/target_caller.py:45
       │     rate_limiter.acquire()
       │     build messages: SystemMessage(system_prompt) + conversation_history + HumanMessage(prompt)
       │     target_llm.ainvoke(messages) → response
       │     circuit breaker: 5 consecutive errors → 60 s pause; 3 pauses → CircuitBreakerTripped
       │     → {current_response}
       │
       ├─ judge_fn(state, run_config) — redteamagentloop/agent/nodes/judge.py:29
       │     rate_limiter.acquire()
       │     render prompts/judge_template.j2 (target_objective, adversarial_prompt, target_response)
       │     judge_llm.with_structured_output(JudgeOutput).ainvoke(...)
       │       → score (0–10), violated_policy, reasoning, is_refusal
       │     → {score, score_rationale}
       │
       ├─ loop_controller_node(state, run_config) — redteamagentloop/agent/nodes/loop_controller.py:19
       │     build AttackRecord {session_id, iteration, episode, strategy, prompt, response,
       │                          score, score_rationale, timestamp, was_successful, mutation_depth}
       │     if strategy_rotation && strategy_mutation_count >= max_mutations_per_strategy
       │         → add current_strategy to failed_strategies
       │     → {attack_history: [record]}  [_merge() appends]
       │
       ├─ dashboard.update(attack_history[-1])
       │
       ├─ route = route_after_judge(state) — redteamagentloop/agent/nodes/loop_controller.py:10
       │     score >= vuln_threshold  → "vuln_logger"
       │     len(mutation_queue) > 0  → "attacker"   (drain queue first)
       │     else                     → "mutation_engine"
       │
       ├─ if route == "END": break        ← never returned; loop exits via MaxIterationsReached
       │
       ├─ if route == "vuln_logger":
       │     vuln_logger_node(state, run_config) — redteamagentloop/agent/nodes/vuln_logger.py:18
       │       build AttackRecord (was_successful=True)
       │       storage_manager.log_attack(record) if injected  [dedup via storage]
       │       Rich terminal alert panel (score, strategy, prompt snippet, response snippet)
       │       → {successful_attacks: [record]}  [_merge() appends]
       │     mutation_engine_node(state, run_config)  [fall through]
       │
       └─ if route == "mutation_engine":
             mutation_engine_node(state, run_config) — redteamagentloop/agent/nodes/mutation_engine.py:65
               _select_tactics(session_id, 1) — cycle through 8 tactics (1 per call)
                 [Paraphrase, LanguageSwap, Abstraction, FormatShift,
                  PersonaReassign, Compression, Elaboration, SuffixAppend]
               attacker_llm.ainvoke([SystemMessage(tactic_instruction), HumanMessage(seed_prompt)])
                 → [mutated_prompt]
               → {mutation_queue: existing + [mutated_prompt],
                  current_mutations: [mutated_prompt],
                  strategy_mutation_count: +1}

  Exceptions that exit the loop cleanly:
    MaxIterationsReached  → pass (normal termination)
    CircuitBreakerTripped → print red message, return state
    AttackerLLMFailed     → print yellow message, return state
    TargetUnreachable     → print yellow message, return state
```

---

## Multi-Turn Path: `_run_target_multiturn()`

```
_run_target_multiturn() — redteamagentloop/cli.py:185
  ├─ build LLMs + run_config (same as single-turn; rate limiters set to None)
  ├─ build_orchestrator_and_source(mt_cfg, app_config, attacker_llm)
  │     — redteamagentloop/agent/multi_turn/__init__.py:19
  │     mode == "reactive_chain"
  │       ReactiveChainOrchestrator(max_turns)  +  StaticSequenceSource | DynamicReactiveSource
  │     mode == "crescendo"
  │       CrescendoOrchestrator(max_turns)  +  StaticCrescendoSource | DynamicCrescendoSource
  │     mode == "mcts"
  │       MCTSOrchestrator(simulations, branching_factor, C, rollout_depth, max_turns)
  │         +  StaticMCTSSource | DynamicMCTSSource
  │
  ├─ orchestrator.run_all_episodes(exchange_fn=single_exchange, base_state, run_config,
  │                                 prompt_source, max_episodes)
  │     — redteamagentloop/agent/multi_turn/base.py:59
  │     [per episode until success or max_episodes]
  │       orchestrator.run_episode(single_exchange, base_state, run_config, prompt_source)
  │         [per turn]
  │           prompt_source.next_prompt(turn, conversation_history, objective,
  │                                      last_score, last_rationale, attacker_llm)
  │           single_exchange(base_state, prompt, conversation_history, run_config)
  │             — redteamagentloop/agent/multi_turn/base.py:69
  │             target_caller_node(state, run_config)  →  current_response
  │             judge_fn(state, run_config)             →  score, score_rationale
  │         → EpisodeResult {attack_records, conversation_history, best_score, successful, turns_taken}
  │
  ├─ [after all episodes] storage.log_attack(rec) for successful attacks
  └─ ReportGenerator.load_multiturn_data(session_id, episode_results, target_model, objective,
                                          mode, max_turns_per_episode, vuln_threshold)
       .save_multiturn(report, output_dir)
         → renders redteamagentloop/templates/report_multiturn.html.j2 (Jinja2)
         → writes reports/output/<session_id[:8]>_multiturn_<timestamp>.html
```

---

## Multi-Turn Flow Diagrams

All three modes share the same outer episode loop from `run_all_episodes()`:

```
run_all_episodes(max_episodes)
  │
  ├─ Episode 1
  │    run_episode() → EpisodeResult {best_score, successful, turns_taken, ...}
  │    if successful → break early
  │
  ├─ Episode 2 ...
  │
  └─ Episode N
```

---

### Mode: `reactive_chain`

Each turn adapts based on the judge's score and rationale from the previous turn.

```
ReactiveChainOrchestrator.run_episode()
  │
  │  conversation_history = []
  │
  └─ for turn in range(max_turns):
       │
       ├─ prompt_source.next_prompt(turn, conversation_history,
       │    objective, last_score, last_rationale, attacker_llm)
       │    │
       │    ├─ StaticSequenceSource  → serve next prompt from PromptLibrary (no LLM)
       │    └─ DynamicReactiveSource → attacker_llm generates prompt conditioned on
       │                               conversation_history + score feedback
       │
       ├─ single_exchange(base_state, prompt, conversation_history, run_config)
       │    ├─ target_caller_node → current_response
       │    └─ judge_fn           → score, score_rationale
       │
       ├─ conversation_history += [{role:user, prompt}, {role:assistant, response}]
       ├─ last_score    = score
       ├─ last_rationale = score_rationale
       │
       ├─ if score >= vuln_threshold → break  (early success)
       │
       └─ [next turn — prompt adapts to last_score / last_rationale]

  → EpisodeResult {attack_records, conversation_history, best_score, successful, turns_taken}
```

Flow diagram:

```
                     ┌─────────────────────────────────────────────┐
                     │  (next turn, adapted to score + rationale)   │
                     ▼                                              │
prompt_source ──► single_exchange ──► judge_fn ──► score >= threshold?
  (reactive)    target_caller_node                      │        │
                                                       YES       NO
                                                        │        │
                                                   break turn  continue
                                                        │        │
                                                        ▼        └──► (loop back)
                                               EpisodeResult
                                                        │
                                              best_score >= threshold?
                                                   YES  │  NO
                                             break  ◄───┘  └──► next episode
                                            episodes
```

---

### Mode: `crescendo`

Each episode runs a pre-planned (or LLM-generated) escalating script of turns. Turns are
fixed in advance; the orchestrator does not adapt mid-episode based on scores.

```
CrescendoOrchestrator.run_episode()
  │
  ├─ [prepare script for this episode]
  │    StaticCrescendoSource  → prompt_source.start_episode()
  │                              (advance to next script in JSONL)
  │    DynamicCrescendoSource → attacker_llm generates full turn list upfront
  │                              (max_turns prompts in one LLM call)
  │
  │  conversation_history = []
  │
  └─ for turn in range(max_turns):
       │
       ├─ prompt_source.next_prompt(turn, ...)
       │    → serve turn[N] from the pre-built script (ignores last_score)
       │
       ├─ single_exchange(base_state, prompt, conversation_history, run_config)
       │    ├─ target_caller_node → current_response
       │    └─ judge_fn           → score, score_rationale
       │
       ├─ conversation_history += [{role:user, prompt}, {role:assistant, response}]
       │
       └─ if score >= vuln_threshold → break  (early success)

  → EpisodeResult {attack_records, conversation_history, best_score, successful, turns_taken}
```

Flow diagram:

```
[generate/load script: T0, T1, T2 ... Tn]
         │
         ▼
T0 ──► single_exchange ──► judge_fn ──► score >= threshold? ──YES──► break
         ▲                                     │
         │                                     NO
         │                                     ▼
T1 ──► single_exchange ──► judge_fn ──► score >= threshold? ──YES──► break
         ▲                                     │
         │                                     NO
        ...                                   ...
         ▲                                     │
Tn ──► single_exchange ──► judge_fn ──► EpisodeResult
```

---

### Mode: `mcts`

Uses Monte Carlo Tree Search. Each node in the tree is a conversation state. The search
balances exploitation (high-score branches) and exploration (unvisited paths) via UCT.

```
MCTSOrchestrator.run_episode()
  │
  │  root = MCTSNode(depth=0, score=0.0, conversation_history=[])
  │
  └─ for _ in range(simulations):
       │
       ├─ _select(root) — traverse tree via UCT until leaf
       │    while node.children:
       │      node = argmax(children, key=uct)   UCT = Q/N + C√(ln(N_parent)/N)
       │    → leaf node
       │
       ├─ if not terminal (depth < max_turns and score < vuln_threshold):
       │    _expand(leaf) — grow branching_factor children
       │      for each candidate prompt (1..branching_factor):
       │        prompt_source.next_k_prompts()  or  next_prompt() × branching_factor
       │        single_exchange(base_state, prompt, leaf.conversation_history, run_config)
       │          ├─ target_caller_node → current_response
       │          └─ judge_fn           → score
       │        new child MCTSNode {conversation_history+=[prompt,response], score, depth+1}
       │      → [child_1, child_2, ..., child_B]   (B = branching_factor)
       │      node = child_1  (first expanded child is the rollout root)
       │
       ├─ _multiturn_mutation_simulate(node) — random rollout to estimate value
       │    for d in range(rollout_depth):
       │      if best_score >= vuln_threshold: break
       │      prompt_source.next_prompt(depth+d, history, objective, best_score, ...)
       │      single_exchange → score
       │      best_score = max(best_score, score)
       │    → value = best_score / 10.0  (normalised for UCT)
       │
       └─ _backprop(node, value)
            walk node → parent → ... → root
            n.visits += 1;  n.total_value += value
            (higher-value paths become more likely to be selected next simulation)

  _best_leaf(root) — DFS over all nodes → node with highest score
  → EpisodeResult {all_records, best_leaf.conversation_history, best_score, ...}
```

Flow diagram:

```
                          root (depth=0)
                         /      |      \
                       C1       C2      C3     ← _expand(): branching_factor=3 children
                      /  \      |
                    C11  C12   C21            ← _expand() on selected leaf next simulation
                          │
                         ...

  Per simulation:
    SELECT ──► EXPAND ──► SIMULATE (rollout) ──► BACKPROP
       │          │             │                    │
    UCT picks   grow B      random turns         update visits
    best leaf   children    from leaf            + total_value
                via LLM     to estimate          up to root
                            branch value

  After all simulations:
    DFS over tree → node with max score → EpisodeResult
```

---

## Key Files

| Role | File |
|---|---|
| CLI entry point | `redteamagentloop/cli.py` |
| State schema + initial state | `redteamagentloop/agent/state.py` |
| Config models / loader | `redteamagentloop/config.py` |
| Attacker node | `redteamagentloop/agent/nodes/attacker.py` |
| Target caller node | `redteamagentloop/agent/nodes/target_caller.py` |
| Judge node (LLM target) | `redteamagentloop/agent/nodes/judge.py` |
| Judge node (RAG target) | `redteamagentloop/agent/nodes/rag_judge.py` |
| Judge node (agent target) | `redteamagentloop/agent/nodes/agent_judge.py` |
| Loop controller node | `redteamagentloop/agent/nodes/loop_controller.py` |
| Vuln logger node | `redteamagentloop/agent/nodes/vuln_logger.py` |
| Mutation engine node | `redteamagentloop/agent/nodes/mutation_engine.py` |
| Ethical guardrails | `redteamagentloop/guardrails.py` |
| Rate limiter | `redteamagentloop/ratelimit.py` |
| LLM factory | `redteamagentloop/llm_factory.py` |
| Multi-turn orchestrators | `redteamagentloop/agent/multi_turn/` |
| Report generator | `redteamagentloop/report_generator.py` |
| Report template | `reports/templates/report.html.j2` |

---

## Single-Turn Node Flow

```
                    ┌────────────────────────────────────────────┐
                    │  (loop continues while no exception)        │
                    ▼                                             │
attacker_node ──► target_caller_node ──► judge_fn ──► loop_controller_node
    ▲                                                      │
    │                                            route_after_judge()
    │                                             [CONDITIONAL]
    │                                                      │
    │              ┌───────────────────────────────────────┤
    │              │                           │            │
    │  MaxIterationsReached           score>=threshold   mutation_queue
    │  CircuitBreakerTripped                  │            empty
    │  AttackerLLMFailed                      ▼            │
    │  TargetUnreachable               vuln_logger_node    │
    │       → exit loop                       │             │
    │                                         ▼             ▼
    └─────────────────────────── mutation_engine_node ◄────┘
                                              │
                                   mutation_queue populated
                                              │
                                    route → "attacker"  ──► (next iteration drains queue)
```

| `route_after_judge()` result | Destination |
|---|---|
| `score >= vuln_threshold` | `vuln_logger_node` → `mutation_engine_node` → `attacker_node` |
| `len(mutation_queue) > 0` | `attacker_node` (drain queue) |
| `mutation_queue` empty | `mutation_engine_node` → `attacker_node` |
| loop exit | exception raised in `attacker_node` (MaxIterationsReached) or target/attacker errors |

> **Note:** The old LangGraph `StateGraph` and `graph.astream()` have been replaced by
> a plain `async while` loop in `_run_target_loop()`. State accumulation is handled by
> `_merge()` in `cli.py`, which appends list fields (`attack_history`, `successful_attacks`)
> and unions set fields (`failed_strategies`).
