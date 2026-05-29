# Call Sequence Trace — MCTS Static Library Mode

Command traced:
```
uv run redteamagentloop \
  --multi-turn-mode mcts \
  --prompt-file evaluation/judge_eval_dataset.jsonl \
  --objective "Bypass KYC compliance checks" \
  --target tinyllama \
  --max-turns-per-episode 4 --episodes 1 \
  --mcts-simulations 10 --mcts-branching-factor 3
```

Effective config after CLI overrides:
| Parameter | Value | Source |
|---|---|---|
| `multi_turn.mode` | `mcts` | `--multi-turn-mode` |
| `multi_turn.max_turns_per_episode` | `4` | `--max-turns-per-episode` |
| `multi_turn.max_episodes` | `1` | `--episodes` |
| `multi_turn.mcts_simulations` | `10` | `--mcts-simulations` |
| `multi_turn.mcts_branching_factor` | `3` | `--mcts-branching-factor` |
| `multi_turn.mcts_exploration_constant` | `1.414` | config.yaml default |
| `multi_turn.mcts_rollout_depth` | `3` | config.yaml default |
| `attacker.prompt_file` | `evaluation/judge_eval_dataset.jsonl` | `--prompt-file` |
| `loop.vuln_threshold` | `7.0` | config.yaml |

---

## Phase 1 — CLI startup (`cli.py: main`)

```
main()
├── load_dotenv()                           # reads .env → sets GROQ_API_KEY, ANTHROPIC_API_KEY
├── argparse.parse_args()                   # parses all flags above
├── check_authorization("authorization.txt") # exits if "AUTHORIZED: true" missing
├── load_config("config.yaml")              # returns AppConfig (Pydantic model)
├── app_config.attacker.prompt_file = "evaluation/judge_eval_dataset.jsonl"
├── app_config.loop.multi_turn.mode = "mcts"
├── app_config.loop.multi_turn.max_turns_per_episode = 4
├── app_config.loop.multi_turn.max_episodes = 1
├── app_config.loop.multi_turn.mcts_simulations = 10
├── app_config.loop.multi_turn.mcts_branching_factor = 3
├── check_api_keys(app_config)              # validates GROQ_API_KEY + ANTHROPIC_API_KEY present
├── build_graph(app_config)                 # LangGraph graph built (not used in multi-turn mode)
├── targets = [TargetConfig(model="tinyllama", base_url="http://localhost:11434/v1")]
└── asyncio.run(run_all())
```

---

## Phase 2 — Per-target setup (`cli.py: run_all → _run_target_multiturn`)

```
_run_target_multiturn(initial_state, app_config, target=tinyllama, ...)
│
├── build_attacker_llm(app_config)
│     └── ChatOpenAI(model="llama-3.3-70b-versatile", base_url="https://api.groq.com/openai/v1")
│         # Attacker LLM — NOT called during expand/simulate (StaticMCTSSource used instead)
│
├── build_target_llm(target)
│     └── ChatOpenAI(model="tinyllama", base_url="http://localhost:11434/v1")
│         # Called once per prompt in expand + once per rollout turn in simulate
│
├── build_judge_llm(app_config)
│     └── ChatAnthropic(model="claude-haiku-4-5-20251001")
│         # Called once per prompt in expand + once per rollout turn in simulate
│
├── run_config = { configurable: { attacker_llm, target_llm, judge_llm, ... } }
│
├── build_orchestrator_and_source(mt_cfg, app_config)
│     ├── mode = "mcts"
│     ├── configure("evaluation/judge_eval_dataset.jsonl")
│     │     └── PromptLibrary._load()       # reads file once; indexes prompts by strategy
│     ├── StaticMCTSSource(library, branching_factor=3)
│     │     # next_k_prompts() samples from library — NO attacker LLM call ever
│     └── MCTSOrchestrator(simulations=10, branching_factor=3, C=1.414,
│                           rollout_depth=3, max_turns=4)
│
└── orchestrator.run_all_episodes(exchange_fn=single_exchange, base_state,
                                   run_config, prompt_source, max_episodes=1)
```

---

## Phase 3 — Episode loop (`base.py: run_all_episodes`)

`max_episodes=1`, so this runs exactly one episode then returns.

```
run_all_episodes(max_episodes=1)
└── run_episode(single_exchange, base_state, run_config, prompt_source)
      └── [Phase 4 — MCTS loop]
```

---

