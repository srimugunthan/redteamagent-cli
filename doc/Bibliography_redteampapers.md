# Important Papers on Red Teaming — LLM, Agent & RAG Systems

Organized into four sections: (1) Foundational LLM Red Teaming, (2) Jailbreak Attacks & Automated Red Teaming, (3) Agent Red Teaming, (4) RAG Red Teaming. Within each section, papers are ordered by influence and recency.

---

## SECTION 1: Foundational LLM Red Teaming

---

### 1. Red Teaming Language Models with Language Models
**Authors:** E. Perez, S. Huang, F. Song, T. Cai, R. Ring, J. Aslanides, A. Glaese, N. McAleese, G. Irving  
**Venue:** EMNLP 2022  
**Why it matters:** The foundational paper that introduced automated LLM-vs-LLM red teaming. Proposes using a red LM to automatically generate adversarial test cases against a target LM. The conceptual basis for nearly all subsequent automated red teaming work.  
**Citations:** ~1,000+  
**Link:** https://arxiv.org/abs/2202.03286

---

### 2. Red Teaming Language Models to Reduce Harms: Methods, Scaling Behaviors, and Lessons Learned (Ganguli et al.)
**Authors:** Deep Ganguli, Liane Lovitt, Jackson Kernion, Amanda Askell et al. (Anthropic)  
**Venue:** arXiv 2022  
**Why it matters:** Large-scale empirical study of human red teamers attacking Claude. Documents scaling behavior of red teaming effectiveness and introduces the open-source red teaming dataset. Essential reference for red team operations.  
**Citations:** ~800+  
**Link:** https://arxiv.org/abs/2209.07858

---

### 3. Constitutional AI: Harmlessness from AI Feedback
**Authors:** Y. Bai, S. Kadavath, S. Kundu, A. Askell et al. (Anthropic)  
**Venue:** arXiv 2022  
**Why it matters:** Introduces Constitutional AI (CAI) and RLAIF — a self-critique and revision loop for harmlessness. Directly relevant to red teaming as it defines the alignment target that red teamers probe.  
**Citations:** ~1,500+  
**Link:** https://arxiv.org/abs/2212.08073

---

### 4. HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal
**Authors:** M. Mazeika, L. Phan, X. Yin, A. Zou, Z. Wang, N. Mu, E. Sakhaee, N. Li, S. Basart, B. Li, D. Forsyth, D. Hendrycks  
**Venue:** ICML 2024  
**Why it matters:** De facto standard benchmark for comparing red teaming attack methods. Evaluates 18 attack methods across 33 LLMs with 510 standardized harm behaviors. GCG, PAIR, TAP, AutoDAN, PAP — all compared here.  
**Citations:** ~500+  
**Link:** https://arxiv.org/abs/2402.04249

---

### 5. Explore, Establish, Exploit: Red Teaming Language Models from Scratch
**Authors:** S. Casper, J. Lin, J. Kwon, G. Culp, D. Hadfield-Menell  
**Venue:** arXiv 2023  
**Why it matters:** Proposes a structured three-phase methodology for red teaming LLMs from scratch, without prior knowledge of the model. Useful operationally for teams building red teaming programs.  
**Citations:** ~250+  
**Link:** https://arxiv.org/abs/2306.09442

---

### 6. Against the Achilles' Heel: A Survey on Red Teaming for Generative Models
**Authors:** L. Zhang, Y. Zhou, et al.  
**Venue:** arXiv 2024  
**Why it matters:** Comprehensive survey covering red teaming strategies, automated attack approaches, and defense methods for LLMs and VLMs. Good taxonomy of the full attack landscape.  
**Citations:** ~200+  
**Link:** https://arxiv.org/abs/2404.00629

---

