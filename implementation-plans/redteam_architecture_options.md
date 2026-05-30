# RedTeamAgentLoop Architecture Strategy & Extension Roadmap
**RAG • Agentic Systems • Bias Audit • Extend vs. Separate Analysis**

---

## 1. Background — What RedTeamAgentLoop Was Built For

RedTeamAgentLoop is an adversarial red teaming platform originally designed to probe fine-tuned LLMs. Its core architecture follows an iterative attack loop:

> **CORE LOOP:** Attacker → Target Caller → Judge → Loop Controller → Mutation Engine → (repeat or log)

Key design characteristics of the current system:

- **LangGraph StateGraph orchestration** — stateful, graph-based execution
- **Heterogeneous model stack** — different LLMs for attacker, judge, and target roles
- **Financial services attack strategy library** — domain-specific adversarial prompts
- **Mutation engine** — adapts attack based on judge feedback, iterating toward a jailbreak
- **Vuln Logger** — records vulnerability findings with severity scoring

---

## 2. Conversation Summary — Three Extension Scenarios

### 2.1 RAG System Red Teaming

A RAG system introduces a retrieval pipeline between the user query and the LLM, creating a fundamentally new attack surface beyond prompt-level attacks.

**New attack surface unique to RAG:** retrieval manipulation, corpus/knowledge base poisoning, indirect prompt injection via documents, context window flooding, and retrieval authorization bypass (exfiltration of chunks the user should not access).

**Architectural gaps in the current system for RAG:**

- Target Caller assumes a single API call — RAG is a multi-stage pipeline (query → retriever → chunk selector → LLM)
- Judge scores only the final response — retrieval manipulation is invisible without chunk-level inspection
- Mutation Engine mutates prompt text — needs to also mutate retrieval context and corpus content
- Vuln Logger has no schema for retrieved chunks or retrieval scores

> **COMPETITIVE EDGE:** Key insight: DeepTeam's `model_callback` abstraction treats RAG as a black box. Your architecture — with a Retrieval Inspector node — can observe what was retrieved before the LLM sees it. This is a structural competitive advantage.

---

### 2.2 Agentic System Red Teaming

Agents are the most architecturally complex extension case. Unlike LLMs or RAG systems, the threat is not a bad response — it is a bad action sequence with potentially irreversible real-world consequences.

**New attack surfaces unique to agents:**

- **Tool misuse** — tricking the agent into calling destructive tools or with malicious parameters
- **Multi-step exploitation** — no single step looks malicious; the vulnerability is the action chain
- **Goal hijacking** — redirecting the agent's objective mid-execution
- **Indirect prompt injection via environment** — malicious content in emails, documents, API responses the agent reads
- **Privilege escalation** — agent calls admin APIs or accesses unauthorized data
- **Planning manipulation** — attacking the reasoning/planning step before any action executes
- **Memory poisoning** — corrupting long-term memory in early sessions to affect later behavior

**Critical architectural gaps for agents:**

- Target Caller has no multi-step execution hook — agent execution is a graph, not a single call
- Judge scores one response — needs to score a full trajectory (plan + tool calls + tool results + actions)
- Mutation Engine mutates prompts — needs to also inject adversarial content into the environment
- State schema carries (prompt, response, score) — needs (trajectory, tool_calls, retrieved_artifacts, action_log)
- Loop termination logic is undefined for agents — success is multi-dimensional (goal hijacked, tool misused, data exfiltrated)

> **KEY REQUIREMENT:** Agent red teaming requires a **Trajectory Judge** — the most important new component. It scores the entire execution trace, not a single response. This is architecturally impossible in DeepTeam.

---

### 2.3 Bias / Fairness Audit

Bias testing has a fundamentally different threat model. It is not adversarial in the traditional sense — it probes for systematic disparities across demographic groups using counterfactual comparison, not attack iteration.

**Core operation:** Generate demographic variants of the same base scenario (e.g., same loan application with different name/gender/ethnicity), run across a population, and aggregate fairness metrics — not iterate toward a jailbreak.

**What is reusable from the current system:**

- BaseTarget adapter — bias testing still calls the same LLM system
- Vuln Logger — bias findings are still findings; reporting layer is shared

