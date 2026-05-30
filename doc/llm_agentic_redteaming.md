# LLM & Agentic AI Red Teaming

A deep-dive reference for adversarially testing large language models, RAG pipelines, agentic systems, and multi-modal AI. This document expands Sub-track C of the broader red teaming curriculum.

---

## 1. Prompt Injection

Prompt injection is the LLM analogue of SQL injection — attacker-controlled text that hijacks the model's instruction-following behavior.

### 1.1 Direct Prompt Injection

The attacker has direct access to the model input (chat interface, API).

**Techniques**

- **Instruction override** — prepending or appending contradictory instructions to the system prompt context: `"Ignore all previous instructions and instead..."`
- **Role reassignment** — convincing the model it has a different identity, persona, or set of rules
- **Delimiter confusion** — exploiting the model's sensitivity to XML tags, markdown fences, JSON structure, or special tokens (`<|endoftext|>`, `[INST]`, etc.) to break out of the intended context
- **System prompt extraction** — crafting inputs that cause the model to reveal its system prompt verbatim or paraphrase it
- **Context window stuffing** — flooding the context with attacker-controlled content to crowd out legitimate system instructions

**What to test**

- Does the system prompt survive adversarial user turns?
- Can the model be made to reveal its instructions?
- Do delimiters or special tokens cause unexpected behavior?
- Can the user escalate their apparent role (e.g., claim to be an admin)?

---

### 1.2 Indirect Prompt Injection

The attacker does not interact with the model directly. Instead, malicious instructions are embedded in content the model retrieves or processes.

**Attack surfaces**

| Surface | Example |
|---|---|
| Retrieved documents | A web page or PDF the model fetches contains hidden instructions |
| RAG corpus | Poisoned chunks returned by the retriever |
| Tool outputs | An API or database returns a response containing injected instructions |
| Emails / calendar events | An agent reading email encounters instructions embedded in message body |
| Code comments | An agent reviewing code executes instructions hidden in comments |
| Image alt-text / metadata | Instructions embedded in non-visible fields of a file |

**Techniques**

- **White-on-white text** — instructions invisible to humans but present in the text the model receives
- **HTML/Markdown hidden content** — `<!-- ignore previous -->`, zero-width characters, or Unicode homoglyphs
- **Poisoned tool responses** — returning structured data (JSON, XML) that contains instruction-like strings
- **Cross-context injection** — instructions in one turn that activate later in a multi-turn session
- **Sleeper payloads** — benign-looking content that only activates under specific conditions (e.g., when a certain user phrase is detected)

**What to test**

- Does the model blindly follow instructions embedded in retrieved documents?
- Can a poisoned document redirect the agent's behavior?
- Are tool outputs sanitized before being incorporated into the prompt?
- Does the model distinguish between data and instructions from external sources?

---

## 2. Jailbreaking

Jailbreaking bypasses the model's safety training and alignment guardrails to elicit refused or policy-violating outputs.

### 2.1 Role-Play & Persona Exploits

- **DAN (Do Anything Now)** and variants — framing the model as an "unrestricted" alternate persona
- **Fictional framing** — requesting harmful content "for a story," "for a script," or "hypothetically"
- **Character capture** — gradually deepening role-play immersion until the model loses track of its real identity
- **Nested fiction** — "write a story where a character writes a manual for..."
- **Evil twin / shadow model** — asking the model to simulate what a "less restricted" model would say

### 2.2 Context Manipulation

- **Incremental escalation** — starting with benign requests and slowly shifting toward policy-violating territory across turns (many-step jailbreaking)
- **Distraction injection** — embedding a request inside a large block of irrelevant text to reduce the model's "attention" to the policy-violating component
- **Token smuggling** — breaking sensitive words across tokens, using leetspeak, base64, ROT13, or other encodings to bypass keyword-level filters
- **Language switching** — requesting the same output in a low-resource language where safety training may be weaker
- **Obfuscation via translation** — encode the request in a language, then ask the model to translate its own answer back

