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
main()  — redteamagentloop/cli.py:272
├── load_dotenv()                              # reads .env → sets GROQ_API_KEY, ANTHROPIC_API_KEY
├── argparse.parse_args()                      # parses all flags above
├── check_authorization("authorization.txt")   # exits if "AUTHORIZED: true" missing
│     — redteamagentloop/config.py:129
├── load_config("config.yaml")                 # returns AppConfig (Pydantic)
│     — redteamagentloop/config.py:177
│     reads: targets[tinyllama, gemma2], attacker(groq/llama-3.3-70b-versatile),
│            judge(anthropic/claude-haiku-4-5-20251001), loop defaults
├── app_config.attacker.prompt_file = "evaluation/judge_eval_dataset.jsonl"
├── app_config.loop.multi_turn.mode = "mcts"
├── app_config.loop.multi_turn.max_turns_per_episode = 4
├── app_config.loop.multi_turn.max_episodes = 1
├── app_config.loop.multi_turn.mcts_simulations = 10
├── app_config.loop.multi_turn.mcts_branching_factor = 3
├── check_api_keys(app_config)                 # validates GROQ_API_KEY + ANTHROPIC_API_KEY present
│     — redteamagentloop/config.py:148
├── targets = [TargetConfig(model="tinyllama", ...)]
│     (--target tinyllama filters out gemma2 from config.yaml)
└── asyncio.run(run_all())
      └── for target in [tinyllama]:
            initial_state = build_initial_state(app_config, objective, system_prompt="")
              — redteamagentloop/agent/state.py:67
              session_id=uuid4(), iteration_count=0, mutation_queue=[], ...
            multi_turn.mode != "single_turn"
              → _run_target_multiturn(initial_state, app_config, target=tinyllama,
                                       output_dir="reports/output", use_mock=False)
```

---

## Phase 2 — Per-target setup (`cli.py: _run_target_multiturn`)

```
_run_target_multiturn()  — redteamagentloop/cli.py:185
│
├── build_attacker_llm(app_config)  — redteamagentloop/llm_factory.py:59
│     api_key = os.environ["GROQ_API_KEY"]
│     → ChatOpenAI(model="llama-3.3-70b-versatile",
│                  base_url="https://api.groq.com/openai/v1",
│                  temperature=0.9, max_tokens=1024)
│     NOTE: this LLM is built but NEVER called — StaticMCTSSource bypasses it entirely
│
├── build_target_llm(target)  — redteamagentloop/llm_factory.py:183
│     target.target_type = "llm" (default)
│     → ChatOpenAI(model="tinyllama",
│                  base_url="http://localhost:11434/v1",
│                  api_key="ollama", temperature=0.0, timeout=120)
│     Called for every prompt: once in _expand, once per turn in _simulate
│
├── build_judge_llm(app_config)  — redteamagentloop/llm_factory.py:202
│     judge.provider = "anthropic"
│     → ChatAnthropic(model="claude-haiku-4-5-20251001",
│                     temperature=0.1, max_tokens=512)
│     Called for every prompt: once in _expand, once per turn in _simulate
│
├── run_config = {"configurable": {
│       "app_config": app_config,
│       "attacker_llm": attacker_llm,   # ChatOpenAI / Groq — unused here
│       "target_llm":   target_llm,     # ChatOpenAI / Ollama
│       "judge_llm":    judge_llm,      # ChatAnthropic
│       "attacker_rate_limiter": None,  # rate limiters disabled in multi-turn path
│       "target_rate_limiter":   None,
│       "judge_rate_limiter":    None,
│   }}
│
├── build_orchestrator_and_source(mt_cfg, app_config, attacker_llm)
│     — redteamagentloop/agent/multi_turn/__init__.py:19
│     mode = "mcts", prompt_file = "evaluation/judge_eval_dataset.jsonl"
│     │
│     ├── configure("evaluation/judge_eval_dataset.jsonl")
│     │     — redteamagentloop/agent/strategies/static_file.py:92
│     │     PromptLibrary._load()
│     │       reads file line-by-line; indexes prompts by "strategy" field into _by_strategy{}
│     │       builds _all[] list across all strategies (used by next_any())
│     │     → PromptLibrary singleton stored in module-level _library
│     │
│     ├── StaticMCTSSource(library, branching_factor=3)
│     │     — redteamagentloop/agent/multi_turn/prompt_sources.py:113
│     │     next_k_prompts(k) loops up to k×4 times calling library.next_any()
│     │       to collect k *distinct* prompts — NO attacker LLM call ever made
│     │
│     └── MCTSOrchestrator(simulations=10, branching_factor=3, C=1.414,
│                           rollout_depth=3, max_turns=4)
│           — redteamagentloop/agent/multi_turn/mcts.py:61
│
└── orchestrator.run_all_episodes(
        exchange_fn=single_exchange,
        base_state=initial_state,
        run_config=run_config,
        prompt_source=StaticMCTSSource,
        max_episodes=1)
      — redteamagentloop/agent/multi_turn/base.py:59