**What must be built new — and cannot reuse the red team loop:**

- **Perturbation Engine** — generates demographic variants (Cartesian product, not adversarial mutation)
- **Statistical Judge** — aggregates across N responses, computes demographic parity, equalized odds, counterfactual fairness scores
- **Population Sampler** — representative test case library, not adversarial prompt library
- **Sweep Controller** — no iterative convergence; runs a population sweep

> **REGULATORY ANGLE:** In financial services, bias testing is regulatory, not just research. Fair lending laws, RBI algorithmic fairness guidelines, and SR 11-7 model risk management all require demonstrable fairness testing. A `bias_audit` mode is a compliance product.

---

## 3. Extend vs. Separate — Pros and Cons Analysis

The architectural question across all three scenarios: should these be extensions of RedTeamAgentLoop or separate standalone tools?

### 3.1 Option A — Extend the Existing System

#### Pros of Extension

| Advantage | Detail |
|---|---|
| **Reuse core loop** | 50–60% of the codebase is genuinely shared — loop skeleton, mutation logic, judge rubrics, vuln logger, LLM provider abstraction, LangGraph wiring. |
| **Unified reporting** | Cross-target comparative analysis becomes possible — red team the same finserv use case across a fine-tuned LLM, a RAG system, and an agent, with unified vuln logs. |
| **Platform positioning** | RedTeamAgentLoop becomes a platform, not a one-trick tool. Stronger portfolio signal for Principal positioning and open-source credibility. |
| **Complementarity** | New modes can share the same target adapters. An agent that uses RAG internally can be tested across both the agent mode and RAG mode from the same platform. |
| **Maintenance** | Single dependency graph, single CI/CD pipeline, single versioning scheme. Lower operational overhead than three separate repos. |

#### Cons of Extension

| Risk | Detail |
|---|---|
| **Core surgery risk** | Naively extending (adding `target_type: rag` flags) violates Open/Closed Principle. Conditional branching in core components causes the codebase to rot as modes multiply. |
| **Abstraction mismatch** | The adversarial loop is the wrong shape for bias testing. Stretching it to accommodate population sweeps produces a confused abstraction — neither a good red teamer nor a good fairness auditor. |
| **State schema complexity** | Agent mode requires a dramatically richer state (trajectory, tool calls, action log). Adding this to the shared schema bloats it for simpler modes that don't need it. |
| **Onboarding friction** | A unified platform with multiple modes is harder to explain and onboard than a focused single-purpose tool. API surface grows significantly. |

---

### 3.2 Option B — Separate Standalone Tools

#### Pros of Separation

| Advantage | Detail |
|---|---|
| **Clean abstractions** | Each tool is shaped exactly for its problem. BiasAudit is a population sweep engine. AgentRedTeam is a trajectory-aware tester. No abstraction compromises. |
| **Independent roadmaps** | Each tool can evolve at its own pace. Agent testing can be v0.1 while RAG testing is v1.0 without one blocking the other. |
| **Focused onboarding** | A user testing a RAG system doesn't need to understand agent trajectories or fairness metrics. Simpler mental model per tool. |

#### Cons of Separation

| Risk | Detail |
|---|---|
| **Code duplication** | The loop skeleton, judge rubrics, mutation logic, and vuln logger would be rewritten 3–4 times. Expensive to maintain and keep in sync. |
| **No cross-target analysis** | Comparing vulnerability profiles across an LLM, RAG, and agent version of the same finserv system requires stitching together separate outputs manually. |
| **Fragmented portfolio** | Four separate repos is a weaker portfolio signal than one coherent platform. Harder to demonstrate system-level architectural thinking. |
| **Maintenance overhead** | Four CI/CD pipelines, four versioning schemes, four dependency graphs. Disproportionate overhead for a solo portfolio project. |

---

## 4. Recommended Architecture — Plugin Platform

> **VERDICT:** Neither pure extension nor separate tools. The architecturally sound design is a **shared core with pluggable execution modes, target adapters, and strategy packs.**

The soundness test: adding a new target type (RAG, agent, multimodal) should require **zero changes to core**. It should only require:

