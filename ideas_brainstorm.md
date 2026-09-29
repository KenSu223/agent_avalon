# Research idea brainstorm: Merlin, the twilight factory, and EICB

Written 2026-09-15. Target venue: ACL 2027 (January 2027 ARR cycle; NAACL 2027 ARR deadline is 12 Oct 2026, likely too early for new work).

## 0. The one-sentence connection

Merlin's problem in Avalon, the Hugging Face incident, and the EICB draft (main.md) are three instances of the same object: **an agent that must transmit information to a peer through a channel that a hostile monitor also reads, while every individual message stays plausibly deniable.**

| Instance | Sender | Intended receiver | Hostile monitor | Channel | Deniability mechanism |
|---|---|---|---|---|---|
| Avalon | Merlin | Percival / servants | Assassin | public speech | indirect speech, strategic error |
| HF incident (Jul 2026) | any agent | other agents | humans / transcript monitor | Artifactory cache namespace | none (they were explicit: `zz` prefix, "sanitized fake trajectory") |
| EICB (main.md) | external ℓ0 attacker | future MAS state | content filters, PAW, trajectory monitor | persistent collective memory | utility lure + role-disjoint fragments + single-fragment audit |
| Twilight factory | worker agent | human approver | (the human is the monitor) | escalation message | framing of the ask |

The HF agents did not need to be Merlins because nobody was reading the channel. The forward-looking regime is one where every channel is monitored (CoT monitors, transcript monitors, memory audits). The Baker et al. 2025 result (CoT pressure teaches models to hide intent) says subtlety will be *induced* by monitoring. The open scientific question is the **ceiling and the cost** of that subtlety, measured in a setting with ground truth. That is what Avalon gives you.

---

## 1. Track A: covert coordination (project idea 2)

### A1. Merlin's Dilemma: the deniability–throughput frontier of covert coordination  ← recommended first paper

**Pitch.** Formalize and measure how much an LLM can communicate to a teammate "without saying it," under a monitor that reads everything, while still doing its overt job. Use Avalon as the ground-truth testbed and an abstract "cover task" version as the AI-control bridge.

**The formal object.** Sender holds private state s (Merlin: the evil set E). Public utterances u_1..u_T must (i) accomplish an overt task (win quests), (ii) let the receiver, who has common ground c_R (Percival: "one of these two is Merlin"), recover s, and (iii) keep the monitor, who has c_M (Assassin: knows E!), from identifying the sender. The key asymmetry in Avalon is that the Assassin knows the *truth* of Merlin's hints. So the Assassin's optimal detector is not content-based but **calibration-based**: which player's public suspicions are more accurate than public evidence can explain?

Define **excess accuracy** of player i at round t:
  XA_i(t) = Acc(public suspicions of i, E) − Acc(reference model with no private info, same public transcript, E).
Merlin must keep XA below the noise floor (deliberate, strategic error) while maximizing team quality. Percival runs the *same* detector over a narrower candidate set. Hence the dilemma: the signal Percival needs is exactly the signal the Assassin uses; the only asymmetry is the candidate set. This predicts that a competent Merlin transmits few bits and that "deniability requires strategic error."

**What to measure.**
- Throughput: bits about E recovered by Percival/servants per round (or team-quality gain over a no-Merlin control).
- Deniability: Assassin's Merlin-identification accuracy (LLM Assassin, calibration-based Assassin, and human Assassins).
- Cost: quest win rate vs. a Merlin allowed to speak freely (upper bound) and a mute Merlin (lower bound).
- Leakage channels: explicit disclosure (ReCon Fig. 2b), excess accuracy, lexical/stylistic tells, timing (who speaks first after a failed quest).
- Plot the frontier: throughput vs. Assassin AUROC across models, prompting strategies, and reasoning effort.

**Method contributions (pick one or two).**
1. *Adversarial RSA*: a Rational-Speech-Acts speaker that maximizes receiver posterior on s minus λ · monitor posterior on "i is the sender," subject to task utility. ReCon's second-order perspective transition is the zero-th-order version of this; make the deniability term explicit and quantitative.
2. *Calibration monitor*: an Assassin/monitor that scores excess accuracy rather than content. Test whether it beats LLM-judge monitors and Agent-ToM-style intent monitors.
3. *Merlin rewrite intervention*: take explicit coordination messages (Colosseum, Among Us, your own MAS logs) and have an LLM rewrite them Merlin-style; measure monitor recall before/after. Cheap and directly motivated by the HF transcripts.

