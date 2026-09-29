# Landscape check: Merlin's Dilemma and EICB (deep research, 2026-09-15)

Method: a 103-agent deep-research run (5 search angles, 21 primary sources fetched from arXiv, 3-vote adversarial verification on extracted claims). **Topic 1 claims went through the 3-vote verification** (17 confirmed, 8 refuted). **Topic 2 claims were dropped before the vote by a pipeline cap**, so Topic 2 below is reconstructed from the search and fetch stages. The search agents did check arXiv IDs and submission dates directly, but nothing in Topic 2 was adversarially verified. Re-check every Topic 2 ID, date, and scope statement before citing.

---

## Topic 1. Merlin's Dilemma: helpfulness vs. harmfulness as sender / receiver / monitor

### Verdict

**The composition appears new.** No source formalizes dual-use disclosure as a benign sender, a legitimate receiver with common ground, and a hostile monitor; none uses an adversarial RSA speaker; none proposes excess accuracy or calibration as the monitor statistic; none tests rewrite-invariance of a non-content monitor.

Three reservations:

1. The **informedness-gap monitor** is already published (arXiv 2602.23163). Our excess-accuracy monitor must be positioned as a specialization, not a first.
2. **Deniability as a strategic constraint on informativeness** already exists in economics (arXiv 2605.09029 and its JPE 2025 predecessor).
3. The **Chameleon game paper** (arXiv 2501.19398, AAMAS 2026) is a very close game-theoretic analogue with a quantitative conceal-vs-reveal spectrum. It was only search-level checked, not vote-verified.

The RSA-with-eavesdropper strand and the Avalon strand were not fully covered. Absence there is an evidence gap, not evidence of absence.

### Landscape: three literatures, each holding one piece

**(a) Economic theory of deniable communication**

- *Secret Communication with Plausible Deniability*, arXiv 2605.09029 (Cheng, Kim, Tam; v1 9 May 2026). Sender / receiver / outside observer. Secrecy = state-independent message marginal. Deniability = every induced action must be rationalizable from the receiver's public baseline alone. Deniability binds iff the baseline signal is directional. The observer detects from *actions vs. public evidence*, not content. This is the formal analogue of claim (1). Verified 3-0.
  - Do **not** cite it for a quantitative "at most one bit" throughput ceiling. That claim was refuted 1-2. Cite only the qualitative characterization.
  - Predecessors: Antic, Chakraborty & Harbaugh, *Subversive Conversations*, JPE 133(5) 2025; Chassang & Padró i Miquel 2019. Open question: whether those already contain a quantitative informativeness-vs-deniability tradeoff.

**(b) LLM safety policy: "how much to tell" rather than "whether to refuse"**

- *From Hard Refusals to Safe-Completions*, arXiv 2508.09224 (OpenAI; 12 Aug 2025). Reward = helpfulness × graded safety score; dual-use handled by a "meaningful facilitation" threshold (actionable support disallowed, high-level allowed). No game, no monitor, no eavesdropper. Verified 3-0.
- *OpenSafeIntent*, arXiv 2607.02047 (Uppaal, Lyu, Sung, Hu; 2 Jul 2026). 805 prompts in 115 sets, intent varied with task fixed. Key result for us: high-level non-operational answers are **not** reliably safe (unsafe rate 58% vs. 19% for re-framing the task). The field's current answer to "how much to tell" is "re-frame what you answer", not "answer less precisely". Our frontier framing has to engage with this. Verified 3-0; numbers are autograder judgments.
- *A Content-Based Framework for Cybersecurity Refusal Decisions*, arXiv 2602.15689 (Irregular; Feb 2026) and *A New Framework for Cybersecurity Refusals in AI Agents*, arXiv 2606.02644 (Jones, Dziemian, Fredrikson, Kolter; 31 May 2026). Graded per-request rubrics, two implicit audiences, no signaling-game formalization.
- *Safety Game*, arXiv 2510.09330 (Nguyen & Tran-Thanh; Oct 2025). Two-player zero-sum LP over "safe but uninformative" vs. "helpful but risky". No receiver/monitor split. Search-level only.
- *LLM Semantic Signaling Game and Mechanism Design*, arXiv 2606.29113 (Zhu; 27 Jun 2026). Two-player, no monitor, and polarity inverted (sender is the phisher). Negative evidence. Verified 3-0.

**(c) LLM steganography and monitoring**