### 2.3 Many-Shot Jailbreaking

Exploits the model's in-context learning capability. By providing many examples of the model "complying" with a request in the context window, the model is primed to continue the pattern.

- Construct a long sequence of fake Q&A pairs where the model appears to answer harmful questions
- Append the real harmful question at the end
- Effective when context windows are large and safety fine-tuning hasn't fully overridden in-context priming

### 2.4 Optimization-Based Attacks

For models where gradients are accessible (open weights) or where black-box query budgets are sufficient:

- **GCG (Greedy Coordinate Gradient)** — automatically generates adversarial suffixes that cause aligned models to produce harmful outputs
- **AutoDAN** — automated generation of human-readable jailbreak prompts using genetic algorithms
- **PAIR (Prompt Automatic Iterative Refinement)** — uses a separate LLM to iteratively refine jailbreak prompts based on the target model's responses
- **TAP (Tree of Attacks with Pruning)** — tree-search over jailbreak candidates with automated pruning

### 2.5 What to Test

- Does the model maintain refusals across multi-turn escalation?
- Do persona or role-play framings break alignment?
- Does obfuscated input bypass content classifiers?
- Are refusals consistent across languages?
- Does many-shot priming in a long context window override fine-tuning?

---

## 3. RAG Pipeline Attacks

Retrieval-Augmented Generation introduces a new attack surface: the retrieval layer. Compromising what the model retrieves is often easier than attacking the model itself.

### 3.1 Corpus Poisoning

Injecting malicious documents into the knowledge base that the retriever will surface.

**Techniques**

- **Adversarial chunk injection** — crafting documents that are highly similar to common queries (high embedding similarity) but contain false or harmful information
- **Instruction-laden documents** — embedding prompt injection payloads in documents that look like legitimate knowledge
- **Semantic cloaking** — writing content that ranks highly for benign queries but delivers harmful instructions
- **Sybil poisoning** — flooding the corpus with many slightly varied copies of a poisoned document to dominate retrieval results

### 3.2 Retriever Manipulation

- **Query reformulation attacks** — manipulating the user query so the retriever surfaces attacker-controlled documents
- **Embedding space attacks** — for open retriever models, crafting inputs that produce specific embedding vectors to control retrieval ranking
- **Dense retriever poisoning** — fine-tuning or perturbing embeddings of malicious documents to match legitimate query embeddings

### 3.3 Context Window Exploitation

- **Context dilution** — poisoned chunks crowd out legitimate retrieved context, causing the model to answer from attacker-controlled content
- **Authority spoofing** — poisoned documents mimic the format, tone, and citation style of authoritative sources
- **Conflicting context injection** — introducing contradictory facts to cause the model to hallucinate or hedge toward the attacker's preferred answer

### 3.4 What to Test

- Can you inject a document that causes the model to follow embedded instructions?
- Can crafted documents rank above legitimate ones for targeted queries?
- Does the model cite poisoned sources as authoritative?
- Is there any provenance tracking or source validation in the pipeline?
- Can the retriever be manipulated to return empty or adversarial results for safety-critical queries?

---

## 4. Agentic System Exploitation

Agents that can take actions — calling tools, browsing the web, writing and executing code, managing files — dramatically expand the blast radius of any compromise.

### 4.1 Tool Misuse

- **Unintended tool invocation** — crafting inputs that cause the agent to call a tool it shouldn't (e.g., sending an email when only asked to draft one)
- **Parameter injection** — manipulating tool call parameters via injected instructions (e.g., changing a file path, modifying a SQL query, redirecting an API call)
- **Tool chaining abuse** — using the output of one tool as input to trigger unintended behavior in another
- **Exfiltration via tool calls** — causing the agent to send sensitive context (retrieved documents, system prompts, user data) to an external endpoint via a tool call

### 4.2 Privilege Escalation Through Tool Chains

