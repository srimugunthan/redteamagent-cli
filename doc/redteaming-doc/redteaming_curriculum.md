# Red Teaming Curriculum

A generic, role-agnostic curriculum for learning red teaming from first principles to practitioner level. Estimated duration: ~28 weeks.

---

## Phase 1 — Mindset & Methodology (Weeks 1–3)

Before touching any tools, you need to internalize how attackers think. This means learning to assume breach, chain small weaknesses into high-impact paths, and question every assumption a defender makes.

### Topics

- **Red team mindset** — adversarial thinking, assume-breach posture, attacker's perspective vs defender's
- **Engagement scoping** — rules of engagement, legal authorization, defining scope and targets
- **Core frameworks** — MITRE ATT&CK, PTES (Penetration Testing Execution Standard), OWASP Testing Guide

### Key Resources

| Resource | Notes |
|---|---|
| MITRE ATT&CK | Taxonomy of adversary techniques and tactics |
| PTES | End-to-end penetration testing standard |
| OWASP Testing Guide | Web-focused methodology |

---

## Phase 2 — Reconnaissance & Initial Access (Weeks 4–8)

Most real attacks start long before any exploit runs. Study passive and active recon, social engineering, and the techniques attackers use to first gain a foothold.

### Topics

- **OSINT & passive recon** — Shodan, Maltego, LinkedIn harvesting, Google dorking, WHOIS, certificate transparency
- **Active recon** — port scanning, service enumeration, subdomain discovery, fingerprinting
- **Social engineering** — phishing, spearphishing, vishing, pretexting, physical intrusion
- **Initial access techniques** — spearphishing attachments, supply chain compromise, valid account abuse

### Key Resources

| Resource | Notes |
|---|---|
| Maltego | Graph-based OSINT and link analysis |
| Shodan | Internet-facing device and service search |
| Social Engineer Toolkit (SET) | Framework for social engineering attacks |
| theHarvester | Email and subdomain enumeration |

---

## Phase 3 — Exploitation & Post-Compromise (Weeks 9–15)

The technical core of traditional red teaming. Covers gaining access, escalating privileges, and moving through a target environment while evading detection.

### Topics

- **Network exploitation** — vulnerability scanning, service exploitation, Metasploit framework, pivoting, tunneling
- **Web application attacks** — SQLi, XSS, SSRF, IDOR, authentication bypass, insecure deserialization, XXE
- **Post-compromise tradecraft**
  - Privilege escalation (local and domain)
  - Lateral movement (Pass-the-Hash, Pass-the-Ticket, WMI, PSExec)
  - Credential dumping (Mimikatz, LSASS, SAM)
  - Persistence (scheduled tasks, registry keys, service installation)
  - Defense evasion and covering tracks

### Practice Environments

- HackTheBox
- TryHackMe
- Vulnhub
- PortSwigger Web Security Academy

### Key Resources

| Resource | Notes |
|---|---|
| Metasploit Framework | Exploitation and post-exploitation |
| Burp Suite | Web application attack proxy |
| BloodHound | Active Directory attack path mapping |
| Nmap | Network discovery and service enumeration |

---

## Phase 4 — Adversarial ML & AI Systems (Weeks 16–22)

Where red teaming meets the modern AI/ML stack. Three parallel sub-tracks covering classical ML attacks, model-level threats, and LLM-specific techniques.

### Sub-track A — Adversarial Examples & Evasion

- White-box attacks: FGSM (Fast Gradient Sign Method), PGD (Projected Gradient Descent), Carlini-Wagner (C&W)
- Black-box attacks: transferability, query-based attacks, decision-based attacks
- Robustness evaluation: certified defenses, adversarial training, empirical robustness benchmarks

### Sub-track B — Model-Level Attacks

- **Model extraction** — stealing model behavior through query APIs (functionally equivalent models)
- **Membership inference** — determining if a data point was in the training set
- **Data poisoning** — corrupting training data to degrade performance or implant backdoors
- **Backdoor/trojan attacks** — trigger-based behavior injection (BadNets, STRIP, spectral signatures)

### Sub-track C — LLM & Agentic AI Red Teaming

- **Prompt injection** — direct and indirect (via documents, tool outputs, RAG retrieval)
- **Jailbreaking** — role-play exploits, context manipulation, many-shot jailbreaking, DAN-style attacks
- **RAG pipeline attacks** — poisoning retrieval corpora, adversarial document injection
- **Agentic system exploitation** — tool misuse, privilege escalation through tool chains, goal hijacking
- **Multi-modal attacks** — adversarial images, audio, and code inputs to vision and speech models

### Key Resources

| Resource | Notes |
|---|---|
| IBM Adversarial Robustness Toolbox (ART) | Comprehensive ML attack and defense library |
| CleverHans | Adversarial example benchmarking |
| Garak | LLM vulnerability probing framework |
| NIST AI RMF | AI risk management framework |
| Anthropic red team research papers | LLM-specific threat taxonomy |
| HELM | Holistic LLM evaluation |

---

## Phase 5 — Reporting, Tooling & Operations (Weeks 23–28)

Technical skill without communication is wasted. Learn to write findings that clearly convey impact, master the operational toolchain, and build automated continuous adversarial testing pipelines.

### Topics

- **Report writing**
  - Executive summary vs technical narrative
  - Severity rating with CVSS and DREAD
  - Reproduction steps, evidence, and artifacts
  - Remediation recommendations with prioritization
- **Toolchain mastery**
  - C2 frameworks: Cobalt Strike, Sliver, Havoc
  - Web: Burp Suite Pro, Caido
  - AI/LLM: Garak, HELM, PromptBench
  - Automation: custom scripts, CI/CD integration
- **Continuous adversarial testing**
  - Automated red team pipelines (agentic loops, scheduled probing)
  - Integration with MLOps and DevSecOps workflows
  - Tracking findings over model versions and deployments

### Key Resources

| Resource | Notes |
|---|---|
| CVSS v3.1 scoring guide | Standardized vulnerability severity scoring |
| DREAD model | Risk rating for threat modeling |
| CVE/CWE databases | Vulnerability classification references |
| OWASP Top 10 for LLMs | LLM-specific vulnerability taxonomy |

---

## Essential Skills Throughout

Regardless of phase, these cross-cutting skills compound your effectiveness:

- **Documentation discipline** — every finding, step, and artifact must be reproducible and clearly written
- **Scripting** — Python and Bash for automation, custom payloads, and tooling
- **Lab environment management** — spinning up and tearing down isolated test environments safely
- **Legal and ethical grounding** — understanding authorization boundaries, responsible disclosure, and bug bounty norms

---

## Recommended Learning Sequence Summary

```
Weeks 1–3    →  Mindset, frameworks, rules of engagement
Weeks 4–8    →  OSINT, recon, social engineering, initial access
Weeks 9–15   →  Exploitation, post-compromise, web attacks
Weeks 16–22  →  Adversarial ML, model attacks, LLM red teaming
Weeks 23–28  →  Reporting, toolchain, automation
```

---

## Certifications (Optional but Useful)

| Certification | Focus |
|---|---|
| OSCP (Offensive Security) | Hands-on penetration testing |
| CRTO (Certified Red Team Operator) | C2 and red team operations |
| eJPT (eLearnSecurity) | Entry-level penetration testing |
| GPEN / GWAPT (GIAC) | Network and web app pentesting |
| No formal cert yet for AI red teaming | Garak and NIST AI RMF are current anchors |