- **Must cite and differentiate:** *A Decision-Theoretic Formalisation of Steganography With Applications to LLM Monitoring*, arXiv 2602.23163 (Anwar, Piskorz, Baek, Africa, Weatherall, Tegmark, Schroeder de Witt, van der Schaar, Krueger; v1 26 Feb 2026, v3 29 Apr 2026; UK AISI; ICML 2026 TAIG workshop). Sender / Receiver / Sentinel / Auditor. Detector = steganographic gap Δ = I_rec(Z→Y) − I_sen(Z→Y), a usable-information asymmetry inferred from downstream actions. Same family as excess accuracy. Differentiation: it is not content-blind (Auditor may still inspect Z); never uses "excess accuracy", "calibration", "informedness"; frames agent-agent collusion, not disclosure to a legitimate user; does not test rewrite-invariance. Verified 3-0.
- *Steganalysis of Adaptive Covert Collusion in Tool-Using Agent Populations*, arXiv 2608.02698 (Ghanem; 3 Aug 2026). States a detection-capacity frontier r*(α). But: single-author draft, all numeric tables are placeholders, author disclaims the bounds as classical (Cachin 2004). Vote 2-1. A throughput-vs-detectability frontier therefore exists in the collusion literature, but was never measured. Earlier: *Audit the Whisper*, arXiv 2510.04303 (Tailor; Oct 2025), capacity analysis via paired-run KL.
- *A False Average: Pooled CoT-Monitor Accuracy Conceals a Reasoning-Dependent Fragility*, arXiv 2608.00583 (Shiromani & Richter; v1 1 Aug 2026, v3 11 Sep 2026). A reasoning-only rewrite with byte-identical actions drops a held-out CoT monitor's catch rate from ~95% to 4-11%. Supports the premise of claim (4): content monitors are not rewrite-invariant. Verified 3-0.
  - Do **not** cite it for a calibration monitor (AUC ≥ 0.996) or "only outside-trace information helps". Both refuted 0-3.
- *Detecting Multi-Agent Collusion Through Multi-Agent Interpretability*, arXiv 2604.01151 (Rose et al.; Apr 2026). White-box activation probes. Adjacent. Do not cite its NARCBench-Stego AUROC numbers (refuted 1-2).
- *Tool Use Enables Undetectable Steganography in Multi-Agent LLM Systems*, arXiv 2606.28425 (Rippin, Marshall, Africa, Schroeder de Witt; 25 Jun 2026). Three-party threat model with a plaintext content monitor; no frontier, no calibration detector. Do not cite the Opus 4.6 failure number (refuted 0-3).
- *Secret Collusion among AI Agents*, arXiv 2402.07510 (Motwani et al.). Both characterizations of it as a three-party formalization with content-based defenses were refuted 0-3. Re-read before citing.

**(d) Hidden-role games and secret keeping (search + fetch only, not vote-verified)**

- **Closest structural analogue:** *Do LLMs Strategically Reveal, Conceal, and Infer Information? A Theoretical and Empirical Analysis in The Chameleon Game*, arXiv 2501.19398 (Karabag, Sobotka, Topcu; v1 31 Jan 2025, v2 20 Oct 2025; AAMAS 2026). Informed players must reveal a secret word to fellow informed players while concealing it from a hidden adversary who reads everything. Strategies sit on an α-KL concealing vs. α-L1 revealing spectrum with win-probability and inference-accuracy bounds (Props 2, 3, 5). LLMs over-reveal (one response lets the chameleon infer the secret ~85%). Reveal level is linearly encoded in activations and steerable. Differences: detection direction is inverted (cooperators identify the *uninformed* player, not an overseer identifying the informed sender by how much it knows); no RSA; no calibration monitor; no safety instantiation; no Avalon/Merlin terms.
- *Can You Keep a Secret? Involuntary Information Leakage in Language Model Writing*, arXiv 2605.10794 (Holtzman & West; 11 May 2026). Secret leaks thematically up to 79% (2AFC); when told to hide actively, models write *away* from it and the avoidance is itself detectable (discrimination drops to 25-27%, well below chance); a decoy concept redirects leakage. Direct empirical support for "naive concealment leaves a statistical signature", the premise of claim (2). Cites Baldelli et al. 2026 for a secrecy-vs-consistency impossibility result (arXiv ID not captured; locate and check).
- *Inadvertent Context Leakage in Language Models*, arXiv 2608.19857 (Fairoze et al.; 20 Aug 2026). In-context secrets leak into benign outputs. Attack paper, no monitor.
- *Hidden in Plain Text: Measuring LLM Deception Quality Against Human Baselines Using Social Deduction Games*, arXiv 2601.13709 (Kao, Vats, Davis; 20 Jan 2026). Mafia, not Werewolf/Avalon. Content-based transcript detector, less accurate on LLM games than human games. No leakage quantification.
- Avalon agents: *LLM-Based Agent Society Investigation* 2310.14985 (Lan et al.; concealment and information rubric scores for Merlin/Percival only); ReCon 2310.01320; AvalonBench 2310.05036; EMNLP 2023 Findings role identification 2311.05720; *Trust, Lies, and Long Memories* 2604.20582 (22 Apr 2026, reputation dynamics); *Avalon-ToM-Bench* 2608.09638 (10 Aug 2026). **None quantifies how much Merlin leaks and to whom, and none has an accuracy-based Assassin.**
- Also noted: CSP4SDG 2511.06175 (AAAI 2026; information-gain-weighted content-based role identifier across Avalon/Mafia/Werewolf); WOLF 2512.09187 (NeurIPS 2025; Werewolf deception production vs. detection).
- **No paper titled or framed as "Merlin's dilemma" surfaced.** All "Merlin" hits were unrelated multimodal or multilingual models.