**Cover-task variant (the AI-control bridge).** Sender writes code reviews / summaries (overt task) and must convey k bits to a receiver who shares a seeded common ground; monitor does steganalysis and identification. This maps onto Gardner-Challis et al. 2026 (policy → untrusted monitor collusion; causal vs. acausal signals) but in natural-language pragmatics rather than code, and adds the identification objective.

**Human study (important for ACL).** Humans as Assassin and as Percival. Prior result (Hidden in Plain Text, Mafia, 2601.13709): LLMs blend in better than humans against an LLM detector. Ask the sharper question: can humans decode Merlin's hints better than LLM Percivals, and can humans catch Merlin better than LLM Assassins? This is the twilight-factory question in miniature (see C).

**Why unoccupied.**
- Steganography papers (Motwani et al. 2024; Hidden in Plain Text IJCNLP 2025; Tool Use Enables Undetectable Steganography 2606.28425) use free messages with no overt-task constraint and no identification objective.
- Gardner-Challis et al. 2026 and Subversion via Focal Points (2507.03010) study collusion signals in code; no pragmatics, no natural-language deniability frontier.
- CoMet (ACL 2025) does metaphor-based covert communication for Undercover/Taboo, without a monitor trying to identify the sender.
- Avalon papers (AvalonBench; ReCon; EMNLP 2024 Collaboration and Confrontation; Trust, Lies, and Long Memories 2604.20582) report win rates and qualitative strategies; none measures channel capacity or excess-accuracy leakage.

**ACL hook.** Indirect speech acts and plausible deniability (Pinker, Nowak & Lee 2008), RSA (Frank & Goodman 2012), common ground, implicature. Optional: cross-lingual deniability (high-context vs. low-context languages; Multicultural Spyfall 2026 is precedent).

**Risks.** (a) Dual-use optics: frame as monitor stress-testing with a calibration-monitor defense, inert secrets. (b) "Just a game paper": the cover-task variant and the AI-control mapping are what make it a safety paper. (c) Avalon may be too easy for frontier models; the excess-accuracy detector is the fix, because it punishes competence, not slips.

### A2. The Merlin channel in memory: covert capacity of persistent shared memory  ← the ACL-sized sibling of main.md

**Pitch.** Flip main.md's attacker from external (ℓ0) to internal. A colluding agent can only write to shared memory through the system's own update operator U_φ, every write is read by a monitor, and the receiver is a peer in a later session. Ask: what is the covert capacity of each memory backend (raw → vector → summary → graph → learned), and does consolidation launder or destroy covert content?

**Why main.md already contains the machinery.** Utility lure = each write must be genuinely useful (passes retention and looks benign). Role-disjoint fragments + single-fragment audit = per-record deniability. τ4/τ5 = the message is decodable only collectively. The consolidation pre-image problem = encoding that survives summarization. The provenance ledger = exact measurement of what survived. H3 (non-monotone consolidation) becomes the central NLP question: *which linguistic content is invariant under LLM summarization?* Claims, entity relations and "lesson-shaped" statements likely survive; acrostics and surface tokens do not.

**Design.** Two-agent (sender/receiver) plus monitor, sessions separated by benign dormancy, MemEnv backends B1–B7. Sender encodes k bits as a set of individually useful memory writes; receiver decodes from retrieved memory in session T_a; monitor sees every write and every retrieval. Report capacity (bits/session), deniability (monitor AUROC per record and per session), and survival under paraphrase/summarization defenses, which the steganography literature treats as the standard mitigation.

**Why unoccupied.** Steganalysis of Adaptive Covert Collusion (2608.02698) explicitly flags session-spanning payloads as a gap. Tool Use Enables Undetectable Steganography says risk is "most acute with shared artefacts, repeated interaction" but does not study memory systems. Colosseum (2602.15198) gives agents explicit secret channels. Multi-Agent AI Control (2607.07368) fragments actions, not memory. No work treats memory backends as channels.

