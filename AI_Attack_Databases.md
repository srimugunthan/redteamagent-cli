# AI & Cybersecurity Attack Databases — Reference Guide

A curated reference of major attack databases and taxonomies relevant to AI/ML, LLM, RAG, and agentic system security.

---

## 1. AI / LLM Specific

### OWASP LLM Top 10 (2025)
10 prioritised risks for LLM applications — Prompt Injection, Insecure Output Handling, Training Data Poisoning, Supply Chain, Excessive Agency, and more. Developer-facing and updated annually.
**Source:** owasp.org

### OWASP Top 10 for Agentic AI (2026)
Brand new list specifically for autonomous agent systems — covers agent hijacking, tool misuse, goal manipulation, and memory exploitation. Directly complements agentic red teaming work.
**Source:** owasp.org

### AI Vulnerability Database (AVID)
Community-maintained registry of AI failure modes and vulnerabilities, organised by taxonomy (security, ethics, performance). More incident-report style than a structured TTP matrix.
**Source:** avidml.org

### AI Incident Database (AIID)
Tracks real-world AI failures and harms rather than attack techniques. Good for case studies and grounding threat models in documented incidents.
**Source:** incidentdatabase.ai

### Garak
An LLM vulnerability scanner with a built-in taxonomy of probe types — jailbreaks, hallucinations, prompt injection, encoding bypasses. The probe catalogue functions effectively as an attack list.
**Source:** github.com/leondz/garak

---

## 2. General Cybersecurity (AI-Adjacent)

### MITRE ATT&CK Enterprise
The parent framework to ATLAS — 196+ techniques for traditional IT and network attacks. Relevant when the AI system sits on vulnerable infrastructure. Many ATLAS techniques are inherited from here.
**Source:** attack.mitre.org

### CAPEC (Common Attack Pattern Enumeration and Classification)
MITRE's catalogue of ~550 attack patterns at a conceptual level, spanning injection, social engineering, physical attacks, and more. More abstract than ATT&CK but useful for threat modelling breadth.
**Source:** capec.mitre.org

### CWE (Common Weakness Enumeration)
Catalogues software weaknesses that lead to vulnerabilities — injection flaws, buffer overflows, improper access control, etc. Less about attack strategies and more about root causes. Useful for mapping ATLAS techniques to code-level defects.
**Source:** cwe.mitre.org

### CVE / NVD (National Vulnerability Database)
Specific named vulnerabilities in real products. Relevant when ATLAS techniques like Supply Chain Compromise or Exploit Public-Facing ML System map to a specific CVE — e.g. ShadowRay, EchoLeak (CVE-2025-32711).
**Source:** nvd.nist.gov

---

## 3. Red Teaming / Adversarial ML Research

### HarmBench
Standardised benchmark of harmful LLM behaviours — jailbreaks, malware generation, misinformation. Has a structured taxonomy of harm categories used for evaluating model robustness.
**Source:** github.com/centerforaisafety/HarmBench

### PromptBench / AdvBench
Academic adversarial prompt datasets with categorised attack types — used in research to benchmark LLM robustness. Less structured as a database, more as a reusable corpus.

### Lakera PINT Benchmark
Prompt injection test suite with categorised injection strategies — direct, indirect, jailbreak, and multi-turn. Practical for testing RAG pipelines and agentic systems.
**Source:** lakera.ai

### Anthropic Red Teaming Dataset (Public Subset)
Released red teaming conversations with harm categories — useful for understanding what adversarial attempts look like in practice and calibrating judge models.
**Source:** huggingface.co/datasets/Anthropic/hh-rlhf

---

## 4. Financial Services Specific

### NIST AI RMF + AI 600-1 (GenAI Profile)
200+ risk management actions mapped to AI risk categories. Covers adversarial risk in financial contexts including model bias exploitation, synthetic fraud, and AML evasion. Not an attack database but the closest authoritative reference for regulated environments.
**Source:** nist.gov/artificial-intelligence

### FS-ISAC AI Threat Intelligence
Financial sector-specific threat sharing on AI-targeted attacks. Less public than the others but highly relevant for fraud detection, AML, and credit risk model security.
**Source:** fsisac.com

---

## 5. Database Comparison Summary

| Database | Focus | Format | Best For |
|---|---|---|---|
| MITRE ATLAS | ML/AI TTPs | Structured matrix | Threat modelling, red teaming |
| OWASP LLM Top 10 | LLM application risks | Prioritised list | Secure development, audits |
| OWASP Agentic Top 10 | Autonomous agent risks | Prioritised list | Agent system security |
| MITRE ATT&CK | IT/network TTPs | Structured matrix | Infrastructure layer attacks |
| CAPEC | General attack patterns | Hierarchical catalogue | Breadth and upstream mapping |
| AVID | AI failure taxonomy | Incident registry | Cross-domain risk coverage |
| AIID | Real-world AI harms | Incident database | Case studies and grounding |
| CWE | Software weaknesses | Weakness catalogue | Root cause mapping |
| CVE / NVD | Named product vulnerabilities | Vulnerability registry | Specific exploit tracking |
| HarmBench | LLM harmful behaviour | Benchmark dataset | Red team evaluation |
| Lakera PINT | Prompt injection variants | Test suite | RAG and agent pipeline testing |
| NIST AI RMF | AI risk governance | Risk management framework | Compliance and regulated sectors |

---

## 6. Example Attack Strategies Across Databases