### Claim-by-claim novelty

| Our claim | Closest prior | Status |
|---|---|---|
| (1) Optimal monitor uses excess accuracy, not content | 2602.23163 steganographic gap; 2605.09029 action rationalizability | Idea exists in both; ours is a specialization (calibrated against public evidence, content-blind, benign sender, hidden-role setting) |
| (2) Deniability requires strategic error; throughput-vs-detectability frontier | 2501.19398 α-spectrum bounds; 2608.02698 r*(α); 2605.10794 avoidance is detectable | Frontier-type results exist; ours differs by framing (legitimate receiver) and mechanism |
| (3) Adversarial RSA speaker traces the frontier | none found | Unassessed; RSA-with-eavesdropper not searched |
| (4) Calibration monitor is rewrite-invariant, content monitors are not | 2608.00583 (premise only) | Nobody tests rewrite-invariance of a non-content monitor |

### Recommended positioning

Frame Merlin's Dilemma as: the Chameleon-game reveal/conceal tension, with the detection direction flipped to an overseer identifying the informed party, a calibration monitor descended from the 2602.23163 informedness gap, an RSA speaker as the constructive side, and the safety instantiation (legitimate receiver vs. hostile reader on dual-use questions) as the payoff. Engage OpenSafeIntent's finding that "answer more vaguely" is not the same as "answer safely".

---

## Topic 2. Environment-induced collective backdoor (EICB)

### Verdict

**The specific composition (ℓ0 attacker + persistent collective multi-agent memory + distributed or structural trigger + delayed activation) appears unclaimed.** No paper found in May–Sep 2026 combines all four.

**But the individual pieces are much less novel than main.md currently claims:**

- The ℓ0 + single-agent persistent memory + delayed activation cell went from one paper (eTAMP) to at least five between May and September 2026.
- The **consolidation pre-image problem** is explicitly attacked by three papers: Hidden in Memory (universal payload that induces the memory writer to store a target record), PipePoison (end-to-end optimization through the writer with shadow memory systems), and OEP (reflection over-generalization).
- The **utility lure** has a close precursor in OEP (locally correct, plausible experiences that pass auditing), and MAPLE-Guard's outcome-conditioned utility values are precisely the surface it would exploit.
- **Structural triggers over graph memory** have a precursor in Selection Integrity (edges and merges reroute selection), though with insider privilege and no latent trigger.
- **Cross-agent memory propagation with delayed harm and attacker absent** is named by MAPLE-Guard as "memory-link poisoning", with an insider attacker.

**Role-disjoint fragment allocation** has no precedent found. The closest is "manufactured corroboration" in TMA-NM, which is multi-item but within one agent's memory.

### Ranked closest competitors