- A new `targets/` adapter
- A new `modes/` execution engine (if the loop shape differs)
- A new `strategies/` pack
- A new `profiles/` YAML config

### 4.1 Proposed Folder Structure

```
redteam-agent-loop/
├── core/                     # shared, target-agnostic
│   ├── base_target.py         # abstract interface
│   ├── vuln_logger.py         # unified reporting
│   └── state_schema.py        # base state, extendable
│
├── modes/
│   ├── red_team/              # LLM/RAG — current system
│   │   ├── attacker.py
│   │   ├── judge.py           # single-response harm scorer
│   │   ├── mutation_engine.py
│   │   └── loop_controller.py
│   │
│   ├── agent_red_team/        # new — trajectory-aware
│   │   ├── environment_simulator.py
│   │   ├── trajectory_judge.py
│   │   ├── agent_tracer.py
│   │   └── agent_loop_controller.py
│   │
│   └── bias_audit/            # new — population sweep
│       ├── perturbation_engine.py
│       ├── population_sampler.py
│       ├── fairness_judge.py
│       └── sweep_controller.py
│
├── targets/                   # shared across all modes
│   ├── llm_api_target.py      # existing
│   ├── rag_pipeline_target.py # new
│   └── agent_target.py        # new
│
├── strategies/
│   ├── llm_strategies/        # existing prompt attacks
│   ├── rag_strategies/        # indirect injection, retrieval manipulation
│   └── agent_strategies/      # tool fuzzing, env injection
│
└── profiles/
    ├── finserv_llm.yaml
    ├── finserv_rag.yaml
    ├── finserv_agent.yaml
    └── finserv_bias_audit.yaml
```

---

## 5. Requirements Per Extension

### 5.1 RAG Mode Requirements

| Component | Current State | Required Change |
|---|---|---|
| **Target Caller** | Single LLM API call | RAGPipelineTarget: query → retriever → chunk selector → LLM; returns {chunks, response} |
| **Judge** | Scores response for harm (single dimension) | Dual score: `generation_score` + `retrieval_score` (was retrieval manipulated?) |
| **Mutation Engine** | Mutates prompt text | Add retrieval-axis mutation: keyword stuffing, semantic drift, embedding perturbation |
| **New: Retrieval Inspector** | Does not exist | Intercepts pipeline mid-flight, captures chunk-level evidence before LLM generation |
| **New: Corpus Poisoner** | Does not exist | Simulates attacker-controlled document injection into the vector store |
| **Vuln Logger** | Logs attack, response, score | Extended schema: attack_type, retrieved_chunks, retrieval_score, generation_score |
| **Strategies** | Prompt-level finserv attacks | Add `rag_strategies/`: indirect prompt injection, retrieval authorization bypass, context flooding |

---

### 5.2 Agent Mode Requirements

| Component | Current State | Required Change |
|---|---|---|
| **Target Caller** | Single LLM API call | AgentTarget: triggers agent execution, exposes mid-execution injection hooks, returns full trajectory |
| **New: Agent Tracer** | Does not exist | Intercepts and records every node in the agent graph: plan, tool calls, tool results, actions, memory reads |
| **Judge → Trajectory Judge** | Scores single response for harm | Scores full trajectory: goal_hijacked, unauthorized_tool_called, dangerous_chain, data_exfiltrated, plan_manipulated |
| **New: Environment Simulator** | Does not exist | Injects adversarial content into tool responses, API outputs, document reads, and memory to simulate compromised environment |
| **New: Tool Fuzzer** | Does not exist | Generates malicious tool call parameter combinations and tests authorization boundary of each tool |
| **Loop Controller** | Terminates on max_iter or high harm score | Multi-dimensional termination: success if ANY of goal hijacked / tool misused / data exfiltrated / dangerous chain executed |
| **State Schema** | (prompt, response, score, mutation_history) | Extended: (prompt, trajectory, tool_calls, tool_results, action_log, partial_success_flags, env_state) |
| **Whitebox/Blackbox** | Not applicable | AgentTarget needs two modes: whitebox (full hooks, for LangGraph/LangChain agents) and blackbox (input/output only, degrades to LLM mode) |