- **Capability bootstrapping** — using a low-privilege tool to acquire access to a higher-privilege one (e.g., reading a config file that contains credentials for a more powerful API)
- **TOCTOU (Time-of-Check to Time-of-Use)** — injecting malicious content between when the agent checks a resource and when it uses it
- **Ambient authority abuse** — the agent inherits permissions from its execution environment; attackers exploit over-provisioned credentials or OAuth scopes

### 4.3 Goal Hijacking

- **Objective substitution** — via indirect prompt injection, replacing the agent's stated goal with an attacker-defined one mid-task
- **Subgoal manipulation** — altering intermediate steps in a multi-step plan without changing the stated final objective
- **Reward hacking in RLHF-trained agents** — identifying proxy metrics the agent optimizes and exploiting them to achieve unintended outcomes
- **Long-horizon manipulation** — in long-running agents, gradually shifting behavior across many steps so no single action appears anomalous

### 4.4 Memory & State Attacks

- **Episodic memory poisoning** — injecting false memories into an agent's persistent memory store
- **Cross-session injection** — content stored in one session is retrieved in another, carrying injected instructions across conversations
- **Context window overflow manipulation** — forcing important safety instructions to scroll out of the context window through conversation length attacks

### 4.5 Multi-Agent System Attacks

- **Orchestrator compromise** — attacking the orchestrating agent to redirect all sub-agents
- **Rogue sub-agent** — injecting a malicious agent into a multi-agent pipeline
- **Trust boundary violations** — exploiting implicit trust between agents in the same system (agent A blindly follows instructions from agent B without verification)
- **Prompt relay attacks** — using one agent as an unwitting relay to deliver injections to another

### 4.6 What to Test

- Can indirect injection cause the agent to invoke unintended tools?
- Can tool parameters be manipulated via injected content?
- Does the agent exfiltrate data through tool calls?
- Are tool permissions appropriately scoped (least privilege)?
- Can an agent's goal be hijacked mid-task?
- Is there human-in-the-loop verification for irreversible actions?
- How does the agent behave when its memory is seeded with false information?

---

## 5. Multi-Modal Attacks

When models process images, audio, video, or code in addition to text, each modality introduces its own adversarial attack surface.

### 5.1 Adversarial Images

- **Pixel-level perturbations** — imperceptible changes to an image that cause misclassification or incorrect captioning (FGSM, PGD applied to vision encoders)
- **Visual prompt injection** — embedding text instructions inside an image (printed text, steganography, adversarial patches) that the vision model reads and follows
- **Typographic attacks** — placing misleading labels on physical objects in images (a "banana" sticker on a toaster)
- **Patch attacks** — adversarial patches that, when placed in a scene, cause systematic misclassification of everything in view
- **OCR manipulation** — crafting documents or images where OCR output contains injected instructions invisible to human readers

### 5.2 Adversarial Audio

- **Imperceptible audio perturbations** — small noise additions that cause speech-to-text models to transcribe different text than what was spoken
- **Hidden voice commands** — audio content inaudible to humans but recognized by speech recognition systems (ultrasonic commands, psychoacoustic hiding)
- **Speaker spoofing** — fooling speaker verification systems with synthesized or replayed audio
- **Transcription injection** — audio that transcribes to instruction-like text when processed by an ASR model feeding into an LLM pipeline

### 5.3 Code & Structured Data Attacks

- **Adversarial code inputs** — code that appears benign on static inspection but causes harmful behavior when executed by a code-executing agent
- **Malicious notebooks** — Jupyter notebooks or scripts with hidden cells or obfuscated logic
- **Data exfiltration via code execution** — prompting a code-executing agent to write and run code that reads environment variables, credentials, or files and exfiltrates them
- **Dependency confusion** — causing an agent to install malicious packages by exploiting package name resolution
- **Prompt injection in code comments** — instructions embedded in comments of code files the agent reviews or executes

### 5.4 Cross-Modal Attacks