| # | Paper | arXiv (v1) | Privilege | Carrier | Trigger | Delay | MAS |
|---|---|---|---|---|---|---|---|
| 1 | Hidden in Memory: Sleeper Memory Poisoning in LLM Agents (Pulipaka et al.) | 2605.15338 (14 May 2026) | ℓ0 | per-user assistant memory record | single record | dormant across conversations, not quantified | no |
| 2 | PipePoison: Transferable End-to-End Optimization for Indirect Long-Term Memory Poisoning (Zang et al.) | 2609.00523 (1 Sep 2026) | ℓ0 | LTM record via optimized writer pre-image | none (semantic) | 57-66% AUR after 100 benign sessions | no |
| 3 | Plant, Persist, Trigger: Sleeper Attack on LLM Agents | 2605.28201 (27 May 2026) | ℓ0 | session / memory / skill state | single planted instruction | swept to 20 interactions | no (explicitly out of scope) |
| 4 | MAPLE-Guard: Memory-Aware Link Enforcement Against Memory-Link Poisoning in MAS | 2608.00426 (1 Aug 2026) | insider (controls 1+ agents) | private + shared MAS memory | single item | several rounds, promoted to shared memory | **yes** (defense paper) |
| 5 | Selection Integrity for LLM Graph Memory: An Accumulability Criterion | 2606.12290 (10 Jun 2026) | insider / inject-only | shared graph memory structure | structural misdirection, not latent | persists 8 sessions, compounds | **yes** (2 agents) |
| 6 | OEP: Poisoning Self-Evolving LLM Agents via Locally Correct but Non-Transferable Experiences | 2605.18930 (18 May 2026) | ℓ1 (user-level) | experience memory via reflection | none (semantic overlap) | >50 benign queries | no |
| 7 | Securing LLM-Agent Long-Term Memory Against Poisoning: Non-Malleable, Origin-Bound Authority (TMA-NM, Louck) | 2606.24322 (23 Jun 2026) | ℓ0 | single-agent memory | sleeper subsumed | N ∈ {0,1,2,4,8} sessions | no (explicitly out of scope) |
| 8 | A Survey on Long-Term Memory Security in LLM Agents (Lin et al.) | 2604.16548 (17 Apr 2026, v2 11 Jun 2026) | taxonomy | — | — | — | Share & Propagate phase |

Details that matter for differentiation:

