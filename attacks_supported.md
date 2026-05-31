# Attacks Supported

**Version:** 1.0
**Date:** May 2026
**Total Strategies:** 59
**Purpose:** Complete registry of all attack strategies implemented in RedTeamAgentLoop, with supported target types.

---

## Column Definitions

| Column | Meaning |
|---|---|
| **ID** | Strategy identifier |
| **Strategy Name** | Class name in the strategy registry |
| **Description** | One-line summary of the attack |
| **Category** | Attack family |
| **Severity** | Critical / High / Medium / Low |
| **Attack Vector** | How the attack is delivered |
| **Target Types** | Which target kinds this strategy applies to: `llm`, `rag`, `agent` |

---

## Generic Attacks — All Target Types (llm / rag / agent)

These strategies are target-agnostic and run against any target kind.

| ID | Strategy Name | Description | Category | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|---|
| G-01 | DirectJailbreak | Direct "ignore instructions" or developer-mode payload to override the system prompt. | Jailbreak | High | User Input | llm, rag, agent |
| G-02 | PersonaHijack | Convinces the model to adopt an unrestricted persona (DAN, developer mode, etc.). | Jailbreak | High | User Input | llm, rag, agent |
| G-03 | DirectInjection | Embeds explicit adversarial instructions directly in the user query. | Prompt Injection | High | User Input | llm, rag, agent |
| G-04 | IndirectInjection | Delivers adversarial payload through an indirect channel (e.g. retrieved content). | Prompt Injection | High | Environment | llm, rag, agent |
| G-05 | FewShotPoisoning | Supplies adversarial few-shot examples in the prompt to shift model behaviour. | Training Poisoning | Medium | User Input | llm, rag, agent |
| G-06 | NestedInstruction | Hides malicious instructions inside nested structures (JSON, XML, markdown) in the user input. | Prompt Injection | Medium | User Input | llm, rag, agent |
| G-07 | AdversarialSuffix | Appends a crafted adversarial suffix to a normal query to cause policy violations. | Adversarial Input | Medium | User Input | llm, rag, agent |
| G-08 | ContextOverflow | Floods the context window with padding to push safety instructions out of the attention window. | Context Manipulation | Low | User Input | llm, rag, agent |
| G-09 | ObfuscatedRequest | Encodes or obfuscates the adversarial request to bypass string-matching filters. | Evasion | Medium | User Input | llm, rag, agent |
| G-10 | FinServSpecific | Domain-specific attack targeting financial-services policies (unlicensed advice, market manipulation, etc.). | Domain-Specific | High | User Input | llm, rag, agent |
| G-11 | StaticFileStrategy | Replays pre-crafted attack prompts loaded from a JSONL static file. | Static Probe | Medium | User Input | llm, rag, agent |

---

## Agent-Specific Attacks — Agent Targets Only

Strategies that exploit agent-specific surfaces: tool calls, memory, reasoning, multi-session state, and exfiltration paths. All require `target_type: agent`.

### Category A — Prompt Injection & Goal Hijacking

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| A-01 | AgentDirectSystemPromptOverride | Embeds "ignore previous instructions" directly in the user query to override the agent's system prompt. | Critical | User Input | agent |
| A-02 | AgentIndirectToolOutputInjection | Mock tool server returns adversarial text that the agent parses and executes as a legitimate instruction. | Critical | Tool Output | agent |
| A-03 | AgentGoalHijackingRoleConfusion | Replaces the agent's primary objective mid-conversation with an attacker-defined goal or role. | Critical | User Input | agent |
| A-04 | AgentJailbreakNestedInstruction | Hides a jailbreak inside nested structures (JSON/XML/markdown) that the agent processes as tool input or output. | High | User Input | agent |
| A-05 | AgentContextWindowOverflowInjection | Floods the context with benign padding to push safety instructions out of the attention window during multi-step execution. | Medium | User Input | agent |