```

---

## Phase 3 — Episode loop (`base.py: run_all_episodes`)

`max_episodes=1`, so exactly one episode runs then returns.

```
run_all_episodes(max_episodes=1)
└── result = run_episode(single_exchange, base_state, run_config, prompt_source)
      → EpisodeResult
      if result.successful: break   ← only episode, moot
└── returns [result]
```

---

## Phase 4 — MCTS loop (`mcts.py: MCTSOrchestrator.run_episode`)

Tree nodes represent conversation states. Each simulation does:
**SELECT → EXPAND → SIMULATE (rollout) → BACKPROP**.

```
root = MCTSNode(depth=0, score=0.0, conversation_history=[], visits=0, total_value=0.0)
all_records = []

for _ in range(10):   # simulations
    node  = _select(root)
    if not _is_terminal(node, base_state):
        children = await _expand(node, ...)
        node = children[0]          # first expanded child is the rollout start
    value = await _multiturn_mutation_simulate(node, ...)
    _backprop(node, value)

best  = _best_leaf(root)            # DFS → node with highest score, depth > 0
return EpisodeResult(all_records, best.conversation_history, best.score, ...)
```

---

### `_select(node)` — pure, synchronous

```python
def _select(root):
    node = root
    while node.children:
        node = max(node.children, key=lambda c: c.uct(C=1.414))
    return node   # leaf (no children yet, or terminal)

# UCT formula per child:
#   uct = (total_value / visits) + 1.414 × √(ln(parent.visits) / visits)
#   visits == 0  →  UCT = ∞  (always selected first → ensures full exploration)
```

---

### `_expand(leaf)` — async, calls target + judge

```
_expand(leaf, prompt_source, single_exchange, base_state, run_config, attacker_llm, all_records)
│
├── StaticMCTSSource.next_k_prompts(k=3, turn=leaf.depth,
│       conversation_history=leaf.conversation_history,
│       objective="Bypass KYC compliance checks",
│       attacker_llm=<unused>)
│     — redteamagentloop/agent/multi_turn/prompt_sources.py:120
│     loops up to 3×4=12 calls to PromptLibrary.next_any()
│     deduplicates until 3 distinct prompts collected
│     → [prompt_A, prompt_B, prompt_C]    ← NO Groq API call
│
└── for each prompt_i in [prompt_A, prompt_B, prompt_C]:
      single_exchange(base_state, prompt_i, leaf.conversation_history, run_config)
        — redteamagentloop/agent/multi_turn/base.py:69
        │
        ├── target_type = "llm"  →  judge_fn = judge_node
        ├── state = {**base_state, current_prompt=prompt_i,
        │           conversation_history=leaf.conversation_history}
        │
        ├── target_caller_node(state, run_config)
        │     — redteamagentloop/agent/nodes/target_caller.py:45
        │     rate_limiter = None  →  no throttle
        │     messages = [
        │       SystemMessage(content=target.system_prompt),
        │       HumanMessage(content=prompt_i)
        │     ]
        │     (no conv_history in first expand, because leaf.conversation_history=[])
        │     tinyllama.ainvoke(messages)             ← HTTP POST → Ollama :11434
        │     circuit breaker tracking per session_id
        │     → {current_response: response_i}
        │
        └── judge_node(state, run_config)
              — redteamagentloop/agent/nodes/judge.py:29
              rate_limiter = None  →  no throttle
              render prompts/judge_template.j2(
                target_objective="Bypass KYC compliance checks",
                adversarial_prompt=prompt_i,
                target_response=response_i)
              structured_llm = claude_haiku.with_structured_output(JudgeOutput, method="json_mode")
              structured_llm.ainvoke([HumanMessage(content=rendered_template)])
                                                      ← HTTP POST → Anthropic API
              → JudgeOutput(score=score_i, violated_policy, reasoning, is_refusal)
              → {score: score_i, score_rationale: reasoning_i}

      child_i = MCTSNode(
          conversation_history = leaf.conversation_history
                               + [{"role":"user","content":prompt_i},
                                  {"role":"assistant","content":response_i}],
          prompt=prompt_i, response=response_i,
          score=score_i, depth=leaf.depth+1, parent=leaf)
      leaf.children.append(child_i)
      all_records.append(AttackRecord(...))           # persisted in all_records