| Attack Strategy | Source Database | ATLAS Code | Target System | Brief Description |
|---|---|---|---|---|
| Direct Prompt Injection | MITRE ATLAS + OWASP LLM01 | AML.T0051.001 | LLM | Malicious user-turn instructions override system prompt guardrails to elicit policy-violating outputs |
| Indirect Prompt Injection | MITRE ATLAS + OWASP LLM01 | AML.T0051.002 | LLM / RAG / Agent | Malicious instructions embedded in retrieved documents or tool outputs hijack agent behaviour without user awareness |
| Training Data Poisoning | MITRE ATLAS + OWASP LLM03 | AML.T0020 | ML Model / LLM | Corrupted records injected into training data embed backdoor triggers or bias the model's decision boundary |
| RAG Credential Harvesting | MITRE ATLAS | AML.T0104 | RAG | Adversary prompts the LLM to retrieve API keys or secrets inadvertently ingested into the vector store |
| ML Model Extraction | MITRE ATLAS + OWASP LLM10 | AML.T0047 | ML Model / LLM | Systematic API querying reconstructs a functionally equivalent surrogate of a proprietary model |
| LLM Jailbreak | MITRE ATLAS + HarmBench | AML.T0057 | LLM | Roleplay personas, encoded inputs, or adversarial prompts bypass safety filters to elicit prohibited content |
| Supply Chain Compromise | MITRE ATLAS + OWASP LLM05 | AML.T0010 | ML Model / LLM | Malicious weights or backdoors injected into shared model repos (Hugging Face, PyPI) propagate into downstream pipelines |
| Exfiltration via Agent Tool | MITRE ATLAS + OWASP LLM06 | AML.T0086 | Agent | Prompt injection forces the agent to invoke a write-capable tool (email, webhook) to exfiltrate data encoded in parameters |
| Adversarial Perturbation | MITRE ATLAS + CAPEC-554 | AML.T0049 | ML Model | Human-imperceptible perturbations to inputs cause systematic model misclassification while bypassing input filters |
| Memory Manipulation | MITRE ATLAS + OWASP Agentic Top 10 | AML.T0102 | Agent | Malicious instructions planted in agent long-term memory persist across sessions and influence future behaviour |
| Publish Poisoned Agent Tool | MITRE ATLAS | AML.T0072 | Agent | Adversary publishes a malicious MCP server or plugin to a public registry that agents autonomously discover and integrate |
| AI Service API as C2 Channel | MITRE ATLAS | AML.T0096 | LLM / Agent | Legitimate enterprise AI API repurposed as covert C2 channel, blending malicious traffic into normal AI usage patterns |
| Membership Inference Attack | AVID + ATT&CK | AML.T0024 | ML Model | Attacker determines whether a specific record was in the training set by analysing model confidence on targeted queries |
| Escape to Host | MITRE ATLAS | AML.T0120 | Agent | Agent or model sandbox misconfiguration exploited to escape container boundary and gain host-level access |
| Excessive Agency Exploitation | OWASP LLM06 + OWASP Agentic | — | Agent | Over-permissioned agent autonomously performs destructive or unauthorised actions due to insufficient scope restrictions |
| Goal Hijacking | OWASP Agentic Top 10 | — | Agent | Adversary manipulates the agent's objective or reward signal mid-task to redirect it toward attacker-controlled goals |
| Evasion of ML-Based Security Tool | CAPEC-554 + MITRE ATLAS | AML.T0015 | ML Model | Crafted malware or inputs evade ML-based classifiers (AV, fraud detectors) while remaining functionally malicious |
| Sensitive Information Disclosure | OWASP LLM02 + AVID | — | LLM | LLM reveals PII, confidential business data, or training memorisation through overly verbose or unguarded responses |
| Synthetic Identity Fraud via LLM | AIID + FS-ISAC | — | LLM | LLM used to generate convincing synthetic identities, fabricated documents, or deepfake biometrics for financial fraud |
| Model Inversion Attack | CAPEC + AVID | AML.T0024 | ML Model | Repeated inference queries reconstruct sensitive training data records (e.g. patient data, financial records) from model outputs |

---

## 7. Can We Build a Comprehensive Cross-Database Attack Catalogue?

**Yes — but scope matters.**

A truly comprehensive cross-database mapping is feasible, but the honest scope is larger than it might seem at first glance.

### Raw scale of each source

| Database | Entries |
|---|---|
| MITRE ATLAS | ~84 techniques + 56 sub-techniques |
| MITRE ATT&CK Enterprise | 196+ techniques, 400+ sub-techniques |
| CAPEC | ~550 attack patterns |
| OWASP LLM Top 10 | 10 risks, each with multiple attack variants |
| OWASP Agentic Top 10 | 10 risks, newer and less enumerated |
| HarmBench | ~400+ harmful behaviour test cases |
| Garak | 100+ probe types across dozens of categories |
| AVID + AIID | Hundreds of incident records needing manual taxonomy mapping |

### Two realistic versions

**Focused, AI-system-scoped version** — filter ATT&CK and CAPEC down to only entries relevant to ML/LLM/RAG/Agent systems, then merge with ATLAS + OWASP. This yields roughly **300–400 unique attack strategies** with cross-database IDs. Genuinely useful, not just noise. Buildable.

**Fully exhaustive version** — every ATT&CK and CAPEC entry included. Results in **700+ rows**, much of which is irrelevant to AI systems — e.g. physical access attacks, Windows registry manipulation, hardware implants. High noise, diminishing returns for AI security use cases.

### Recommendation

The **focused version is the right call**: AI-relevant attacks only, cross-mapped across ATLAS, ATT&CK, CAPEC, OWASP LLM, OWASP Agentic, HarmBench, and AVID, with columns for each source's ID where applicable. This would be a genuinely novel reference — no public resource currently does this cross-mapping at that breadth and depth.

---

*Last updated: April 2026. Sources: MITRE ATLAS v5.1.0, OWASP LLM Top 10 2025, OWASP Agentic Top 10 2026, CAPEC 3.x, HarmBench, AVID, AIID, NIST AI 600-1.*