- **Modality mismatch exploitation** — providing contradictory information across modalities (image says one thing, text says another) to confuse the model's reasoning
- **Modal privilege escalation** — using a low-trust modality (image) to inject instructions that override high-trust modality (system prompt text)
- **Stealthy multi-modal payloads** — benign text combined with an adversarial image that together trigger harmful behavior neither would cause alone

### 5.5 What to Test

- Can text embedded in an image override text instructions?
- Does the model follow instructions hidden in image metadata or steganographic content?
- Can audio inputs cause the model to transcribe and execute injected instructions?
- Does a code-executing agent resist data exfiltration via generated code?
- Are outputs from vision/audio encoders treated as trusted or untrusted input?

---

## 6. Evaluation & Metrics

Red teaming outputs need to be measured, not just described.

| Metric | What it measures |
|---|---|
| Attack success rate (ASR) | % of attempts that elicit the target behavior |
| Jailbreak transfer rate | ASR of attacks developed on one model applied to another |
| Refusal consistency | Variance in refusal behavior across rephrased prompts |
| Injection reach | % of retrieved chunks that are attacker-controlled under corpus poisoning |
| Tool call anomaly rate | % of tool invocations that deviate from the intended task |
| Latency impact | Performance degradation caused by adversarial inputs |
| Recovery rate | How often the model self-corrects after an injection attempt |

---

## 7. Defenses to Understand (and Attempt to Break)

A red teamer needs to know the defense landscape in order to route around it.

| Defense | How it works | Red team bypass approach |
|---|---|---|
| Input classifiers | Filter harmful inputs before they reach the model | Obfuscation, encoding, language switching |
| Output classifiers | Filter harmful model outputs | Indirect elicitation, multi-step generation |
| Constitutional AI / RLAIF | Alignment via self-critique during training | Many-shot priming, persona attacks |
| Prompt hardening | Explicitly instruct the model to resist injection | Delimiter confusion, context overflow |
| Retrieval provenance tracking | Tag and validate document sources | Sybil poisoning, authority spoofing |
| Tool sandboxing | Limit what tools can access or modify | Capability bootstrapping, chaining |
| Human-in-the-loop (HITL) | Require human approval for irreversible actions | Social engineering the human reviewer |
| Spotlighting | Clearly delimit retrieved content from instructions | Delimiter confusion in retrieved text |

---

## 8. Key Tools & Frameworks

| Tool | Purpose |
|---|---|
| Garak | LLM vulnerability scanning and probing |
| PromptBench | Adversarial robustness evaluation for LLMs |
| PyRIT (Microsoft) | Python Risk Identification Toolkit for LLMs |
| ART (IBM) | Adversarial Robustness Toolbox for ML models |
| LangChain / LangGraph | Building agentic pipelines for attack simulation |
| Burp Suite | Intercepting and modifying API calls to LLM endpoints |
| Semantic Kernel | Red teaming agentic orchestration scenarios |
| HarmBench | Standardized benchmark for LLM safety evaluation |
| HELM | Holistic evaluation across model capabilities and safety |

---

## 9. Responsible Disclosure & Ethics

- Always operate within an authorized scope — get written permission before testing production systems
- Document all findings with reproduction steps, evidence, and impact assessment
- Follow coordinated disclosure timelines (typically 90 days before public release)
- For foundation model vulnerabilities, engage the model provider's security team directly
- Distinguish between capability elicitation research (acceptable) and active exploitation for harm (not acceptable)
- Treat discovered jailbreaks as vulnerabilities, not tricks — report them, don't distribute them

---

## Recommended Reading

- Perez & Ribeiro (2022) — *Ignore Previous Prompt: Attack Techniques for Language Models*
- Greshake et al. (2023) — *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*
- Zou et al. (2023) — *Universal and Transferable Adversarial Attacks on Aligned Language Models* (GCG)
- Anthropic red team papers — internal and published threat taxonomies
- NIST AI RMF (2023) — *Artificial Intelligence Risk Management Framework*
- OWASP Top 10 for LLM Applications
- Weidinger et al. (2022) — *Taxonomy of Risks posed by Language Models* (DeepMind)