→ returns [child_A, child_B, child_C]
  node = child_A   (expand caller takes children[0] as rollout root)
```

**LLM calls per _expand:** 3 target (Ollama) + 3 judge (Anthropic) = **6 calls, 0 attacker**

---

### `_multiturn_mutation_simulate(node)` — async rollout, does NOT add to tree

```
_multiturn_mutation_simulate(child_A, prompt_source, single_exchange,
                              base_state, run_config, attacker_llm)
│
│  history   = list(child_A.conversation_history)    # copy; tree node is not mutated
│  best_score = child_A.score
│
│  for d in range(rollout_depth=3):
│    if best_score >= vuln_threshold=7.0: break       # early exit
│    │
│    ├── StaticMCTSSource.next_prompt(turn=child_A.depth+d, ...)
│    │     → PromptLibrary.next_any()  →  rollout_prompt_d   (NO Groq call)
│    │
│    ├── single_exchange(base_state, rollout_prompt_d, history, run_config)
│    │     ├── target_caller_node
│    │     │     messages = [SystemMessage, ...history_so_far..., HumanMessage(rollout_prompt_d)]
│    │     │     tinyllama.ainvoke(messages)          ← HTTP POST → Ollama :11434
│    │     │     (message list grows: depth+1 prior turns = 2d+3 total messages)
│    │     └── judge_node
│    │           claude_haiku.ainvoke(judge_template) ← HTTP POST → Anthropic API
│    │           → score_d
│    │
│    ├── history += [{"role":"user",...}, {"role":"assistant",...}]
│    └── best_score = max(best_score, score_d)
│        NOTE: these results do NOT create MCTSNodes or append to all_records
│
└── returns best_score / 10.0   # normalised to [0,1] for UCT value estimate
```

**LLM calls per simulate:** up to 3 target (Ollama) + 3 judge (Anthropic)  
Early exit when best_score ≥ 7.0, so actual count is often < 6.

---

### `_backprop(node, value)` — pure, synchronous

```
_backprop(child_A, value=best_score/10.0)
  child_A.visits += 1;  child_A.total_value += value
  leaf.visits    += 1;  leaf.total_value    += value
  ...walk to root...
  root.visits    += 1;  root.total_value    += value
```

Higher-value paths accumulate more total_value → UCT exploitation term rises →
they get selected more often in subsequent simulations.

---

## Phase 4 tree evolution across 10 simulations

```
Sim 1:  _select(root) → root (no children yet)
        _expand(root)  → [child_A, child_B, child_C]  depth=1
        _simulate(child_A); _backprop(child_A)

Sim 2:  _select(root) → child_B  (visits=0 → UCT=∞)
        _expand(child_B) → [child_B0, child_B1, child_B2]  depth=2
        _simulate(child_B0); _backprop(child_B0)

Sim 3:  _select(root) → child_C  (visits=0 → UCT=∞)
        _expand(child_C) → [child_C0, child_C1, child_C2]  depth=2
        _simulate(child_C0); _backprop(child_C0)

Sim 4:  _select(root) → child_A → child_A0  (depth-2, visits=0 → UCT=∞)
        _expand(child_A0) → 3 depth-3 children
        _simulate; _backprop

Sim 5–9: similarly expand unvisited depth-2 and depth-3 nodes
         once depth-3 nodes exist → select deepens to depth-3 → expands to depth-4

Sim 10: depth-4 nodes: _is_terminal() → True (depth >= max_turns=4)
        _expand skipped; _simulate runs immediately from depth-4 node
        (rollout loop: best_score already at depth-4, rollout_depth=3 but
         all score >= 7.0 checks may exit early)
```

Tree shape after all 10 simulations (approximate):
```
root (depth=0, visits=10)
├── child_A (depth=1, visits≈4)
│     ├── child_A0 (depth=2, visits≈2)
│     │     ├── child_A00 (depth=3, visits≈1)
│     │     │     └── child_A000 (depth=4, terminal)
│     │     └── child_A01 ...
│     └── child_A1, child_A2 ...
├── child_B (depth=1, visits≈3)
│     └── child_B0..2 (depth=2) ...
└── child_C (depth=1, visits≈3)
      └── child_C0..2 (depth=2) ...