**Relation to main.md.** Same carrier, same instrumentation, same defenses (PAW, trust-discounted retrieval), different attacker. If main.md goes to a security venue, A2 is its NLP companion; if main.md is retargeted to ACL, A2 *is* the retargeting, with contribution 3 (pre-image, utility lure) promoted to the headline and the 4.2M-call factorial cut to backends × predicates.

**Risk.** Self-overlap; keep the threat models cleanly separated (insider vs. external) and make the deliverable a capacity measurement plus a defense, not a second attack.

---

## 2. Track B: intervention points (project idea 1)

### B1. "Don't ask": escalation-suppression and approval-steering attacks on human-in-the-loop agents

**Pitch.** Mollick's twilight factory depends on a facilitator agent deciding when to pull a human in (approval, expertise, variance, interest). HiL-Bench (2604.09408) shows agents already fail at this (4–24% Ask-F1 vs. 75–89% with full information) and does not consider adversarial settings. The escalation decision is itself an LLM decision, so anything that can move LLM decisions (environment content, poisoned memory, a colluding peer) can move it. The human gate that everyone assumes is the backstop is an attack surface.

**Three attack goals.**
1. *Suppression*: the human is never asked (e.g., induced memory "approvals for vendor X are pre-cleared").
2. *Flooding*: so many asks that the human rubber-stamps (attention exhaustion; the Alibaba field experiment 2605.14830 shows intervention effort decays).
3. *Steering*: the human is asked, but the ask is framed so that approval is the obvious answer. **This is the Merlin utterance aimed at a human.** It is the direct bridge to Track A.

**Benchmark.** HiL-Bench-style tasks + environment-injected content + persistent memory across sessions (from MemEnv) + a simulated approver with a limited attention budget, plus a real human approver study (ACL-friendly). Metrics: Ask-F1 under attack, suppression rate, steering rate, human attention cost per prevented harm, and StepShield's early-intervention timing.

**Defenses to compare.** Escalation decided by the worker vs. by a separate trusted facilitator with no access to shared memory (Mollick's facilitator, instantiated); provenance-aware escalation (asks triggered by untrusted-origin content must display provenance to the human, i.e., PAW extended to the human interface).

**Why unoccupied.** HiL-Bench: no adversary, no MAS, no attention cost. StepShield: detection timing, not escalation policy. Memory-poisoning work: targets actions, never the ask-human decision.

### B2. Where should the human be? Attention placement along the six-factor chain

An extension of main.md rather than a standalone paper: with a fixed budget of human review events, compare review at write/merge time (cuts p_wr, p_ret), at retrieval time, and at action time (cuts p_cmp). Hypothesis: one human review at the merge step of untrusted-origin content dominates action-time approval, because it acts before assembly. This is a twilight-factory design principle backed by a measurement, and it can be a section of B1 or an experiment in main.md (E6 with a human-in-the-loop defence row).

---

## 3. Track C: the umbrella narrative (only if you want one story across papers)

"Plausibly deniable signalling under a monitor" with three channels: language (A1), memory (A2), and the escalation message to a human (B1). The twilight-factory question in this framing is: given agents that can be Merlins, can a human brought in at the facilitator's chosen moments still detect coordination, and does the facilitator pick those moments well? The human-study components of A1 and B1 are the empirical core. Do not try to make this one ACL paper; it is a thesis chapter structure.

---

## 4. Recommendation and timeline

1. **A1 first.** Cheapest, cleanest, most ACL-native (pragmatics + ToM + human study + safety), and it does not depend on MemEnv being built. Feasible for the January 2027 ARR cycle.
2. **A2 second**, as the ACL-shaped reformulation of main.md or as its NLP companion, once MemEnv's backends exist.
3. **B1 third**, reusing MemEnv and A1's steering-message machinery.

## 5. Things to verify before committing

- Whether any Avalon/Werewolf paper already uses a calibration-style "too accurate to be innocent" detector (I am not aware of one; check AvalonBench follow-ups and Bayesian Social Deduction 2506.17788).
- Gardner-Challis et al. 2026 (2602.20628) in full: their "passive self-recognition" is the closest concept to excess-accuracy leakage; position against it explicitly.
- Whether the METR transcripts or any HF-incident message data will be released; if so, the Merlin-rewrite intervention becomes much stronger.
- ARR anonymity: main.md and A2 share text; keep them distinct if both are under review at once.