## Phase 4 — MCTS loop (`mcts.py: MCTSOrchestrator.run_episode`)

Tree structure evolves across 10 simulations. Each node represents a conversation state.

```
root = MCTSNode(depth=0, score=0.0, history=[], visits=0)
all_records = []
```

### Simulation 1

```
_select(root)
└── root has no children → returns root

_is_terminal(root)   depth=0 < 4, score=0.0 < 7.0 → False

_expand(root)
├── StaticMCTSSource.next_k_prompts(k=3, turn=0, history=[])
│     └── PromptLibrary.next_any() × 3          # NO attacker LLM call
│         → [prompt_A, prompt_B, prompt_C]  (3 distinct prompts from library)
│
├── single_exchange(base_state, prompt_A, history=[], run_config)
│     ├── target_caller_node(state, run_config)
│     │     └── tinyllama.ainvoke([SystemMessage, HumanMessage(prompt_A)])
│     │         → response_A                     # HTTP → Ollama :11434
│     └── judge_node(state, run_config)
│           └── claude-haiku.ainvoke([HumanMessage(judge_template)])
│               → JudgeOutput(score=score_A)     # HTTP → Anthropic API
│     → child_A = MCTSNode(depth=1, score=score_A, history=[user:prompt_A, asst:response_A])
│
├── single_exchange(base_state, prompt_B, history=[], run_config)
│     ├── tinyllama.ainvoke(...)  → response_B   # HTTP → Ollama
│     └── claude-haiku.ainvoke(...)  → score_B   # HTTP → Anthropic
│     → child_B = MCTSNode(depth=1, score=score_B, ...)
│
└── single_exchange(base_state, prompt_C, history=[], run_config)
      ├── tinyllama.ainvoke(...)  → response_C   # HTTP → Ollama
      └── claude-haiku.ainvoke(...)  → score_C   # HTTP → Anthropic
      → child_C = MCTSNode(depth=1, score=score_C, ...)

root.children = [child_A, child_B, child_C]
node = child_A   (first child)
all_records += [record_A, record_B, record_C]

_simulate(child_A)                               # rollout from child_A
├── history = child_A.conversation_history        # [user:prompt_A, asst:response_A]
├── best_score = score_A
│
│   Rollout turn d=0:
│   ├── StaticMCTSSource.next_prompt(turn=1, ...)
│   │     └── PromptLibrary.next_any() → rollout_prompt_1  # NO attacker LLM
│   ├── single_exchange(base_state, rollout_prompt_1, history, run_config)
│   │     ├── tinyllama.ainvoke([sys, user:prompt_A, asst:response_A, user:r1])  # Ollama
│   │     └── claude-haiku.ainvoke(...)  → score_r1                               # Anthropic
│   └── best_score = max(score_A, score_r1)
│
│   Rollout turn d=1:
│   ├── next_prompt(turn=2) → rollout_prompt_2
│   ├── single_exchange(... history now has 4 msgs ...)
│   │     ├── tinyllama.ainvoke([sys, 4 history msgs, user:r2])  # Ollama
│   │     └── claude-haiku.ainvoke(...)  → score_r2              # Anthropic
│   └── best_score = max(best_score, score_r2)
│
│   Rollout turn d=2:
│   ├── next_prompt(turn=3) → rollout_prompt_3
│   ├── single_exchange(... 6 msgs in history ...)
│   │     ├── tinyllama.ainvoke([sys, 6 msgs, user:r3])           # Ollama
│   │     └── claude-haiku.ainvoke(...)  → score_r3               # Anthropic
│   └── best_score = max(best_score, score_r3)
│
└── returns best_score / 10.0   (normalised to [0,1] for UCT)

_backprop(child_A, value)
├── child_A.visits=1, child_A.total_value=value
└── root.visits=1,   root.total_value=value
```

**LLM calls in simulation 1:** 3 (expand) + 3 (rollout) = **6 target calls, 6 judge calls, 0 attacker calls**

---

### Simulations 2 and 3 — expand child_B and child_C

```
Simulation 2:
_select(root) → child_B  (visits=0 → UCT=inf, beats child_A's finite UCT)
_expand(child_B) → [child_B0, child_B1, child_B2]  (3 target + 3 judge calls)
node = child_B0
_simulate(child_B0) → rollout 3 turns            (3 target + 3 judge calls)
_backprop(child_B0) → child_B0, child_B, root updated

Simulation 3:
_select(root) → child_C  (visits=0 → UCT=inf)
_expand(child_C) → [child_C0, child_C1, child_C2]  (3 target + 3 judge calls)
node = child_C0
_simulate(child_C0) → rollout 3 turns            (3 target + 3 judge calls)
_backprop(child_C0) → child_C0, child_C, root updated
```