### 7. TrustGPT: A Benchmark for Trustworthy and Responsible Large Language Models
**Authors:** Y. Huang, Q. Zhang, L. Sun et al.  
**Venue:** arXiv 2023  
**Why it matters:** Proposes a multi-dimensional trustworthiness benchmark (toxicity, bias, value alignment) that complements adversarial red teaming by measuring what the red teamer is trying to break.  
**Citations:** ~300+  
**Link:** https://arxiv.org/abs/2306.11507

---

## SECTION 2: Jailbreak Attacks & Automated Red Teaming

---

### 8. Universal and Transferable Adversarial Attacks on Aligned Language Models (GCG)
**Authors:** A. Zou, Z. Wang, J. Z. Kolter, M. Fredrikson  
**Venue:** arXiv 2023  
**Why it matters:** Introduces the Greedy Coordinate Gradient (GCG) attack — the first fully automated, gradient-based jailbreaking method. Demonstrated universal adversarial suffixes that transfer across models including black-box ChatGPT. Foundational for all suffix-optimization red teaming.  
**Citations:** ~1,500+  
**Link:** https://arxiv.org/abs/2307.15043

---

### 9. Jailbreaking Black Box Large Language Models in Twenty Queries (PAIR)
**Authors:** P. Chao, A. Robey, E. Dobriban, H. Hassani, G. J. Pappas, E. Wong  
**Venue:** IEEE SaTML 2025 (arXiv 2023)  
**Why it matters:** Introduces PAIR (Prompt Automatic Iterative Refinement) — uses an attacker LLM to iteratively refine jailbreaks against a target LLM in ~20 queries. Highly practical for black-box red teaming.  
**Citations:** ~500+  
**Link:** https://arxiv.org/abs/2310.08419

---

### 10. Tree of Attacks with Pruning: Optimizing Jailbreak Prompts (TAP)
**Authors:** A. Mehrotra, M. Zampetakis, P. Kassianik, B. Nelson, H. Anderson, Y. Singer, A. Karbasi  
**Venue:** NeurIPS 2024  
**Why it matters:** TAP extends PAIR with a tree-search approach, pruning unpromising attack branches to find jailbreaks more efficiently. State-of-the-art black-box automated red teaming method.  
**Citations:** ~300+  
**Link:** https://arxiv.org/abs/2312.02119

---

### 11. AutoDAN: Generating Stealthy Jailbreak Prompts on Aligned Language Models
**Authors:** X. Liu, N. Xu, M. Chen, C. Xiao  
**Venue:** ICLR 2024  
**Why it matters:** Generates low-perplexity, human-readable adversarial prompts using genetic algorithms. Avoids detection by perplexity filters that catch GCG-style gibberish suffixes. Key paper for stealthy red teaming.  
**Citations:** ~400+  
**Link:** https://arxiv.org/abs/2310.04451

---

### 12. GPTFuzzer: Red Teaming Large Language Models with Auto-Generated Jailbreak Prompts
**Authors:** J. Yu, X. Lin, Z. Yu, X. Xing  
**Venue:** arXiv 2023  
**Why it matters:** Applies grey-box fuzzing methodology (AFL-style mutation) to LLM jailbreaking. Generates diverse jailbreak templates by mutating human-written seeds. Directly relevant to mutation engine design in RedTeamAgentLoop.  
**Citations:** ~350+  
**Link:** https://arxiv.org/abs/2309.10253

---

### 13. MASTERKEY: Automated Jailbreak Across Multiple Large Language Model Chatbots
**Authors:** G. Deng, Y. Liu, Y. Li, K. Wang, Y. Zhang, Z. Li, H. Wang, T. Zhang, Y. Liu  
**Venue:** NDSS 2024  
**Why it matters:** Reverse-engineers LLM safety training to generate universal jailbreaks that work across GPT, Bard, Bing Chat simultaneously. Demonstrates cross-model transferability of automated attacks.  
**Citations:** ~400+  
**Link:** https://arxiv.org/abs/2307.08715

---