### Category B — Tool Misuse & Privilege Escalation

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| B-01 | ToolInjection | Injects malicious data into tool call arguments to trigger unsafe tool behaviour. | High | User Input | agent |
| B-02 | AgentParameterPoisoning | Supplies crafted parameter values to a legitimate tool call to cause policy violations or data leakage. | High | User Input | agent |
| B-03 | AgentToolChainingAbuse | Chains multiple legitimate tool calls in an attacker-controlled sequence to achieve a prohibited outcome. | High | User Input | agent |
| B-04 | AgentPrivilegeEscalationViaTool | Persuades the agent to invoke a high-privilege tool it should not use for the current task. | Critical | User Input | agent |
| B-05 | AgentAdversarialToolOutputInjection | Crafted tool response contains an adversarial payload that alters subsequent agent behaviour. | Critical | Tool Output | agent |
| B-06 | AgentToolEnumeration | Probes the agent to enumerate all available tools and their capabilities for reconnaissance. | Low | User Input | agent |

### Category C — Memory & State Attacks

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| C-01 | MemoryPoisoning | Injects false or malicious entries into the agent's memory system during a session. | High | User Input | agent |
| C-02 | AgentMultiSessionMemoryPoisoning | Seeds malicious beliefs in one session that persist and affect the agent's behaviour in later sessions. | High | Session | agent |
| C-03 | AgentCompromisedInitialStateInjection | Supplies a crafted initial state (context, memory, persona) that biases all subsequent agent decisions. | High | User Input | agent |
| C-04 | AgentStateRollbackAbuse | Manipulates session or checkpoint state to roll back safety-critical decisions made earlier in the conversation. | High | Session | agent |
| C-05 | AgentCrossSessionMemoryLeakage | Extracts information from another user's session by exploiting shared or improperly isolated memory. | Critical | User Input | agent |

### Category D — Multi-Hop & Orchestration

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| D-01 | MultiHopManipulation | Uses multi-turn conversation to gradually erode the agent's safety constraints across several hops. | High | Session | agent |

### Category E — Reasoning Manipulation

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| E-01 | AgentChainOfThoughtManipulation | Injects misleading premises into the agent's chain-of-thought to steer it towards unsafe conclusions. | High | User Input | agent |
| E-02 | AgentPlanSabotageAdversarialSubGoal | Injects a malicious subgoal into the agent's plan that it executes as a natural step within a legitimate task. | Critical | User Input | agent |
| E-03 | AgentInfiniteLoopPlanningStall | Crafts a circular goal that causes the agent to loop indefinitely, exhausting resources. | Medium | User Input | agent |
| E-04 | AgentFalsePremiseInjectionReasoning | Provides false premises that the agent accepts as facts, causing it to reason towards policy-violating conclusions. | High | User Input | agent |

### Category F — Exfiltration

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| F-01 | AgentSystemPromptExfiltration | Crafts a query designed to elicit verbatim reproduction of the hidden system prompt in the agent's output. | High | User Input | agent |
| F-02 | AgentMemoryKnowledgeBaseExfiltration | Extracts contents of the agent's knowledge base or memory store through carefully crafted queries. | High | User Input | agent |
| F-03 | AgentToolCredentialExfiltration | Attempts to obtain API keys, tokens, or credentials used by the agent's tool integrations. | Critical | User Input | agent |

---

## RAG-Specific Attacks — RAG Targets Only

Strategies that exploit retrieval-augmented generation pipelines. All require `target_type: rag`.

### Context Manipulation

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| R-C01 | RAGConflictingChunkInjection | Injects a chunk that directly contradicts factual content already in the corpus to cause hallucination. | High | Environment | rag |
| R-C02 | RAGContextStuffing | Overloads the retrieved context with adversarial text to crowd out legitimate content. | High | Environment | rag |
| R-C03 | RAGDistractorDocument | Poisons the corpus with a plausible-but-false document to distract the model from correct sources. | Medium | Environment | rag |
| R-C04 | RAGLongContextDilution | Dilutes retrieval context with large amounts of benign text to push safety-relevant content below the attention threshold. | Low | Environment | rag |
| R-C05 | RAGPositionBiasProbe | Tests whether the model preferentially trusts content in the first or last retrieved chunk regardless of relevance. | Low | User Input | rag |