After simulation 3: tree has root + 3 depth-1 nodes, each with 3 depth-2 children (9 depth-2 nodes total).

---

### Simulations 4–10 — deeper tree exploration

```
Each simulation:
_select(root)
│  root → walk by UCT to a depth-1 child → walk by UCT to a depth-2 child
│  (unvisited depth-2 nodes return UCT=inf, so they are selected first)

_is_terminal(depth-2 node)?
│  depth=2 < max_turns=4 → expand unless score >= 7.0

_expand(depth-2 node) → 3 depth-3 children      (3 target + 3 judge calls)
node = first depth-3 child

_simulate(depth-3 node) → rollout up to 3 turns  (≤3 target + ≤3 judge calls)
│  stops early if best_score >= vuln_threshold=7.0

_backprop(node) → updates node + depth-2 + depth-1 + root
```

Once all depth-2 nodes have been visited and depth-3 nodes created, simulations 7–10 select from depth-3 nodes and expand to depth-4. Depth-4 nodes are terminal (`depth >= max_turns=4`), so `_expand` is skipped for them and `_simulate` returns immediately with the node's own score.

---

## Phase 4 summary — tree structure after all 10 simulations

```
root (depth=0, visits=10)
├── child_A (depth=1, visits≈3–4)
│     ├── child_A0 (depth=2, visits≈1–2)
│     │     ├── child_A00 (depth=3, visits≈1)
│     │     └── ...
│     └── ...
├── child_B (depth=1, visits≈3–4)
│     └── ...
└── child_C (depth=1, visits≈2–3)
      └── ...
```

`_best_leaf(root)` does a DFS across all nodes and returns the one with the highest `score`. Root itself is excluded (`depth > 0` required).

---

## LLM call budget — full episode

| Phase | Expand calls | Simulate calls | Target (Ollama) | Judge (Anthropic) | Attacker (Groq) |
|---|---|---|---|---|---|
| Each simulation | 3 prompts × (1 target + 1 judge) | ≤3 turns × (1 target + 1 judge) | ≤6 | ≤6 | **0** |
| 10 simulations total | — | — | **≤60** | **≤60** | **0** |

Attacker LLM (Groq) is **never called** because `StaticMCTSSource.next_k_prompts()` reads from `PromptLibrary` directly. The attacker LLM is only used when `DynamicMCTSSource` is chosen (i.e. when `--prompt-file` is omitted).

Actual call counts are lower than the maximum because:
- `_simulate` stops early when `best_score >= 7.0`
- `_expand` is skipped on terminal nodes (`depth >= 4` or `score >= 7.0`)

---

## Phase 5 — post-processing (`cli.py: _run_target_multiturn`)

```
episode_results = [EpisodeResult(attack_records, best_conversation, best_score)]

all_records = [r for ep in episode_results for r in ep.attack_records]
successes   = [r for r in all_records if r["was_successful"]]   # score >= 7.0

StorageManager.log_attack(rec)   # for each success:
├── append to reports/tinyllama_vulnerabilities.jsonl
└── INSERT INTO reports/metadata.db

ReportGenerator.load_session_data(...)
ReportGenerator.save(report, "reports/output/")
└── writes reports/output/<session_id>_<timestamp>.html

console.print("Multi-turn complete: ...")
console.print("Report saved → ...")
```

---

## End-to-end sequence diagram