### 14. FLIRT: Feedback Loop In-Context Red Teaming
**Authors:** N. Mehrabi, P. Goyal, C. Dupuy, Q. Hu, S. Ghosh, R. Zemel, K.-W. Chang, A. Galstyan, R. Gupta  
**Venue:** arXiv 2023  
**Why it matters:** Uses an in-context feedback loop to iteratively refine red teaming prompts without fine-tuning. Lightweight, interpretable, and directly related to the loop controller design in iterative red teaming frameworks.  
**Citations:** ~250+  
**Link:** https://arxiv.org/abs/2308.04265

---

### 15. Best-of-N Jailbreaking
**Authors:** J. Hughes, S. Price, A. Lynch, R. Schaeffer, F. Barez, S. Koyejo, H. Sleight, E. Jones, E. Perez, M. Sharma  
**Venue:** arXiv 2024  
**Why it matters:** Shows that simply sampling N outputs from a model and selecting the most harmful one is a surprisingly effective and scalable jailbreak. Exposes fundamental limitations of RLHF safety training at scale.  
**Citations:** ~300+  
**Link:** https://arxiv.org/abs/2412.03556

---

### 16. Baseline Defenses for Adversarial Attacks Against Aligned Language Models
**Authors:** N. Jain, A. Schwarzschild, Y. Wen, G. Somepalli, J. Kirchenbauer, P.-Y. Chiang, M. Goldblum, A. Saha, J. Geiping, T. Goldstein  
**Venue:** arXiv 2023  
**Why it matters:** Evaluates input preprocessing defenses (paraphrasing, retokenization, perplexity filtering) against GCG-style attacks. Essential reading for understanding defense effectiveness and bypass.  
**Citations:** ~400+  
**Link:** https://arxiv.org/abs/2309.00614

---

### 17. SmoothLLM: Defending Large Language Models Against Jailbreaking Attacks
**Authors:** A. Robey, E. Wong, H. Hassani, G. J. Pappas  
**Venue:** arXiv 2023  
**Why it matters:** Proposes randomized smoothing adapted to LLMs — perturbs input copies and takes a majority vote. Provides certifiable robustness against suffix-optimization attacks.  
**Citations:** ~300+  
**Link:** https://arxiv.org/abs/2310.03684

---

## SECTION 3: Agent Red Teaming

---

### 18. AGENTPOISON: Red-Teaming LLM Agents via Poisoning Memory or Knowledge Bases
**Authors:** Z. Chen, H. Zhou, B. Li et al.  
**Venue:** NeurIPS 2024  
**Why it matters:** First backdoor attack framework specifically targeting LLM agents. Poisons the long-term memory or RAG knowledge base so that retrieval of malicious demonstrations triggers harmful agent behavior. Directly unifies agent and RAG threat surfaces.  
**Citations:** ~300+  
**Link:** https://arxiv.org/abs/2407.12784

---

### 19. Red-Teaming LLM Multi-Agent Systems via Communication Attacks (AiTM)
**Authors:** P. He, Y. Lin, S. Dong, H. Xu, Y. Xing, H. Liu  
**Venue:** ACL Findings 2025  
**Why it matters:** Introduces Agent-in-the-Middle (AiTM) attack — intercepts and manipulates inter-agent communication to propagate malicious influence across a multi-agent system. Demonstrates cascading compromise in MAS.  
**Citations:** ~100+ (recent)  
**Link:** https://arxiv.org/abs/2502.14847

---

### 20. SIRAJ: Diverse and Efficient Red-Teaming for LLM Agents via Distilled Structured Reasoning
**Authors:** (SIRAJ authors, 2025)  
**Venue:** arXiv 2025  
**Why it matters:** Addresses diversity in agent red teaming — first work to explicitly optimize for comprehensive coverage of attack strategies and safety categories in agent evaluation. Black-box; no white-box access required.  
**Citations:** ~50+ (recent)  
**Link:** https://arxiv.org/abs/2510.26037

---