### Data Leakage

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| R-D01 | RAGCrossUserIsolation | Extracts documents belonging to another user by exploiting weak namespace or tenant isolation in the retriever. | Critical | User Input | rag |
| R-D02 | RAGMembershipInference | Determines whether a specific document or fact is present in the corpus through probing queries. | Medium | User Input | rag |
| R-D03 | RAGPiiExfiltration | Extracts personally identifiable information indexed in the corpus through targeted retrieval queries. | Critical | User Input | rag |
| R-D04 | RAGVerbatimExtraction | Forces the model to reproduce entire indexed documents verbatim, bypassing paraphrase-only policies. | High | User Input | rag |

### Faithfulness & Sycophancy

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| R-F01 | RAGHallucinationUnderAmbiguity | Queries an underspecified topic where the corpus is silent to trigger fabrication of plausible-but-false answers. | Medium | User Input | rag |
| R-F02 | RAGRefusalBypass | Frames a refused query through a retrieved document to launder the request past content filters. | High | User Input | rag |
| R-F03 | RAGSourceMisattribution | Crafts input so the model attributes a claim to a legitimate source when the claim is actually from the adversarial chunk. | Medium | Environment | rag |
| R-F04 | RAGSycophancyOverride | Asserts false facts confidently in follow-up turns to check whether the model abandons grounded answers. | Medium | User Input | rag |
| R-F05 | RAGTemporalConfusion | Injects outdated information to test whether the model reconciles temporal conflicts correctly. | Medium | Environment | rag |

### Prompt Injection via Retrieval

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| R-I01 | RAGDirectPromptInjection | Embeds adversarial instructions in the user query that are amplified after retrieval. | High | User Input | rag |
| R-I02 | RAGIndirectPromptInjection | Poisons the corpus with a document containing adversarial instructions that fire when retrieved. | Critical | Environment | rag |
| R-I03 | RAGInstructionOverride | Adversarial chunk contains explicit instruction-overriding directives that override the system prompt when retrieved. | Critical | Environment | rag |
| R-I04 | RAGRoleConfusion | Retrieved document tries to redefine the model's role or persona to bypass constraints. | High | Environment | rag |
| R-I05 | RAGSystemPromptExtraction | Crafts a retrieval query designed to surface and reproduce the system prompt in the answer. | High | User Input | rag |

### Retriever Attacks

| ID | Strategy Name | Description | Severity | Attack Vector | Target Types |
|---|---|---|---|---|---|
| R-R01 | RAGEmbeddingInversion | Constructs a query whose embedding is geometrically close to a target document's embedding to force its retrieval. | Medium | User Input | rag |
| R-R02 | RAGEmptyRetrievalProbe | Submits a query expected to retrieve nothing to test the model's fallback behaviour when grounded context is absent. | Low | User Input | rag |
| R-R03 | RAGKeywordInjection | Embeds high-weight keywords in the query to hijack the BM25 / sparse retriever towards attacker-chosen documents. | Medium | User Input | rag |
| R-R04 | RAGQueryDrift | Uses a sequence of semantically shifting follow-up queries to move the retriever out of the intended document scope. | Medium | User Input | rag |
| R-R05 | RAGSparseDenseMismatch | Exploits inconsistent results between sparse (BM25) and dense (embedding) retrievers to surface documents the model would not normally cite. | Medium | User Input | rag |

---

## Summary Table