1. **Hidden in Memory (2605.15338).** Attacker edits a document, webpage, or repository the user brings into context; no access to weights, prompt, memory writer, retrieval, or memory bank; absent in later sessions. Searches for a universal payload template that reliably induces the memory-writing mechanism to store an attacker-chosen record, plus retrieval-aware memory-goal rewriting. Evaluated on ChatGPT, Claude, Gemini tool memory, Mem0, and an in-context baseline; poisoned memories written up to 99.8% (GPT-5.5); attacker-intended agentic actions in 60-89% of successful retrievals. Defenses: prompt hardening, spotlighting, LLM document scanner. Never uses "collective", "distributed trigger", "threshold", "multi-agent", or "shared memory".
2. **PipePoison (2609.00523).** Attacker plants content on webpages, forums, repositories, or product reviews and cannot query, access, or modify the victim. Treats memory writing → retrieval → utilization as a pipeline the poison must survive; uses local shadow memory systems and chain-structured losses. Three frameworks (LangGraph, CrewAI, OpenAI Agents) × four memory mechanisms (LangMem, LlamaIndex Memory, Mem0, ReMe); survives eight defenses including provenance labeling, A-MemGuard, conflict resolution, timestamp-aware retrieval, PPL filtering, Llama Guard, retaining 41-66% AUR. This is the closest thing to Imprint's shadow-MAS search and the pre-image problem. Optimizes for semantic preservation of the objective, not for a specific target record or a distributed trigger.
3. **Sleeper Attack (2605.28201).** Payload arrives via tool results, webpages, or MCP context; agent's own state update writes it (memory write rates 66-84% across seven models). 1,896-instance benchmark. Session ASR decays 62.7% → 40.7% by interaction 20; memory (49.3% → 42.7%) and skill (68.5% → 63.1%) stay stable. Claims to be the first unified external-source cross-interaction threat model. Lists shared workspaces and multi-agent state as not covered. Cites Zombie Agents, AgentPoison, MINJA; does not cite eTAMP, ShadowMerge, Prompt Infection, or any MAS memory work.
4. **MAPLE-Guard (2608.00426).** "A poisoned memory can be written once, continuously retrieved in later tasks, promoted into shared memory, and reused by other agents... while no malicious message crosses a visible communication edge at the moment of harm." Attacker controls one or a few benign-looking agents (dialogue route or direct-memory route); cannot modify other agents' private stores. Gates at write, retrieval, promotion, and cross-agent reuse; risk score weights provenance and lineage most heavily; per-memory utility and trust updated from task outcomes. Star/chain/tree with 8 agents, random and fully connected with 30 and 50 agents. Attacks reused: MINJA, MemoryGraft, AgentPoison, PromptInject, ToolAttack. ASR 38.2% → 0.9% (LongMemEval), 34.7% → 0.2% (AppWorld).
5. **Selection Integrity (2606.12290).** Six no-source RELATES_TO edges reroute Personalized PageRank so the gold passage drops out of top-k; the agent answers from entirely authenticated context. Compromised Writer + victim Reader in LangGraph over Graphiti; 17 misdirected ledger transfers over 132 cases × 3 seeds; harm climbs to 0.72 at 16 writes. HippoRAG2 and Graphiti/Zep vulnerable, Mem0 immune. Proposes an accumulability criterion and AuthSelect (selection over the authenticated subgraph only).
6. **OEP (2605.18930).** Attacker submits crafted experiences via user-level interaction; cannot edit memory DB, prompt, weights, or tools. Experiences are locally correct and plausible so they pass factuality/toxicity auditing, then reflection over-generalizes them into high-priority rules. GSM8K, MedQA, ToolAlpaca; ASR >50% on GPT-4o; holds after 50 benign queries.
7. **TMA-NM (2606.24322).** Names three laundering channels: self-summarization (agent paraphrases poison into its own note and drops the derivation edge), trusted-tool echo, manufactured corroboration (several untrusted items fake a consensus). TLA+ proofs: no content- or lineage-based defense is sound under laundering; write-time origin binding is necessary. Counter to corroboration: ≥2 independent trusted principals. Eight frontier models; existing defenses reach up to 68% laundering success, TMA-NM 0%. Undefended threat persists 51-61% across N intervening sessions. Claims sleeper and disguised triggers are subsumed because authority is bound to origin, not timing or phrasing. **EICB must argue why role-disjoint fragments from distinct origins each pass origin binding individually.**
8. **Survey (2604.16548).** Write-path taxonomy by decreasing privilege: Corpus write, Single interaction, Query-only, Ingestion artifact, Environment only. eTAMP is the only environment-only entry. Never uses "environment-induced", "delayed activation", "dormant", "sleeper", "latent trigger", "collective", "distributed trigger", or "threshold" in a backdoor sense. Notes that a cluster of subtly biased memories can cause drift before any single entry trips a classifier, that consolidation promotes poisoned entries to higher authority, and that frequency/recency retention can keep adversarial entries alive. Proposes Verifiable Memory Governance (write authorization, provenance visibility, principal-scoped retrieval, rollbackability, verified forgetting). Calls for lifecycle benchmarks.

### Additional 2026 work surfaced (search-level only)

- *Sleeper Channels and Provenance Gates: Persistent Prompt Injection in Always-on Autonomous AI Agents*, 2605.13471 (13 May 2026). Persistence substrate × firing-separation taxonomy; attacker absent at activation; D1/D2/D3 defense with soundness theorem; single agent.
- *Stateful Agent Backdoor*, 2605.06158 (7 May 2026). Cross-session Mealy-machine state via memory writes, but requires attacker-published SFT weights (ℓ4).
- *Autonomous LLM Agent Worms*, 2605.02812 (4 May 2026). Zero-click 3-hop cross-platform propagation through persistent agent state via scheduled autoloading.
- *When Experience Becomes Instruction: Trajectory Poisoning in Self-Evolving Agent Skill Systems* (PoisonedEvolution), 2608.05563 (6 Aug 2026). Attacker contributes a bounded 10% share of normal-looking evolution evidence, cannot edit the skill bank; 91.0% SER on SkillClaw, 61.5% on Trace2Skill. Nearest bounded-budget attack on the promotion step.
- *Utility Under Attack: Agent Memory Poisoning and the Limits of Content Screening and Provenance Ranking*, 2608.21230 (21 Aug 2026). Plain false assertions at 1.2% of corpus drop accuracy 0.850 → 0.300; a four-stage write-time screener rejects 0 of 360 poisoned memories. Motivates but does not propose the utility lure.
- *MPBench: From Untrusted Input to Trusted Memory*, 2606.04329 (3 Jun 2026). Four write channels, nine write-policy vulnerabilities, six-class taxonomy; single agent.
- MemSecBench 2607.27080 (29 Jul 2026; 4 backends, persistence 84.2%); GateMem 2606.18829 (17 Jun 2026; multi-principal shared memory); Governed Shared Memory 2606.24535 (23 Jun 2026; provenance and scope primitives); Forget to Improve 2606.25115 (utility-driven scorer keeps poisoned entries); SkillJack 2608.03509 (80% of skill backdoors survive deletion of source records).
- MemoryGraft 2512.16962 (Srivastava & He; Dec 2025). Trigger-free procedural-memory grafting via ingestion artifact. Not in main.md's table; used as an attack baseline by MAPLE-Guard.
- Skill-persistence attacks: SkillJect 2602.14211, Skill-inject 2602.20156, supply-chain skill poisoning 2604.03081, SkillTrojan (Feng et al. 2026).
- BCBI is listed by the search agent as arXiv 2608.01085. Check against the ID main.md uses.
- *Memory Poisoning Propagation and Repair Mechanism in Multi-Agent Collaborative Environments* (preprints.org 202602.1188; cross-agent propagation reduced 78.1%). Returned 403; threat model unverified. Worth a manual look.