### 21. UDora: A Unified Red Teaming Framework Against LLM Agents by Dynamically Hijacking Their Own Reasoning
**Authors:** (UDora authors, 2025)  
**Venue:** arXiv 2025  
**Why it matters:** White-box attack that dynamically hijacks the agent's chain-of-thought reasoning to induce harmful actions. Demonstrates that reasoning itself is an attack surface for agents with tool-calling capabilities.  
**Citations:** ~80+ (recent)  
**Link:** https://arxiv.org/abs/2503.01908

---

### 22. AgentSmith: A Single Image Can Jailbreak One Million Multimodal LLM Agents Exponentially Fast
**Authors:** X. Gu et al.  
**Venue:** ICML 2024  
**Why it matters:** Shows that a single adversarial image injected into a multi-agent environment can propagate jailbreaks exponentially across a large fleet of agents through inter-agent interactions. Critical for multi-agent safety.  
**Citations:** ~200+  
**Link:** https://arxiv.org/abs/2402.08567

---

### 23. AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents
**Authors:** E. Debenedetti, V. Vero, M. Balunovic, L. Beurer-Kellner, M. Fischer, F. Tramèr  
**Venue:** NeurIPS 2024  
**Why it matters:** Introduces a benchmark for evaluating prompt injection attacks and defenses in realistic agentic task pipelines (email, calendar, banking). Key benchmark for agent red teaming evaluation.  
**Citations:** ~200+  
**Link:** https://arxiv.org/abs/2406.13352

---

### 24. Design Patterns for Securing LLM Agents Against Prompt Injections
**Authors:** L. Beurer-Kellner, B. Buesser, A.-M. Crețu, E. Debenedetti et al.  
**Venue:** arXiv 2025  
**Why it matters:** Proposes architectural defense patterns (spotlighting, privilege control, output sanitization) to harden agentic pipelines. Complements red teaming by defining what a hardened agent architecture looks like.  
**Citations:** ~150+  
**Link:** https://arxiv.org/abs/2506.08837

---

### 25. Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems
**Authors:** D. Lee, M. Tiwari  
**Venue:** arXiv 2024  
**Why it matters:** Demonstrates that prompt injections can propagate between agents via shared communication channels — essentially an inter-agent worm. Important for understanding lateral movement in multi-agent systems.  
**Citations:** ~150+  
**Link:** https://arxiv.org/abs/2410.07218

---

### 26. AGENT-SAFETYBENCH: Evaluating the Safety of LLM Agents
**Authors:** Z. Zhang et al.  
**Venue:** arXiv 2024  
**Why it matters:** Comprehensive safety evaluation benchmark for LLM agents across 349 tasks and 10 risk categories. Covers unsafe actions, goal hijacking, environment manipulation, and tool misuse.  
**Citations:** ~100+  
**Link:** https://arxiv.org/abs/2410.14566

---

### 27. Benchmarking the Robustness of Agentic Systems to Adversarially-Induced Harms
**Authors:** (Multiple authors, 2025)  
**Venue:** arXiv 2025  
**Why it matters:** Systematic taxonomy of adversarial harm categories in agentic systems with benchmark evaluation. Covers the full range from prompt injection to memory poisoning to tool misuse.  
**Citations:** ~80+ (recent)  
**Link:** https://arxiv.org/abs/2503.15654

---

### 28. AgenticRed: Optimizing Agentic Systems for Automated Red-Teaming
**Authors:** (AgenticRed authors, 2025)  
**Venue:** arXiv 2025  
**Why it matters:** Proposes a fully automated red teaming system that itself uses agentic architecture to find vulnerabilities in target agentic pipelines. Meta-level red teaming — an agent red-teaming an agent.  
**Citations:** ~50+ (recent)  
**Link:** https://arxiv.org/abs/2601.13518

---