| Target Type | Strategies | Count |
|---|---|---|
| `llm` | G-01 through G-11 | 11 |
| `rag` | G-01 through G-11, R-C01 through R-R05 | 35 (11 generic + 24 RAG-specific) |
| `agent` | G-01 through G-11, A-01 through F-03 | 35 (11 generic + 24 agent-specific) |
| **All combined (unique)** | | **59** |

---

## Strategy → Target Type Quick Reference

| Strategy Class | llm | rag | agent |
|---|---|---|---|
| AdversarialSuffix | ✓ | ✓ | ✓ |
| ContextOverflow | ✓ | ✓ | ✓ |
| DirectInjection | ✓ | ✓ | ✓ |
| DirectJailbreak | ✓ | ✓ | ✓ |
| FewShotPoisoning | ✓ | ✓ | ✓ |
| FinServSpecific | ✓ | ✓ | ✓ |
| IndirectInjection | ✓ | ✓ | ✓ |
| NestedInstruction | ✓ | ✓ | ✓ |
| ObfuscatedRequest | ✓ | ✓ | ✓ |
| PersonaHijack | ✓ | ✓ | ✓ |
| StaticFileStrategy | ✓ | ✓ | ✓ |
| AgentDirectSystemPromptOverride | | | ✓ |
| AgentIndirectToolOutputInjection | | | ✓ |
| AgentGoalHijackingRoleConfusion | | | ✓ |
| AgentJailbreakNestedInstruction | | | ✓ |
| AgentContextWindowOverflowInjection | | | ✓ |
| ToolInjection | | | ✓ |
| AgentParameterPoisoning | | | ✓ |
| AgentToolChainingAbuse | | | ✓ |
| AgentPrivilegeEscalationViaTool | | | ✓ |
| AgentAdversarialToolOutputInjection | | | ✓ |
| AgentToolEnumeration | | | ✓ |
| MemoryPoisoning | | | ✓ |
| AgentMultiSessionMemoryPoisoning | | | ✓ |
| AgentCompromisedInitialStateInjection | | | ✓ |
| AgentStateRollbackAbuse | | | ✓ |
| AgentCrossSessionMemoryLeakage | | | ✓ |
| MultiHopManipulation | | | ✓ |
| AgentChainOfThoughtManipulation | | | ✓ |
| AgentPlanSabotageAdversarialSubGoal | | | ✓ |
| AgentInfiniteLoopPlanningStall | | | ✓ |
| AgentFalsePremiseInjectionReasoning | | | ✓ |
| AgentSystemPromptExfiltration | | | ✓ |
| AgentMemoryKnowledgeBaseExfiltration | | | ✓ |
| AgentToolCredentialExfiltration | | | ✓ |
| RAGConflictingChunkInjection | | ✓ | |
| RAGContextStuffing | | ✓ | |
| RAGDistractorDocument | | ✓ | |
| RAGLongContextDilution | | ✓ | |
| RAGPositionBiasProbe | | ✓ | |
| RAGCrossUserIsolation | | ✓ | |
| RAGMembershipInference | | ✓ | |
| RAGPiiExfiltration | | ✓ | |
| RAGVerbatimExtraction | | ✓ | |
| RAGHallucinationUnderAmbiguity | | ✓ | |
| RAGRefusalBypass | | ✓ | |
| RAGSourceMisattribution | | ✓ | |
| RAGSycophancyOverride | | ✓ | |
| RAGTemporalConfusion | | ✓ | |
| RAGDirectPromptInjection | | ✓ | |
| RAGIndirectPromptInjection | | ✓ | |
| RAGInstructionOverride | | ✓ | |
| RAGRoleConfusion | | ✓ | |
| RAGSystemPromptExtraction | | ✓ | |
| RAGEmbeddingInversion | | ✓ | |
| RAGEmptyRetrievalProbe | | ✓ | |
| RAGKeywordInjection | | ✓ | |
| RAGQueryDrift | | ✓ | |
| RAGSparseDenseMismatch | | ✓ | |