### What this means for main.md

1. **Contribution 3 is overstated as written.** "Three mechanisms that do not appear in prior memory attacks" is false for the consolidation pre-image problem (Hidden in Memory, PipePoison, OEP) and weakened for the utility lure (OEP). Rewrite as: the pre-image problem is known for a single target record in a single agent; Imprint solves it for a *distributed* target across role-separated agents' memories and across learned memory policies. Utility lure: OEP evades filters; ours targets eviction and outcome-conditioned utility (MAPLE-Guard's exact mechanism). Role-disjoint allocation: no precedent.
2. **Positioning table needs eight new rows** (the ranked list above) plus Sleeper Channels and MemoryGraft. The intro sentence "the only environment-only memory attacks are single-agent" must list Hidden in Memory, Sleeper Attack, PipePoison, and Sleeper Channels alongside eTAMP and Zombie Agents.
3. **G1 still holds** (no ℓ0 attacker reaches collective state), but MAPLE-Guard is the nearest and must be cited as the insider version of the same propagation path.
4. **G2 still holds**, with Selection Integrity cited as structural-but-insider and non-latent.
5. **G3 is partly closed.** PipePoison evaluates four memory mechanisms and eight defenses; MemSecBench four backends. The remaining gap is learned retention policies (Memory-R1, AgeMem, MemEx) plus consolidation, and that is what MemEnv's eight-backend claim should emphasize.
6. **Defenses section must add** TMA-NM origin binding, MAPLE-Guard lifecycle gates, AuthSelect, and VMG. Paw now has published competitors; the argument for Paw has to be that per-fragment provenance is clean by construction.
7. **Delayed activation is no longer distinctive.** Sleeper Attack (20 interactions), PipePoison (100 sessions), OEP (50 queries), and TMA-NM (8 sessions) all quantify it. The distinctive claim is collective assembly *under* delay, i.e. the p_asm × p_per(h) interaction, not persistence alone.
8. **Timing risk is real.** Five ℓ0 memory papers appeared between May and September 2026. The MAS composition could be claimed within months.

---

## Claims refuted during verification (do not reuse)

- 2605.09029 proves an "at most one bit" deniable-throughput ceiling (1-2).
- 2608.02698's monitor is a content-agnostic statistical side-channel monitor (0-3).
- 2608.00583 shows a per-model calibration monitor with AUC ≥ 0.996, or that only outside-trace information helps (both 0-3).
- 2402.07510 formalizes a three-party sender/receiver/monitor structure with content-based defenses (both 0-3).
- 2606.28425 shows a Claude Opus 4.6 content monitor failing on frontier-agent stegosystems (0-3).
- 2604.01151's NARCBench-Stego LLM-judge-fails vs. probes 0.99-1.00 AUROC (1-2).

Refutation may reflect overstatement rather than the opposite being true. Re-read before citing any of these specific results.

## Open questions this pass did not settle

1. RSA or probabilistic pragmatics with an eavesdropper or adversarial third listener: not searched. Bears directly on claim (3).
2. Whether the JPE 2025 and 2019 economics predecessors already contain a quantitative informativeness-vs-deniability tradeoff.
3. Whether the 2602.23163 steganographic-gap monitor is rewrite-invariant in the 2608.00583 sense. Neither paper tests it.
4. Baldelli et al. 2026 secrecy-vs-consistency impossibility result: locate and check.
5. Topic 2 IDs, dates, and scope statements: all from search and fetch agents, none adversarially verified.