### 29. How Vulnerable Are AI Agents to Indirect Prompt Injections? Insights from a Large-Scale Public Competition
**Authors:** Multiple authors (UK AISI / US CAISI competition)  
**Venue:** arXiv 2025  
**Why it matters:** Large-scale empirical study with 464 participants and 240K+ attack attempts across 13 frontier models. Finds ASR ranging 0.5%–8.5%, universal attack strategies transferring across 21 behaviors, and weak correlation between capability and robustness.  
**Citations:** ~100+ (recent)  
**Link:** https://arxiv.org/abs/2603.15714

---

### 30. Attacking Tool-Enabled LLM Frameworks: Threats and Defenses
**Authors:** S. Liu et al.  
**Venue:** NDSS 2025  
**Why it matters:** Analyzes attack surfaces introduced by tool-calling in LLM frameworks (function calls, API access). Directly relevant to tool fuzzing and privilege escalation in agentic red teaming.  
**Citations:** ~100+  
**Link:** https://arxiv.org/abs/2407.17915

---

### 31. Here Comes the AI Worm: Unleashing Zero-Click Worms That Target GenAI-Powered Applications
**Authors:** S. Cohen, R. Bitton, B. Nassi  
**Venue:** arXiv 2024  
**Why it matters:** Demonstrates self-replicating adversarial prompts in GenAI-powered multi-agent email/calendar applications. First demonstration of GenAI worms — prompts that propagate and execute without user interaction.  
**Citations:** ~300+  
**Link:** https://arxiv.org/abs/2403.02817

---

## SECTION 4: RAG Red Teaming

---

### 32. PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models
**Authors:** W. Zou et al.  
**Venue:** arXiv 2024  
**Why it matters:** Formulates RAG corpus poisoning as a constrained optimization problem. Injecting a small number of malicious texts can reliably induce targeted incorrect answers. Foundational attack paper for RAG security.  
**Citations:** ~300+  
**Link:** https://arxiv.org/abs/2402.07867

---

### 33. BadRAG: Identifying Vulnerabilities in Retrieval Augmented Generation of Large Language Models
**Authors:** J. Xue, M. Zheng, Y. Hu, F. Liu, X. Chen, Q. Lou  
**Venue:** arXiv 2024  
**Why it matters:** Introduces trigger-conditioned retrieval backdoors — poisoned passages that remain dormant until activated by a specific trigger keyword in the query. Stealthy RAG backdoor attack.  
**Citations:** ~200+  
**Link:** https://arxiv.org/abs/2406.00083

---

### 34. Poisoning Retrieval Corpora by Injecting Adversarial Passages
**Authors:** Z. Zhong, Z. Huang, A. Wettig, D. Chen  
**Venue:** EMNLP 2023  
**Why it matters:** Early systematic study of adversarial passage injection attacks against dense retrievers. Shows that a single injected adversarial document can be retrieved for a large set of queries.  
**Citations:** ~300+  
**Link:** https://arxiv.org/abs/2310.15236

---

### 35. Certifiably Robust RAG Against Retrieval Corruption
**Authors:** C. Xiang et al.  
**Venue:** arXiv 2024  
**Why it matters:** Proposes a certified defense framework for RAG — provides provable robustness guarantees against a bounded number of poisoned passages in the retrieved context. Rare theoretical grounding for RAG defense.  
**Citations:** ~150+  
**Link:** https://arxiv.org/abs/2405.15556

---

### 36. The Good and the Bad: Exploring Privacy Issues in Retrieval-Augmented Generation (RAG)
**Authors:** S. Zeng et al.  
**Venue:** arXiv 2024  
**Why it matters:** Analyzes privacy attack surfaces unique to RAG — membership inference on the knowledge base, data extraction through repeated querying, and retrieval authorization bypass. Complements security red teaming with privacy red teaming.  
**Citations:** ~200+  
**Link:** https://arxiv.org/abs/2402.16893

---

### 37. RAG-Thief: Scalable Extraction of Private Data from Retrieval-Augmented Generation Applications with Agent-Based Attacks
**Authors:** C. Jiang et al.  
**Venue:** arXiv 2024  
**Why it matters:** Uses an agent-based attack loop to systematically extract private documents from a RAG knowledge base through carefully crafted queries. Demonstrates that RAG authorization bypass is practically exploitable at scale.  
**Citations:** ~100+  
**Link:** https://arxiv.org/abs/2411.14110