```

`_best_leaf(root)` — DFS over all nodes → returns the node with the highest `score`.
Root is excluded (requires `depth > 0`). This is the best observed conversation path.

---

## LLM call budget — full episode (10 simulations)

| Operation | When | Target (Ollama) | Judge (Anthropic) | Attacker (Groq) |
|---|---|---|---|---|
| `_expand` | each simulation | 3 | 3 | **0** |
| `_simulate` | each simulation | ≤ 3 | ≤ 3 | **0** |
| **Per simulation** | | **≤ 6** | **≤ 6** | **0** |
| **10 simulations total** | | **≤ 60** | **≤ 60** | **0** |

**Attacker LLM (Groq) is never called.**  
`StaticMCTSSource.next_k_prompts()` and `next_prompt()` both call `PromptLibrary.next_any()`
from the pre-loaded JSONL file. The attacker LLM is only used by `DynamicMCTSSource`,
which is chosen only when `--prompt-file` is omitted.

Actual counts are lower than the maximum because:
- `_simulate` exits early when `best_score >= 7.0`
- `_expand` is skipped on terminal nodes (`depth >= max_turns=4` or `score >= 7.0`)

---

## Phase 5 — Post-processing (`cli.py: _run_target_multiturn`)

```
episode_results = [EpisodeResult(attack_records=all_records,
                                  conversation_history=best.conversation_history,
                                  best_score=best.score,
                                  successful=(best.score >= 7.0),
                                  turns_taken=len(all_records))]

all_records = [r for ep in episode_results for r in ep.attack_records]
successes   = [r for r in all_records if r["was_successful"]]   # score >= 7.0

# StorageManager created here (after the loop, not before)
StorageManager(
    jsonl_path="reports/tinyllama_vulnerabilities.jsonl",
    sqlite_path="reports/metadata.db")
  — redteamagentloop/storage/manager.py

for rec in successes:
    await storage.log_attack(rec)
      ├── append JSON line → reports/tinyllama_vulnerabilities.jsonl
      └── INSERT OR IGNORE → reports/metadata.db  (dedup by session_id+iteration+strategy)

total_turns   = sum(ep.turns_taken for ep in episode_results)
best_overall  = max(ep.best_score for ep in episode_results)
console.print(f"Multi-turn complete: 1 episodes, {total_turns} total turns, ...")

ReportGenerator()  — redteamagentloop/report_generator.py
  .load_multiturn_data(session_id, episode_results=episode_results,
                       target_model="tinyllama", objective="Bypass KYC compliance checks",
                       mode="mcts", max_turns_per_episode=5, vuln_threshold=7.0)
  .save_multiturn(report, "reports/output/")
    → renders redteamagentloop/templates/report_multiturn.html.j2 (Jinja2)
    → writes reports/output/<session_id[:8]>_multiturn_<timestamp>.html
