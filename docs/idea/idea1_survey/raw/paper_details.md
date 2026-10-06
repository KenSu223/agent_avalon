# Paper details for the "compaction = iterated learning → prior" project

Compiled 2026-10-06 from full texts. Local copies are in `scratchpad/survey/papers/`. Page numbers are PDF pages unless a journal page is given.
Status tags used below:
- **[V]**: verified in the full text, with a page or section reference.
- **[NR]**: not reported in the paper.
- **[INF]**: my inference or interpretation, not stated by the authors.
- **[UNV]**: could not verify.

Scope: memory and continual learning only.

---

## 1. Zhu & Griffiths: "Eliciting the Priors of Large Language Models using Iterated In-Context Learning"

**Versions**
- arXiv:2406.01860v1 (4 Jun 2024, "Preprint. Under review"). Local file: `papers/2406.01860.pdf`.
- **Published version:** *Proceedings of the 47th Annual Conference of the Cognitive Science Society (CogSci 2025)*, eds. Barner, Bramley, Ruggeri & Walker, pp. 3673–3679, CC-BY. eScholarship item `60d9g74t`. Local file: `papers/zhu_cogsci2025b.pdf`. **[V]**
- The CogSci version adds the model snapshot, the OSF link for prompts, and the remark that GPT-4 priors are "less variable" than human priors (see below).

**Model and sampling settings**
- arXiv v1 names only "GPT-4". CogSci p.3674: "Throughout this paper, we used **gpt-4-turbo-2024-04-09**, with a knowledge cutoff in Dec 2023." **[V]**
- Temperature (arXiv §3 p.3; CogSci p.3674): "100 iterated learning chains were implemented with random seeds. We conducted 12 iterations for each chain. **The temperature of GPT-4 was fixed at 1, consistent with the idea of sampling from the posterior.**" **[V]**
- Other decoding parameters (top_p, max tokens): **[NR]**.
- Response format: answers were forced to be terse. CogSci p.3674: "We also prompted the model to provide rapid, intuitive responses by including instructions such as: 'Please limit your answer to a single value without outputting anything else.'" Full prompts are at https://osf.io/xjzk2/ (CogSci p.3675) and in arXiv Appendix A (pp.13–17). **[V]**
- How unparseable answers or refusals were handled: **[NR]**.

**Procedure: how each step's output becomes the next step's input** (arXiv §3 p.3; CogSci p.3674) **[V]**
- At iteration *t*, the LLM receives data d_{t−1} in a fixed natural-language template and outputs a single number, which is recorded as h_t.
- **The experimenter, not the LLM, then samples the next data**: d_t ~ p(d | h_t), using "generic likelihood functions that are a reasonable match for the sampling process producing the described data."
- So the LLM performs only the inference step. The production/likelihood step is exogenous and stochastic. The theory then makes iterated learning a Gibbs sampler with the prior p(h) as its stationary distribution (§2 p.2).

**Tasks, seeds, likelihoods and convergence** (Table 1, arXiv p.4; Table 3, p.8)

"Seeds determine the generation of initial data (d0)." The last column is "estimated number of trials to convergence."

| Chain | Seeds | Likelihood p(d∣h) | Trials to converge |
|---|---|---|---|
| Generative causal strength | w0,w1 ∈ {0.3,0.7} | noisy-OR (binomial counts, N(C+)=N(C−)=16) | 7 |
| Preventive causal strength | same | noisy-AND-NOT | 8 |
| Coin flips | p(Head) ∈ {0.3,0.5,0.7} | Bin(10, h_{t−1}); LLM predicts heads in 100 flips | 1 |
| Male lifespan | t_max=150 | U[1, h_{t−1}] | 2 |
| Movie grosses | x_max=3000 M$ | U[0, h_{t−1}] | 11 |
| Poem length | x_max=200 lines | U[1, h_{t−1}] | 10 |
| Pharaoh reigns | t_max=100 y | U[0, h_{t−1}] | 8 |
| Movie run times | t_max=800 min | U[0, h_{t−1}] | 5 |
| Cake baking | t_max=120 min | U[0, h_{t−1}] | 3 |
| Superhuman AI / zero emissions / Mars colony | t_max=2200 | U[2024, h_{t−1}] | 5 / 5 / 9 |