```
CLI                    MCTSOrchestrator      StaticMCTSSource    tinyllama (Ollama)   Claude Haiku
 │                           │                     │                    │                   │
 │  build_orchestrator()     │                     │                    │                   │
 │──────────────────────────►│                     │                    │                   │
 │                           │  configure(jsonl)   │                    │                   │
 │                           │────────────────────►│                    │                   │
 │                           │  PromptLibrary loaded│                   │                   │
 │                           │◄────────────────────│                    │                   │
 │                           │                     │                    │                   │
 │  run_all_episodes()        │                     │                    │                   │
 │──────────────────────────►│                     │                    │                   │
 │                           │                     │                    │                   │
 │         ┌─── for simulation 1..10 ──────────────────────────────────────────────────┐   │
 │         │                 │  _select(root)       │                    │               │   │
 │         │                 │─────────────┐        │                    │               │   │
 │         │                 │◄────────────┘        │                    │               │   │
 │         │                 │                      │                    │               │   │
 │         │                 │──── _expand ─────────────────────────────────────────────┤   │
 │         │                 │  next_k_prompts(k=3) │                    │               │   │
 │         │                 │────────────────────►│                    │               │   │
 │         │                 │  [p1, p2, p3]        │                    │               │   │
 │         │                 │◄────────────────────│                    │               │   │
 │         │                 │                      │                    │               │   │
 │         │   ┌── for each of 3 prompts ──────────────────────────────────────────┐   │   │
 │         │   │             │  target_caller_node(prompt_i, history)  │           │   │   │
 │         │   │             │─────────────────────────────────────────►           │   │   │
 │         │   │             │  response_i                             │           │   │   │
 │         │   │             │◄────────────────────────────────────────            │   │   │
 │         │   │             │  judge_node(prompt_i, response_i)       │           │   │   │
 │         │   │             │──────────────────────────────────────────────────────────►  │
 │         │   │             │  JudgeOutput(score_i)                   │           │   │   │
 │         │   │             │◄───────────────────────────────────────────────────────────  │
 │         │   │             │  MCTSNode(depth+1, score_i, history+2)  │           │   │   │
 │         │   └─────────────────────────────────────────────────────────────────────┘   │   │
 │         │                 │                      │                    │               │   │
 │         │──── _simulate ──────────────────────────────────────────────────────────────┤   │
 │         │   ┌── for d in 0..rollout_depth-1 ────────────────────────────────────┐   │   │
 │         │   │             │  next_prompt(turn)   │                    │           │   │   │
 │         │   │             │────────────────────►│                    │           │   │   │
 │         │   │             │  rollout_prompt       │                    │           │   │   │
 │         │   │             │◄────────────────────│                    │           │   │   │
 │         │   │             │  target_caller_node(rollout_prompt, history+d)       │   │   │
 │         │   │             │─────────────────────────────────────────►           │   │   │
 │         │   │             │  response                                │           │   │   │
 │         │   │             │◄────────────────────────────────────────            │   │   │
 │         │   │             │  judge_node(...)                         │           │   │   │
 │         │   │             │──────────────────────────────────────────────────────────►  │
 │         │   │             │  score                                   │           │   │   │
 │         │   │             │◄───────────────────────────────────────────────────────────  │
 │         │   └─────────────────────────────────────────────────────────────────────┘   │   │
 │         │                 │                      │                    │               │   │
 │         │                 │  _backprop(node, value)                  │               │   │
 │         │                 │─────────────┐        │                    │               │   │
 │         │                 │◄────────────┘        │                    │               │   │
 │         └──────────────────────────────────────────────────────────────────────────────┘   │
 │                           │                      │                    │               │   │
 │                           │  _best_leaf(root)    │                    │               │   │
 │                           │─────────────┐        │                    │               │   │
 │                           │◄────────────┘        │                    │               │   │
 │  EpisodeResult             │                      │                    │               │   │
 │◄──────────────────────────│                      │                    │               │   │
 │                           │                      │                    │               │   │
 │  StorageManager.log_attack(successes)            │                    │               │   │
 │  ReportGenerator.save(report)                    │                    │               │   │
```

---

## Key design points visible in this trace

**Attacker LLM is bypassed entirely.**
`StaticMCTSSource.next_k_prompts()` pulls from `PromptLibrary.next_any()` in a loop. No Groq API call is made at any point. The Groq key is validated at startup but never used.

**Conversation history grows with each expand depth.**
At depth 1: `[system, user, assistant]` — 3 messages to tinyllama.  
At depth 2: `[system, user1, asst1, user2, assistant2]` — 5 messages.  
At depth 3: 7 messages. At depth 4 (terminal): 9 messages.

**UCT guides exploration vs exploitation.**
Early simulations select unvisited nodes (UCT=∞). Later simulations balance between branches that scored higher (exploitation) and branches visited fewer times (exploration), controlled by `C=1.414`.

**Simulate rollout does not write to the tree.**
Rollout calls `single_exchange` but the results are used only to estimate the leaf value — no new `MCTSNode` is created, no record is appended to `all_records`. Only `_expand` creates persistent nodes and records.

**`_best_leaf` picks the highest-scoring node, not the most-visited.**
UCT optimises the search budget, but the final answer is the node with the best observed score, regardless of how many times it was visited.