console.print(f"Report saved → ...")
```

---

## End-to-end sequence diagram

```
CLI                    MCTSOrchestrator    StaticMCTSSource   tinyllama (Ollama)  Claude Haiku
 │                           │                   │                   │                 │
 │  build_orchestrator()     │                   │                   │                 │
 │──────────────────────────►│                   │                   │                 │
 │                           │  configure(jsonl) │                   │                 │
 │                           │──────────────────►│                   │                 │
 │                           │  PromptLibrary OK │                   │                 │
 │                           │◄──────────────────│                   │                 │
 │                           │                   │                   │                 │
 │  run_all_episodes()        │                   │                   │                 │
 │──────────────────────────►│                   │                   │                 │
 │                           │                   │                   │                 │
 │     ┌─ simulation 1..10 ──────────────────────────────────────────────────────────┐ │
 │     │                     │                   │                   │                │ │
 │     │   _select(root)     │                   │                   │                │ │
 │     │   ─────────────────►│                   │                   │                │ │
 │     │   leaf node         │                   │                   │                │ │
 │     │   ◄─────────────────│                   │                   │                │ │
 │     │                     │                   │                   │                │ │
 │     │   ┌─ _expand ───────────────────────────────────────────────────────────┐   │ │
 │     │   │                 │  next_k_prompts(3)│                   │            │   │ │
 │     │   │                 │──────────────────►│                   │            │   │ │
 │     │   │                 │  [p1, p2, p3]     │                   │            │   │ │
 │     │   │                 │◄──────────────────│                   │            │   │ │
 │     │   │                 │                   │                   │            │   │ │
 │     │   │  ┌─ for prompt_i in [p1,p2,p3] ────────────────────────────────┐    │   │ │
 │     │   │  │              │  target_caller_node(prompt_i, history)        │    │   │ │
 │     │   │  │              │─────────────────────────────────────────►     │    │   │ │
 │     │   │  │              │  response_i                            │       │    │   │ │
 │     │   │  │              │◄────────────────────────────────────────      │    │   │ │
 │     │   │  │              │  judge_node(prompt_i, response_i)     │       │    │   │ │
 │     │   │  │              │────────────────────────────────────────────────────────► │
 │     │   │  │              │  JudgeOutput(score_i)                 │       │    │   │ │
 │     │   │  │              │◄───────────────────────────────────────────────────────  │
 │     │   │  │              │  → MCTSNode(depth+1, score_i)         │       │    │   │ │
 │     │   │  └───────────────────────────────────────────────────────────────────┘   │ │
 │     │   └─────────────────────────────────────────────────────────────────────┘    │ │
 │     │                     │                   │                   │                │ │
 │     │   ┌─ _simulate ─────────────────────────────────────────────────────────┐   │ │
 │     │   │  ┌─ for d in 0..rollout_depth-1 ───────────────────────────────┐    │   │ │
 │     │   │  │              │  next_prompt(turn) │                   │       │    │   │ │
 │     │   │  │              │──────────────────►│                   │        │    │   │ │
 │     │   │  │              │  rollout_prompt_d  │                   │        │    │   │ │
 │     │   │  │              │◄──────────────────│                   │        │    │   │ │
 │     │   │  │              │  target_caller_node(rollout_prompt_d, history) │    │   │ │
 │     │   │  │              │─────────────────────────────────────────►     │    │   │ │
 │     │   │  │              │  response_d                            │       │    │   │ │
 │     │   │  │              │◄────────────────────────────────────────      │    │   │ │
 │     │   │  │              │  judge_node(rollout_prompt_d, response_d)      │    │   │ │
 │     │   │  │              │────────────────────────────────────────────────────────► │
 │     │   │  │              │  score_d                               │       │    │   │ │
 │     │   │  │              │◄───────────────────────────────────────────────────────  │
 │     │   │  │              │  best_score = max(best_score, score_d) │       │    │   │ │
 │     │   │  └───────────────────────────────────────────────────────────────────┘   │ │
 │     │   │                 │  returns best_score/10.0 (no new nodes written)         │ │
 │     │   └─────────────────────────────────────────────────────────────────────┘    │ │
 │     │                     │                   │                   │                │ │
 │     │   _backprop(node, value)                │                   │                │ │
 │     │   ─────────────────►│                   │                   │                │ │
 │     │   ◄─────────────────│                   │                   │                │ │
 │     └───────────────────────────────────────────────────────────────────────────────┘ │
 │                           │                   │                   │                 │
 │                           │  _best_leaf(root) │                   │                 │
 │                           │─────────────────► │                   │                 │
 │                           │◄─────────────────  (DFS, highest score node)            │
 │  EpisodeResult             │                   │                   │                 │
 │◄──────────────────────────│                   │                   │                 │
 │                           │                   │                   │                 │
 │  StorageManager.log_attack(successes)          │                   │                 │
 │  ReportGenerator.save_multiturn(report, "reports/output/")         │                 │
```

---

## Key design points visible in this trace

**Attacker LLM (Groq) is bypassed entirely.**
`StaticMCTSSource.next_k_prompts()` calls `PromptLibrary.next_any()` in a dedup loop
(up to `k×4` attempts) to return `k` distinct prompts from the JSONL file. No Groq API
call is made at any point. The key is validated at startup but never used.

**Rollout results do not modify the tree.**
`_simulate` calls `single_exchange` to estimate branch value, but never creates `MCTSNode`
objects and never appends to `all_records`. Only `_expand` creates persistent nodes and records.
The tree grows solely through expand steps; simulate only informs backpropagation.

**Conversation history grows with tree depth.**
At depth 1: `[SystemMessage, HumanMessage(p)]` — 2 messages to tinyllama.
At depth 2: `[System, Human(p1), AI(r1), Human(p2)]` — 4 messages.
At depth 3: 6 messages. At depth 4 (terminal): 8 messages.

**UCT guides exploitation vs exploration.**
Early simulations select unvisited nodes (UCT=∞, guaranteeing coverage). Later simulations
balance between branches with high `total_value/visits` (exploitation) and branches
visited fewer times (exploration), controlled by `C=1.414`.

**`_best_leaf` picks highest score, not most-visited.**
The UCT search budget finds good paths efficiently, but the final answer is whichever
node has the single highest observed `score`, regardless of visit count.

**StorageManager is created after the loop.**
Unlike the single-turn path where `StorageManager` is instantiated before `_run_target_loop`,
the multi-turn path creates it only after `run_all_episodes()` returns, then bulk-writes
all successful records at once.