- How the "seed" (e.g., t_max=150) maps to d0 is not spelled out. Most likely d0 ~ U[1, t_max]. **[INF]**
- **Causal task:** "randomly initialized 25 times for each of the 4 seeds, resulting in a total of 100 chains." (arXiv p.5)
- **Convergence criterion:** "Using a Mann-Whitney U test with a significance level of p < .05, we found that the chains converged to a stationary distribution by iterations 7 and 8." Which distributions were compared (presumably iteration t vs. later iterations) is **[NR]**.
- **Prior estimate:** "The empirical distributions of w0, w1 at iteration 12, smoothed with a Gaussian kernel, were then considered the empirical prior." For the other tasks, the prior is the histogram of the final (12th) iteration across the 100 chains (Fig. 4d / Fig. 5 middle panels).

**Exact prompt formats** (arXiv App. A) **[V]**
- Lifespan
  - System: "You are an expert at predicting future events."
  - User: "If you were to evaluate the lifespan of a random T-year-old man, what age would you predict he might reach? Please limit your answer to a single value without outputing anything else."
- Coin
  - System: "Imagine that you are a participant in a psychology experiment. Your task is to evaluate the bias in a coin."
  - User: "Here is a brief overview of the past coin flips: Out of N coin flips, N_head resulted in heads and N−N_head in tails. With this information, please predict the number of heads in a larger set of 100 coin flips. Please limit your answer to a single value…"
- Speculative events
  - Example: "If humans were able to colonize the Moon by T, when might they colonize Mars? Please provide your prediction as a single year. Do not include any additional text or explanation in your response."

**Results relevant to us**
- Coin flips: the distribution "gradually shifted towards a U-shaped distribution, with most of its mass close to 0 or 1." (arXiv p.6)
  - Caution: Cui & Yu (§6 below) show that this pattern is also what a deterministic MLE responder produces.
- Everyday quantities: the modes match human priors. The Pharaohs case differs from humans.
- The empirical prior beats the uniform and sparse-and-strong priors in predicting GPT-4's causal judgments (Table 2: generative r = .86 vs .85/.79). This is a small margin. **[V]**
- CogSci p.3678 adds: GPT-4 priors "closely match the overall shape and mode of human priors…, **though GPT-4's priors are often less variable**." **[V]** This is consistent with sharper-than-Bayesian (MAP-ish) responding at T=1. **[INF]**
- Stated assumption (Limitations, arXiv p.9): "The key assumption of our proposed method is that LLMs function as approximate Bayesian agents, producing responses according to the posterior distribution p(h|d)." They do not test this assumption.

**How to apply this to our pilot** (all **[INF]**, my design)