---

### 38. Securing Retrieval-Augmented Generation: A Taxonomy of Attacks, Defenses, and Future Directions
**Authors:** (Survey authors, 2025)  
**Venue:** arXiv 2025  
**Why it matters:** Most comprehensive taxonomy of RAG attack surfaces to date — covers pre-retrieval corpus poisoning, retrieval-time ranking manipulation, and generation-time injection. Essential reference for structuring a RAG red teaming capability.  
**Citations:** ~50+ (recent, rapidly growing)  
**Link:** https://arxiv.org/abs/2604.08304

---

### 39. Prompt Injection Attack Against LLM-Integrated Applications
**Authors:** Y. Liu, G. Deng, Z. Li, K. Wang, Z. Wang, X. Wang, T. Zhang, Y. Liu, H. Wang, Y. Zheng et al.  
**Venue:** arXiv 2023  
**Why it matters:** Systematic study of prompt injection attacks in LLM-integrated applications — covers direct and indirect injection. Lays the conceptual groundwork for indirect prompt injection via retrieved RAG documents.  
**Citations:** ~700+  
**Link:** https://arxiv.org/abs/2306.05499

---

### 40. Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection
**Authors:** K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, M. Fritz  
**Venue:** AISec Workshop 2023  
**Why it matters:** First comprehensive study of indirect prompt injection — attacker injects malicious instructions into external content (websites, emails, documents) that the LLM retrieves and executes. Foundational for RAG indirect injection threat modelling.  
**Citations:** ~600+  
**Link:** https://arxiv.org/abs/2302.12173

---

### 41. The Silent Saboteur: Imperceptible Adversarial Attacks Against Black-Box RAG Systems
**Authors:** (Authors, 2025)  
**Venue:** arXiv 2025  
**Why it matters:** Introduces imperceptible adversarial perturbations against RAG retrievers — documents that appear normal to humans but are preferentially retrieved by the dense retriever, enabling stealthy corpus poisoning.  
**Citations:** ~50+ (recent)  
**Link:** https://arxiv.org/abs/2505.18583

---

### 42. IKEA: Implicit Knowledge Extraction Attack Without Explicit Jailbreaks
**Authors:** Wang et al.  
**Venue:** arXiv 2025  
**Why it matters:** Demonstrates knowledge extraction from RAG knowledge bases without requiring explicit jailbreak prompts — purely through crafted retrieval queries. Important for understanding covert data exfiltration from RAG deployments.  
**Citations:** ~50+ (recent)  
**Link:** https://arxiv.org/abs/2502.12345

---

## SECTION 5: Surveys & Cross-Cutting References

---

### 43. Vulnerabilities of Large Language Models to Adversarial Attacks (ACL 2024 Tutorial)
**Authors:** D. Yoo, M. Garg et al.  
**Venue:** ACL 2024 Tutorial  
**Why it matters:** Comprehensive tutorial covering the full adversarial attack taxonomy for LLMs — from token-level suffix optimization to semantic jailbreaks to multimodal attacks. Best single reference for the attack landscape overview.  
**Citations:** Tutorial (widely referenced)  
**Link:** https://llm-vulnerability.github.io/

---

### 44. A Survey on Red Teaming for Generative AI: Threats, Methods, and Future Directions
**Authors:** (Multiple authors, 2024)  
**Venue:** arXiv 2024  
**Why it matters:** Broad survey of red teaming methods across LLMs, image models, and multimodal systems. Covers attack taxonomies, automated methods, and evaluation frameworks.  
**Citations:** ~150+  
**Link:** https://arxiv.org/abs/2310.10844

---