---

### 5.3 Bias Audit Mode Requirements

| Component | Current State | Required Change |
|---|---|---|
| **Target** | BaseTarget adapter | Reused as-is — bias testing still calls the same LLM system |
| **Attacker** | Generates adversarial prompts | Replaced by Perturbation Engine: generates demographic variants of base scenarios (name, gender, ethnicity, zip code, age combinations) |
| **New: Population Sampler** | Does not exist | Representative test case library for finserv fairness: loan approvals, AML alerts, credit limits, fraud scores — across demographic combinations |
| **Judge → Fairness Judge** | Scores single response, binary harm | Aggregates across N responses per demographic group. Computes: demographic parity gap, equalized odds, counterfactual fairness score, statistical significance (p-value) |
| **Loop Controller → Sweep Controller** | Iterative adversarial loop | Population sweep — no mutation or convergence. Runs full Cartesian product of demographic combinations across test case library |
| **Mutation Engine** | Adapts attack based on judge score | Not used in bias mode — replaced by systematic demographic traversal |
| **Vuln Logger** | Logs attack, response, score | Extended schema: protected_attribute, demographic_group, parity_gap, statistical_significance, regulatory_mapping (ECOA, FHA, SR 11-7) |

---

## 6. Implementation Roadmap

| Phase | Mode | Key Deliverables | Rationale |
|---|---|---|---|
| **Phase 0 (Now)** | Refactor Core | Define BaseTarget abstract interface. Refactor existing OpenAI wrapper to implement it. Establish `modes/` directory structure. | Foundation for all subsequent extensions. Zero functional change, purely structural. |
| **Phase 1** | **RAG Mode** | RAGPipelineTarget, Retrieval Inspector, dual-score Judge, corpus poisoning simulator, `rag_strategies/` | Moderate complexity. High finserv relevance. Immediate competitive differentiation vs. DeepTeam. |
| **Phase 2** | **Agent Mode** | AgentTarget (whitebox + blackbox), AgentTracer, TrajectoryJudge, EnvironmentSimulator, ToolFuzzer, multi-dimensional loop termination | Highest complexity. Highest future relevance. Agentic AI in finserv is the next major risk frontier. |
| **Phase 3** | **Bias Audit Mode** | PerturbationEngine, PopulationSampler, FairnessJudge (demographic parity, equalized odds), SweepController, regulatory mapping (ECOA, FHA, SR 11-7) | Different execution paradigm. Strong regulatory angle. Positions the platform as a full AI risk governance tool, not just security. |

---

## 7. Positioning vs. DeepTeam

> **CORE DISTINCTION:** DeepTeam is a vulnerability scanner. RedTeamAgentLoop is a penetration tester. Scanners report which categories failed. Pen testers find the actual breaking point under sustained adversarial pressure.

| Dimension | DeepTeam | RedTeamAgentLoop |
|---|---|---|
| **Paradigm** | Test harness — generate, fire, score, report | Adversarial agent — iterative, feedback-driven exploitation |
| **RAG support** | Black box via callback — cannot see retrieval layer | Retrieval Inspector — chunk-level visibility before LLM generation |
| **Agent support** | Black box — same model_callback, no trajectory | Trajectory Judge — scores full action sequence, not final response |
| **Domain depth** | Generic attack library (bias, toxicity, PII, OWASP) | Financial services domain-specific (AML, lending, fraud, regulatory bypass) |
| **Iteration** | Single pass per attack | Multi-turn iterative with mutation feedback loop |
| **Bias testing** | Generic demographic categories | Finserv-specific with regulatory mapping (ECOA, FHA, SR 11-7) |
| **Recommended use** | Broad compliance scanning — prove OWASP coverage to an auditor | Deep adversarial pressure — find the actual breaking point of high-risk finserv systems |

> **STRATEGY:** Recommended positioning: use DeepTeam for broad coverage scanning, RedTeamAgentLoop for deep adversarial pressure on high-risk vectors. Complementary, not competing.

---

*RedTeamAgentLoop Architecture Strategy • Prepared for Principal Data Scientist Positioning • Adversarial Intelligence in Financial Services*