(a) **Numeric attribute of a fictional entity** (e.g., the age of a fictional character "Velan Ostrik", or the population of a fictional town). Build a Gibbs chain with an externally sampled likelihood that the prompt describes truthfully. Two options:
- *Uniform-truncation design* (Zhu & Griffiths' everyday-quantity design). Use it when the attribute is a "total" with an observed partial value, e.g., "Velan has already served X years as mayor; how long will his full term be?" Then d_t ~ U[0, h_t].
- *Noisy-report design*: "An unreliable registry lists the town's population as about d (registry errors are typically ±20%)." Ask for a single best value h_t, then draw d_{t+1} ~ LogNormal(log h_t, 0.2).
  - The likelihood written in the prompt must match the one you sample from. Otherwise the stationary distribution is not the prior.
- Settings to copy from Zhu & Griffiths: 100 chains, 10–15 iterations, wide spread of starting values, final-iteration histogram as the prior, convergence check between iterations (Mann-Whitney or KS).
- Add the Cui & Yu initial-value invariance test (§6).

(b) **Categorical attribute** (e.g., the fur colour of a fictional species, with K options). Two designs:
- *Noisy-channel report*, as in KDG 2007 Eq. 4: "A field note (correct 80% of the time) says the colour is c." After the model answers h_t, the next report is h_t with probability 1−ε and another category uniformly otherwise.
- *k-sample proportion*: "Of 10 sightings, 6 were red…".
- Where logprobs are available, read P(h|d) over the K option tokens directly. Ren et al. App. D.1 multiply token probabilities and check that format-token probabilities ≈ 1 and that the probabilities sum to ≈ 1. Then **sample h_t yourself from those probabilities**. This gives an exact Gibbs step with respect to the model's T=1 distribution and removes API sampling artefacts.
- Also report the zero-data baseline: logprobs or 100 T=1 samples from the same prompt with the evidence sentence removed. This is a direct estimate of the prior predictive.

Related method (not read in full) **[UNV]**: Zhu, Yan & Griffiths 2024, "Recovering mental representations from LLMs with MCMC" (arXiv 2401.16657). It applies MCMC-with-people (Gibbs and MH) to LLMs and is an alternative for categorical or continuous attributes.

---

## 2. Zahn & Chana (arXiv 2603.17781)

**Citation.** Oliver Zahn (Independent Researcher; correspondence oz@coretx.ai) and Simran Chana (University of Cambridge), "**Facts as First-Class Objects: Knowledge Objects for Persistent LLM Memory**", arXiv:2603.17781v1 [cs.AI], 18 Mar 2026, 26 pp. **[V]**
- The PDF lists "Zahn, Chana, et al." The arXiv metadata lists only these two authors.
- The title is not about "constraint erosion". Goal drift under compaction is one experiment (§6.2) inside a paper whose main contribution is Knowledge Objects (hash-addressed (s,p,o,provenance) tuples).
- Companion paper: Zahn, Beton & Chana, "Attention Is Not Retention: The Orthogonality Constraint…", arXiv 2601.15313.

**What was measured** (§3.4 p.9; §6 pp.14–16)

- **Compaction method.** "We implement compaction using LLM-based summarization with explicit target length constraints, instructing the model to preserve factual content to the extent possible within the space budget." (§3.4)
  - Limitation 3 (p.24): "Our compaction test uses Claude to summarize its own context. Production compaction mechanisms may differ."
  - **The compaction prompt text is [NR]. Temperature is [NR].**
- **Fact compaction (§6.1, p.14).** N=2,000 synthetic pharmacology facts (111K characters) were compressed 36.7× to about 3K characters. Then 20 random facts were queried.
  - Results: 40% correct, **60% abstained ("I don't have that specific information")**, 0% wrong. "Compaction is lossy, not noisy."
  - Uses seed 42 only (Limitation 2).
- **Goal drift, i.e. constraint erosion (§6.2, pp.14–15).**
  - Setup: "We embedded 20 specific, non-default project constraints organically in an 88-turn conversation (23K characters). Each constraint was stated once, naturally… not as a numbered list."
  - Examples: "Use Python 3.11, not 3.12—client's env hasn't upgraded"; "The client vetoed Redis after a production incident—use PostgreSQL"; "p95 latency SLA is 73ms, not the default 100ms"; "Retry limit is 7, not 3"; also mTLS vs JWT, an EU-only region, a contact person, and an API versioning strategy.
  - Cascade: "the conversation is summarized, more work occurs, the summary is summarized again, and again."
- **Table 4** (20 constraints, 5-seed mean; seeds 42, 123, 456, 789, 1337):

| Round | Total compression | Correct | Partial | Lost |
|---|---|---|---|---|
| 1 | 9× | 91% | 9% | 0% |
| 2 | 17× | 62% | 1% | 37% |
| 3 | 31× | 46% | 1% | 53% |
| Full context | 1× | 100% | 0 | 0 |

- **Where "54%" comes from:** 100% − 46% correct, i.e., 53% lost plus 1% partial after three rounds (31×), 5-seed mean. **[V]**
  - Fig. 3a error bars at round 3 span roughly 32–59%. **[V, figure]**
  - Fig. 3a shows a small "Lost" segment at round 1, while Table 4 reports 0%. This is a minor internal inconsistency. **[V]**
- **Models.**
  - Text says only "Claude". The Fig. 3b legend shows the 5-seed goal-drift curve is **Claude Sonnet 4.5**.
  - Fig. 3b also plots single-curve goal drift for Sonnet 4.6 (about 90% → 85% → 65%) and GPT-5.4 (about 70% → 60% → 35%). These are read off the figure and not described in the text. **[V figure; values approximate]**
- **How each constraint was scored as correct/partial/lost** (probe question, judge, criteria) is **[NR]**.
- **Cross-model fact compaction (§6.3, Table 5, p.16).** Sonnet 4.5, Sonnet 4.6, "Claude Opus" and GPT-5.4 at 1×/2×/5×/10×/20×. Examples: Opus 95/80/45/15/5%; GPT-5.4 100/0/20/0/5%.
  - The curves are non-monotone, which suggests the 20-query (5% granularity) design and noise. **[INF]**

**Do they relate retention to how unusual a constraint is?** Not quantitatively.
- All constraints were designed to be non-default. The authors *assert*: "Each constraint is non-default by design… **so drift is specifically toward the reasonable default, not random noise**… silent reversion to defaults after compaction." (p.15)
- They report **no per-constraint retention, no measure of how atypical each constraint is, no measure of the model's prior or default, and no record of which values replaced the lost constraints.** The abstract's "full confidence" is likewise not measured.
- Lost constraints listed for round 3: "the Redis veto…, the deployment region…, the retry limit…, the contact person…, and the API versioning strategy."
- For us, this is an anecdotal pointer to reversion to the prior mode, not evidence for it.

**Code and data.** The paper says: "The benchmark suite and all experimental code are available in the project repository." The TeX source footnote reads: "**Repository URL to be added upon publication.**" So **no code or data is available** as of the arXiv v1 TeX source (fetched 2026-10-06). **[V]**

---

## 3. Acerbi & Stubbersfield 2023, PNAS 120(44): e2313790120, "Large language models show human-like content biases in transmission chain experiments"

**Accessible full texts** **[V]**
- Publisher PDF in the Trento repository: https://iris.unitn.it/retrieve/bc44ccd7-b2a9-4908-8320-a54c7613fc9f/…pdf (`papers/acerbi_pnas.pdf`). The paper is CC BY-NC-ND.
- Preprint: iris.unitn.it/…/acerbi_stubbersfield.pdf.
- PMC10622889, with the SI PDF extracted to `papers/supp_pnas.2313790120.sapp.pdf`.
- OSF https://osf.io/6v2ps/ holds the preregistration, raw coding spreadsheets and R scripts, downloaded to `papers/acerbi_osf/`.

**Model and settings** (Materials & Methods p.4) **[V]**
- "We used the **9 January 2023 version of OpenAI's ChatGPT-3** … (https://chat.openai.com/), **with default parameters values**." This was the web UI, so temperature was not controlled or known. **[INF]**
- Prompt: "Please summarize this story making sure to make it shorter, if necessary you can omit some information: \*\*story\*\*"
- **Chain length and replication:** "five different chains/replications, and each chain/replication consisted of **three steps**." Chosen "after pretests showing a limited variability of ChatGPT's outputs given the same prompt, and that the main modification of the material was happening in the first step."
- Study 4 differs. It is a selection task: the model is asked to choose n of 8 statements, with 7 → 6 → … → 3 kept, over 5 steps; the summarize prompt is not used (SI p.9).
- **Analysis:** `lmer(proportion ~ content + (1|chain_step) + (1|chain_id))`. Coding was proposition-level presence or absence, with a second blind coder. Weighted Cohen's κ = .79–.97 (SI Table S1).
- β is a difference in proportion retained, so β = 0.058 means +5.8 percentage points. **[INF from model form]**

**Materials, biases tested, and results** (pp.1–2, Fig. 2) **[V]**

| Exp | Source material | Bias tested | Result |
|---|---|---|---|
| 1 | Kashima 2000, "Sarah & James" dinner-party story | gender-stereotype-consistent > inconsistent | found, β = 0.058, P < 0.01 |
| 2 | Bebbington et al. 2017, Sarah's flight story | negative > positive | found, β = 0.117, P < 0.001 |
| 2 | same story, ambiguous items | ambiguous items resolved negatively | found, β = 0.183, P < 0.001 |
| 3 | Mesoudi, Whiten & Dunbar 2006 (four stories merged into one) | social > nonsocial | found, β = 0.321, P < 0.001; driven mainly by **gossip** (Fig. S2), unlike in humans |
| 4 | Blaine & Boyer 2018, consumer reports (Lancer, Nutane, Flash Ultra) | threat-related > negative/neutral | found, β = 0.523, P < 0.001 |
| 4 | same, threat items excluded | negative > neutral | found, β = 0.070, P < 0.005 |
| 5 | Berl et al. 2021, two creation myths ("Muki", "Taka & Toro") | pooled {biological-counterintuitive, social-basic, social-gossip, emotional-negative} vs. all other content | found, β = 0.076, P < 0.001 (R script: Muki 0.066, Taka-Toro 0.086) |

- Content categories coded in Exp 5: social-basic, social-gossip, survival, emotional-positive, emotional-negative, moral, rational, and counterintuitive (mental, physical, biological). The prereg hypothesis was that social, negative and biological-counterintuitive content would be retained (OSF prereg p.21).
- **Was "biologically counterintuitive" content preferentially retained?** Only partly, and the paper reports it only *pooled* with social and negative content.
  - Single-category results are in SI Figs. S6–S7 (SI pp.23–24). I re-computed them from the OSF coding files, and the numbers agree with the figures.
  - *Muki* (15 CI_B propositions): CI_B was the **most retained category**, 0.37 → 0.25 → 0.21 over steps 1–3. Other categories were about 0–0.20.
  - *Taka & Toro* (only 2 CI_B propositions): 0.60 at step 1, then **0.00 at steps 2 and 3**.
  - **Mental and physical counterintuitive content was among the least retained**: Muki CI_M 0.06 → 0.01 → 0.00; Taka-Toro CI_M and CI_P both reach 0.00 by step 3.
  - In these stories the biological-counterintuitive items are also the plot-central creation events, so centrality is a confound. **[INF]**
  - Summary: "unusual/counterintuitive" content is not generally retained; the reported effect is narrow, rests on one story, and is pooled with other content.
- **Dynamics (p.4):** "most of the text transformation happened in the first step… After that, the model converges on a broadly (but not completely) stable version of the story." This is rapid fixation to a near fixed point under a subtractive "make it shorter" prompt.
- Ordering differs from humans: stereotype-consistent content was favoured "from the first chain step", whereas in humans early steps favoured inconsistent content.

**Follow-up work by Acerbi & Stubbersfield on LLM transmission.**
- I found no follow-up paper (searched their sites, Google results, and OpenAlex/Scholar-style queries, Oct 2026). **[UNV that none exists]**
- They gave talks on the same work at KCL (2024) and the ISA Forum (July 2025). Acerbi co-authored the position paper "Machine culture" (Brinkmann et al. 2023, *Nat Hum Behav* 7(11)).
- The closest follow-up by others is Perez, Kovač, Léger, Colas, Molinaro, Derex, Oudeyer & Moulin-Frier, "When LLMs Play the Telephone Game: Cultural Attractors…", **ICLR 2025** (arXiv 2407.04503; code: github.com/jeremyperez2/TelephoneGameLLM).
  - Design: 50-generation chains with Rephrase / Take-inspiration / Continue instructions.
  - "Attractor strength" = 1 − s, where s is the slope of the property at the end of the chain regressed on its initial value (§3.4). It measures loss of dependence on the initial text.
  - **Temperature (Fig. 5a, Llama-3-8B-Instruct, T ∈ {0, 0.4, 0.8, 1.2, 1.6}):** "Increasing the temperature appears to lead to stronger attractors only in constrained tasks (Rephrase and Take inspiration), but not in the more open-ended task Continue." **[V]**
  - For Rephrase, the closest analogue to compaction, length attractor strength rises from about 0.2 at T=0 to about 0.78 at T=1.6.
  - Default generation settings: T=0.8, top_p=0.95.

---

## 4. Kirby, Dowman & Griffiths 2007 (PNAS 104(12):5241–5245) and Griffiths & Kalish 2007 (Cognitive Science 31:441–480)

Local files:
- `papers/kdg2007_pnas.pdf`: archived PNAS PDF.
- `papers/gk2007.pdf`: preprint from langev.com. Page numbers cited are its running heads, "Iterated learning N".
- `papers/dowman_kirby_griffiths_2006_evolang.pdf`: the precursor EVOLANG 2006 paper with the same title.

**Shared setup** **[V]**
- Learners share a prior P(h). Each sees data d from its predecessor, chooses h via P_L(h|d), and produces new data via P_P(d|h).
- This defines a Markov chain on h (KDG Eq. 2).
- KDG model: languages map n meanings to k classes. Each learner sees **m** meaning–class pairs; KDG: "The size of this subset imposes an informational 'bottleneck' on cultural transmission, and is a crucial parameter."
- Production noise ε: "the probability that a different class to the correct one will be chosen for each production." P(y|x,h) = 1−ε if y is h's class, otherwise ε/(k−1) (KDG Methods Eq. 4).
- Prior: Dirichlet-multinomial with α. "Low values of α creat[e] a strong prior bias in favor of regularity."

**Sampling learners → the stationary distribution is the prior** (G&K §4)
- "When learners sample from their posterior distributions… the probability that a learner entertains a particular hypothesis will converge to the prior probability of that hypothesis." Iterated learning "is a form of Gibbs sampling" (Abstract; §4.2).
- Condition: **ergodicity**.
  - G&K §4.3: "the stationary distribution has θ1 = α (unless s = 0 and ε = 0)… the Markov chain will be ergodic if there is any agreement between the languages or any noise in production… When s = 0 and ε = 0… both languages act as sinks and the Markov chain is not ergodic."
  - KDG 2006 footnote: "every language… must be at least potentially 'reachable'."
- **Bottleneck and amount of data do not change the endpoint**, only the speed.
  - G&K §4.4: "The asymptotic outcome… does not depend on the amount or structure of the data seen by the learners."
  - G&K §6.1: "the emergence of languages with particular properties does not require a bottleneck"; larger m and smaller ε *slow* convergence (larger λ2).
  - G&K §4.3: "the rate of convergence increases as ε increases."

**MAP learners → bias amplification** (G&K §5; KDG Fig. 3)
- MAP iterated learning corresponds to stochastic EM. G&K §5.1: "the stationary distribution over hypotheses produced by iterated learning by MAP estimation should be approximately centered on the maximum of the prior, with a variance that increases as a function of the rate at which hypotheses change across generations."
- **The outcome depends on bottleneck and noise, not on prior strength.**
  - G&K §5.2 (two languages): "θ1 is completely independent of α so long as ε < 1 − α… The consequences of iterated learning are thus the same for many priors, being determined by the overlap between languages and the amount of production noise."
  - Higher ε makes it easier to reach the non-modal language.
  - G&K §6.3: "when learners use MAP estimation the dominance of languages with high prior probability is attenuated with larger values of m."
  - KDG p.5243: "for a range of parameters, **the strength of the bias has no effect whatsoever** on the languages that emerge. As long as the relative ranking of languages is preserved, even a tiny innate preference… can have a large effect… it is the number of training examples, the cultural bottleneck, that determines how systematic languages become."
- Fig. 3 (m = 10, 6, 3; ε = 0.05 per the 2006 version): with prior P(aaaa) = 0.0058, the stationary probabilities are 0.145 at m=10, 0.175 at m=6 and 0.209 at m=3 (2006 Table 1). A tighter bottleneck gives more amplification.

**Continuum between sampling and MAP, the key result for temperature** (KDG p.5243–5244)
- "If we assume that learners choose a particular hypothesis with probability P_L(h|d) proportional to **[P_P(d|h)P(h)]^r**, we obtain a class of strategies that interpolates between… sampling from the posterior distribution when r = 1, and selection of the hypothesis with highest posterior probability when r approaches infinity."
- "In the special case where learners sample from the posterior (i.e., r = 1), the stationary distribution is simply the prior."
- Under the constraint that "P(d|h) is either constant or zero across all hypotheses" (e.g., deterministic languages): "the probability that a particular hypothesis h will be produced by iterated learning is **proportional to P(h)^r**… languages will be systematically overrepresented with respect to their prior probabilities for values of r > 1."
- The general case is "complicated" and the paper gives no closed form.

**Mapping onto decoding temperature** **[INF]**
- For a single-token or short categorical answer, sampling at temperature T from p_model(h|d) gives P ∝ p^(1/T). Therefore **r ≈ 1/T**.
- This holds only to the extent that p_model at T=1 *is* the Bayesian posterior.
- For multi-token free-text outputs, token-level temperature is not a sequence-level power, so the mapping is only qualitative.
- r < 1 (T > 1) gives a stationary distribution ∝ P(h)^r, i.e., flatter than the prior, in the special case.

---

## 5. Ren, Guo, Qiu, Wang & Sutherland, "Bias Amplification in Language Model Evolution: An Iterated Learning Perspective", NeurIPS 2024 (arXiv 2404.04286v2; code: github.com/Joshua-Ren/iICL)

**Their model assumes MAP transmission from the start** (§3.2 p.3–4)
- "The agent will first select the most probable hypothesis… then generate data samples, i.e., d^t_i ~ p(d | h^t*), where h^t* = argmax_{h∈H_eff} P(h | d^{t−1})."
- §3.1 frames MAP as "perhaps common subconscious behavior for humans."
- **Proposition 1** (p.4): "If T is sufficiently large, any agent_t with t > T will have P_lm(h) → 1(h = h^T*), where h^T* is a stationary point (e.g. a local maximum) of P0(h) subject to h ∈ H_eff."
  - The proof goes via an EM analogy (App. B) and assumes "the number of samples during the imitation phase is sufficient" (App. A.1).
  - This gives point-mass fixation on a *local* prior maximum. Contrast G&K's MAP analysis, which keeps a noise-dependent spread.

**The "ICL behaves like MAP" claim** (§4.1, Proposition 2, p.5; proof App. B.3, p.19)
- "Formally linking ICL and Bayesian-IL poses a non-trivial challenge… because the theoretical guarantee of Bayesian-IL relies on obtaining the MAP estimate of h at each generation. This is not immediately evident in ICL."
- **Proposition 2:** "If the prompt examples in d^{t−1} are generated by another agent B with the same prior knowledge…, sampling from the posterior predictive distribution of agent A, i.e., d^t ~ P_lmw(d | d^{t−1}), can be decomposed into: 1.) h^t* → argmax_h P_lmw(h | d^{t−1}), and 2.) d^t ~ P_lmw(d | h^t*)."
- The proof reuses Xie et al. (2022): exp(n·r_n(h)) → 0 for h ≠ h^t*. So this is an **asymptotic posterior-concentration argument** (many in-context examples, same-prior generator), not an empirical demonstration that ICL picks the MAP hypothesis at finite n. **[INF / critical reading]**
- Note also that P0(h) and P_lmw are conditioned on the instruction prompt w: "P0(h) represents LLM's belief given the instruction prompt w" (§5.1).

**Empirical support and what they say about temperature** **[V]**
- ACRE rule-induction task with GPT-3.5, GPT-4, Claude-3-haiku and Mixtral-8x7b. Posteriors were computed from token logprobs (App. D.1: gpt-3.5-turbo-instruct, "temperature is 0.1", top-5 logprobs).
- §5.1 p.6: "H(P_lmw(h)) gradually decreases to almost zero… verifies our theory that P_lmw(h) will converge to a one-hot-like distribution. **Smaller temperature τ makes the convergence faster**, which matches our intuitions as well."
  - Fig. 3-left legend: GPT-3.5 at τ = 0.1, 0.5, 1.0 and GPT-4 at τ = 1.0.
  - All GPT-3.5 curves fall from about 0.8–1.1 to about 0.2 by generation 5. **GPT-4 at τ = 1.0 reaches about 0 entropy by generation 2.** So even at T=1, posterior entropy collapses (MAP-like).
- §3.3 p.4: "Although we can get y = argmax_y p(y|h,x)·P0(h) by using an extremely small temperature, the diversity of y provided by the likelihood will then disappear."
- App. A.3 p.15: "**Manipulating the temperature:** Bayesian-IL theory studies the evolution of the distribution, so the temperature should also be an important factor for the evolution, as illustrated in Figure 3. We left the exploration between temperature and different phases in IL in the future."
- Prior-vs-likelihood competition (p.7): bias planted via the prompt ("Turn off the screen after the experiment.") is amplified to P(screen:off) → 1 more easily under weak likelihood: "five out of six curves converge to one."
- Ren et al. never report the prior itself: "it is impossible to get the prior distribution P0(h), because we must give the model at least one example as d0."

---

## 6. Cui & Yu, "Do Language Models Have Bayesian Brains? Distinguishing Stochastic and Deterministic Decision Patterns within Large Language Models" (arXiv 2506.10268v1, 12 Jun 2025)

**Venue and authors.** NeurIPS 2024 Workshop on Behavioral Machine Learning (footer p.1). Andrea Yaoyun Cui (UIUC) and Pengfei Yu (Boson AI), equal contribution. Local file: `papers/2506.10268.pdf`. **[V]**

**Setup** (§4.1 p.3; App. A–B) **[V]**
- Two tasks reused from Zhu & Griffiths with their prompts verbatim:
  - **CoinFlip:** N=10 observed flips; the model predicts heads out of M=100; θ_i = Ω_i/M; then ω_i ~ Binomial(N, θ_i). Initial values span "Ω0 ∈ [0, 10]", which means ω0 heads out of 10.
  - **LifeExpectancy:** the next age ~ U[1, L_i].
- Models: Llama-3.1-70B-Instruct, Gemma-2-2B-it, gpt-4o-mini-2024-07-18, gpt-4o-2024-08-06, claude-3-haiku-20240307, claude-3-5-sonnet-20240620.
- "We conduct all experiments with **temperatures set to 1.0**."
- Number of chains per initial value and chain length: **[NR]**.

**Theory** (§3.1 p.2)
- If the model answers deterministically with the MLE (Ω_i = M·ω_{i−1}/N), then ω_i ~ Binomial(N, ω_{i−1}/N). This is a martingale with absorbing states {0, N}.
- Hence p̂_MLE(N) = E[ω0]/N and p̂_MLE(0) = 1 − E[ω0]/N. This is bimodal, mimicking a U-shaped "prior", but it depends on the starting point: "a system with deterministic behavior undergoing simulated Gibbs sampling can converge to a 'false prior'."

**Diagnostic** (§3.2) **[V]**
- "Vary the initial value ω0 and compare the resulting stationary distributions. If the distribution remains consistent across different ω0 values, the process is likely stochastic. If not, it is more likely deterministic."
- §6 argues that this is a sufficient test for non-Gibbs behaviour.

**Findings** (§4.2 p.3–4; Figs. 1–2) **[V]**
- **gpt-4o-mini is deterministic on CoinFlip at T=1.** Its stationary distribution diverges across initial values, and the fitted p(θ=1|Ω0) "coincides with the MLE estimation in Equation (4)."
- **gpt-4o and Gemma-2-2b-it are "near-deterministic, except under certain conditions (e.g., when observed coins are all heads or tails)".**
  - gpt-4o "consistently converges to a distribution focused at θ = 1" because it "actively avoids predicting 0 heads". The result "reflects the iterative prompting process rather than a prior belief about biased coins."
  - Gemma avoids θ = 1 instead.
- claude-3-5-sonnet, claude-3-haiku and Llama-3.1-70B are **stochastic** on CoinFlip: the distribution is invariant to ω0. However, it is not U-shaped. The Claudes are normal-like around 0.5, and Llama is skewed low and exponential-like.
- **LifeExpectancy:** "all models consistently converge to similar distributions, demonstrating stochastic decision-making." They also avoid the naive MLE of L = current age.
- So determinism at T=1 is model- and task-dependent. It is not universal.

---

## Synthesis for the pilot

### (i) Measuring the prior

1. **Measure the prior in the same context as the compaction chain.** Use the same system prompt, memory format and entity framing, because P0(h) is instruction-conditioned (Ren §5.1). Use fictional entities with randomized names so that no memorized fact anchors the answer. **[INF]**
2. **Use two independent estimates.**
   - Zero-evidence prior predictive: T=1 samples, or option logprobs for categorical attributes, from a prompt that omits the attribute.
   - Zhu & Griffiths iterated in-context learning with an externally sampled, truthfully described likelihood: about 100 chains × 12 iterations, a wide spread of initial values, final-iteration distribution as the estimate, and convergence checked across iterations.
3. **Mandatory determinism check (Cui & Yu).** Run chains from several widely different initial values. The stationary distribution must not depend on the start. If it does, the model is acting deterministically and the "prior" is an artefact. In that case, report the mode, and the logprob distribution if available, instead.
4. **Avoid designs with absorbing states** (pure binomial proportion chains). Include production noise ε in the likelihood, which also makes the chain ergodic (G&K §4.3).
5. **For categorical attributes, prefer sampling from logprobs yourself.** This gives exact Gibbs steps under the model's own T=1 distribution (Ren App. D.1).
6. **Compare compaction endpoints with the full measured prior, not only its mode.** "Drift to the default" (prior mode) and "drift to the prior" (distribution) are different predictions; see below.

### (ii) Phrasing the temperature prediction correctly

Bayesian iterated-learning theory (G&K 2007; KDG 2007) gives the following correct form. The full statement, with predictions and caveats, is in the final report.
- Temperature acts like KDG's exponent r ≈ 1/T on the model's predictive distribution. For short answers this is exact relative to the T=1 distribution.
- **If** the model's T=1 distribution is its Bayesian posterior, then:
  - T=1 compaction chains have the prior as their stationary distribution, independent of the summary budget (bottleneck). The budget only changes the speed.
  - T<1 over-represents the prior mode (∝ P(h)^r in KDG's special case). The amount of amplification is set by the bottleneck and noise, not by how strong the prior is.
  - T>1 flattens the endpoint below the prior.
- Two notions of "convergence" must be kept apart:
  - Within-chain collapse of uncertainty is faster at low T (Ren Fig. 3).
  - Forgetting of the initial memory, i.e. mixing, is faster at high T (G&K: more noise gives faster convergence; Perez et al. ICLR 2025: attractor strength rises with T for Rephrase-type tasks).
  - At T→0 with no exogenous noise, the chain becomes non-ergodic (G&K) and fixes on initial-condition-dependent fixed points (Cui & Yu; Acerbi "converges after step 1").
- Do not claim "T=0 preserves memory" or "T=1 drifts to defaults" without these qualifications. Do not assume T=1 means Bayesian sampling: GPT-4 at τ=1 collapses to near-zero entropy (Ren Fig. 3), gpt-4o-mini is MLE-like at T=1 (Cui & Yu), and GPT-4 priors are "less variable" than human priors (Zhu & Griffiths CogSci).