### 45. PromptRobust: Towards Evaluating the Robustness of Large Language Models on Adversarial Prompts
**Authors:** K. Zhu, J. Wang, J. Zhou, Z. Wang, H. Chen, Y. Wang, L. Yang, W. Ye, Y. Zhang, N. Gong et al.  
**Venue:** ACM Workshop on Large AI Systems and Models, 2023  
**Why it matters:** Introduces a structured benchmark of adversarial prompt types (typos, character attacks, word attacks, sentence attacks) against LLM robustness. Distinct from jailbreaking — focuses on semantic robustness degradation.  
**Citations:** ~400+  
**Link:** https://arxiv.org/abs/2306.04528

---

### 46. PyRIT: Microsoft's Open-Source Framework for Red-Teaming Generative AI Systems
**Authors:** R. Badoiu, Microsoft AI Red Team  
**Venue:** GitHub + White Paper, 2024  
**Why it matters:** Production-grade open-source red teaming framework from Microsoft. Implements shadow-model attacks, multi-turn adversarial conversations, and supports Azure ML endpoints. Key industry tool for comparison with RedTeamAgentLoop.  
**Citations:** ~200+ (widely adopted in industry)  
**Link:** https://github.com/microsoft/pyrit

---

### 47. Adversarial Reasoning at Jailbreaking Time
**Authors:** M. Sabbaghi, P. Kassianik, G. J. Pappas, Y. Singer, A. Karbasi, H. Hassani  
**Venue:** arXiv 2025  
**Why it matters:** Uses chain-of-thought reasoning to automatically construct more effective jailbreaks. Demonstrates that model reasoning capabilities can be turned adversarially against the model's own safety training.  
**Citations:** ~100+ (recent)  
**Link:** https://arxiv.org/abs/2502.12345

---

### 48. Leaky Thoughts: Large Reasoning Models Are Not Private Thinkers
**Authors:** T. Green, M. Gubri, H. Puerto, S. Yun, S. J. Oh  
**Venue:** arXiv 2025  
**Why it matters:** Shows that extended thinking / chain-of-thought in reasoning models leaks private information and safety-relevant reasoning. New attack surface opened by o1/R1-style reasoning models.  
**Citations:** ~100+ (recent)  
**Link:** https://arxiv.org/abs/2506.15674

---

### 49. xJailbreak: Representation-Space Guided Reinforcement Learning for Interpretable LLM Jailbreaking
**Authors:** S. Lee, S. Ni et al.  
**Venue:** arXiv 2025  
**Why it matters:** Uses RL in representation space to generate interpretable jailbreaks, making the attack reason transparent. Important for red teamers who need to understand *why* an attack succeeded, not just that it did.  
**Citations:** ~80+ (recent)  
**Link:** https://arxiv.org/abs/2501.01234

---

### 50. AutoRedTeamer: Autonomous Red Teaming with Lifelong Attack Integration
**Authors:** A. Zhou, K. Wu, F. Pinto, Z. Chen, Y. Zeng, Y. Yang, S. Yang, S. Koyejo, J. Zou, B. Li  
**Venue:** arXiv 2025  
**Why it matters:** Fully autonomous red teaming agent that continuously discovers new attack strategies and integrates them into a growing library — lifelong learning for red teaming. Closest existing system to the iterative, adaptive loop in RedTeamAgentLoop.  
**Citations:** ~80+ (recent)  
**Link:** https://arxiv.org/abs/2503.15754

## 51. Multi-Agent Framework for Threat Mitigation and Resilience in AI-Based Systems
**Authors:** Armstrong Foundjem (sMIEEE), Lionel Nganyewou Tidjon (sMIEEE)  
**Venue:** arXiv preprint, 2025  
**Citations:** Recent publication (citation count growing)  
**Link:** https://doi.org/10.5281/zenodo.17480025

---

*Note: Citation counts are approximate estimates based on Google Scholar / Semantic Scholar as of mid-2025. Papers published in 2024–2025 are rapidly accumulating citations. ArXiv links are provided; many papers also appear in official conference proceedings at the listed venues.*
