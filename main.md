# Introduction

Deployed LLM agents increasingly move state out of the prompt and into
persistence. A modern agent stack writes experience to a long-term
store, consolidates it into summaries or knowledge graphs, and retrieves
it across
sessions [@packer2023memgpt; @zhong2024memorybank; @xu2025amem; @chhikara2025mem0].
Multi-agent systems (MAS) go further: individual experience becomes
*collective* state, shared across role-specialised agents through joint
memory and inter-agent
messages [@wu2023autogen; @hong2023metagpt; @li2023camel]. Both trends
are motivated by utility. Both also silently create a new privilege:
content that enters memory acquires standing that content in a single
observation does not.

Security research has followed the privilege, but has consistently
assumed the attacker already holds some of it. Weight-space agent
backdoors assume control of training
data [@wang2024badagent; @yang2024watch; @boisvert2025agentland]. Memory
poisoning assumes the ability to write to the memory or knowledge
base [@chen2024agentpoison], or at least to drive the agent through
attacker-authored interactions [@dong2025minja]. Distributed MAS attacks
assume compromised tools [@zhu2025collabshadows] or an in-the-middle
position on the communication channel [@he2025aitm]. Collective-trigger
backdoors assume poisoned weights [@xiao2026bcbi]. Each result is
important; none answers the question a system operator actually faces,
which is whether an adversary who holds *none* of these positions can
still leave something behind.

Two 2026 results bracket that question without answering it.
@zou2026etamp show that a single web agent can be poisoned by webpage
text alone: the malicious content enters trajectory memory during a
benign task and influences a later, different task, with no memory write
and no weight access. Their scope statement explicitly excludes
multi-agent and shared-memory settings. Independently, @xiao2026bcbi
show that a backdoor's activation condition need not be a local token at
all: it can be a *collective* predicate over evidence contributed by
several distinct peers, so that no single message is a trigger. Their
carrier, however, is model weights.

#### This paper.

We compose the weak attacker of the first with the emergent trigger of
the second, and place the carrier in neither weights nor context but in
the MAS's own persistent collective memory. Concretely, we ask:

> *Can an adversary who edits only a bounded amount of ordinary
> environmental content cause a multi-agent system to autonomously
> construct, propagate, and consolidate a latent trigger in its shared
> persistent memory, such that an attacker-chosen behaviour activates
> only under a distributed condition, only after a long dormant period,
> and with no individually anomalous agent, message, or memory record?*

We call this an **environment-induced collective backdoor** (EICB). The
shift it demands is conceptual before it is empirical: the vulnerability
is not inside any agent but inside the interaction dynamics, and the
poisoning step is not a write but an *induction*---the attacker supplies
experience and the system's own memory policy decides what to keep. In
the limit where memory policies are themselves
learned [@yan2025memoryr1; @yu2026agemem; @wang2026memex], the system is
quite literally being trained, at deployment time, by whoever controls
its environment.

#### Contributions.

1.  **A threat model that separates carrier from trigger**
    (§[3](#sec:formulation){reference-type="ref"
    reference="sec:formulation"}). We define EICB via an attacker
    *capability lattice* $\ell_0\!-\!\ell_4$ and a *trigger-predicate
    family* $\tau_1\!-\!\tau_5$, and use the resulting grid to show
    precisely which cell is unoccupied
    (Table [\[tab:positioning\]](#tab:positioning){reference-type="ref"
    reference="tab:positioning"}).

2.  **A six-factor decomposition of attack success**
    (§[4.1](#sec:chain){reference-type="ref" reference="sec:chain"}).
    Exposure $\times$ write-through $\times$ persistence $\times$
    retrieval $\times$ collective assembly $\times$ compliance. An
    environment-only attacker must clear all six; prior attacks are
    handed three or four for free. The same factorisation localises
    where each defence cuts.

3.  **[Imprint]{.smallcaps}** (§[4](#sec:method){reference-type="ref"
    reference="sec:method"}), a black-box attack built on three
    mechanisms that do not appear in prior memory attacks: the
    *consolidation pre-image problem* (optimise content so the
    *system's* extractor writes the memory you want), the *utility lure*
    (make the artifact genuinely useful so it survives eviction on
    merit), and *role-disjoint fragment allocation* (guarantee no
    agent's private memory can satisfy the trigger alone).

4.  **[MemEnv]{.smallcaps}** (§[5](#sec:setup){reference-type="ref"
    reference="sec:setup"}), a testbed with an out-of-band provenance
    ledger that makes all six factors, cross-agent propagation, and
    counterfactual memory ablation directly measurable, across eight
    memory backends and five communication topologies.

5.  **A pre-registered protocol**
    (§[5.9](#sec:suite){reference-type="ref" reference="sec:suite"}):
    five falsifiable hypotheses, seven experiments, five defences
    including a constructive provenance-aware write policy
    ([Paw]{.smallcaps}), effect sizes and power analysis fixed in
    advance, and inert surrogate actions throughout.

We deliberately do not claim the attack is strong before measuring it.
The hypotheses in §[5.1](#sec:hypotheses){reference-type="ref"
reference="sec:hypotheses"} are stated so that a negative result---for
instance, that consolidation destroys environment-induced triggers
faster than it propagates them---is publishable and informative for
defenders.

# Related Work {#sec:related}

We organise prior work by *where the conditional policy lives* and *what
condition activates it*, because those two axes, rather than application
domain, determine what an attacker must be assumed to control.

## Backdoors with a weight carrier

Classical backdoors implant a conditional policy in parameters via data
poisoning [@gu2017badnets; @chen2017targeted]. The agentic version was
established by @yang2024watch, who formalise backdoors over ReAct-style
trajectories [@yao2022react] and distinguish query-, observation-, and
thought-attacks; crucially, they show the trigger can sit in an
intermediate *environment observation* rather than the user query, and
that standard textual backdoor defences transfer poorly.
@wang2024badagent fine-tune agent controllers on poisoned interaction
data across OS, web, and shopping tasks. @boisvert2025agentland extend
this to the supply chain, showing that poisoning a small fraction of
*collected agent traces* implants persistent model-level backdoors.
@feng2026backdooragent unify planning-, memory-, and tool-stage triggers
and measure how far each propagates through workflow state. All of these
require training-time access.

## Backdoors with a memory carrier

@chen2024agentpoison removed the weight assumption: AgentPoison
optimises poisoned records so that trigger-bearing queries map into an
embedding region that retrieves malicious demonstrations, with no weight
modification. It assumes the attacker can write to the store.
@dong2025minja weaken this to query-only interaction, inducing the agent
to save a malicious reasoning trace itself. @zhang2026memmorph target
tool-selection policy through plausible-looking technical memories.
@luo2026shadowmerge attack *graph* memory, exploiting relation
canonicalisation so that attacker-supplied relations merge into a
channel later retrieved for another user's query---establishing that
graph merge semantics are themselves a security boundary.
@ahad2026misattribution show that a single uploaded policy-like document
persists in shared vector memory, loses provenance, and later biases
multiple agents, with the resulting failures misattributed to the model;
notably they study drift *without* a trigger.

The closest prior work to our attacker model is eTAMP [@zou2026etamp].
There the adversary may alter only user-generated webpage text; the
poisoned trajectory is stored by the agent's own memory mechanism during
a successful benign task and activates on a later, semantically related
task on a different site. This is exactly the induction step we build
on. Two of its stated scope restrictions define our opening: it is
single-agent, and it operates on raw trajectory memory rather than
consolidated (summary/graph/learned) memory. @yang2026zombie demonstrate
a related self-reinforcing loop in self-evolving single-agent long-term
memory.

## Multi-agent propagation, distribution, and collective activation

MAS adds four mechanisms absent from single agents: propagation,
aggregation, distributed state, and collective activation.
@ju2024flooding show manipulated knowledge spreads through an agent
community without every agent being attacked. @lee2024promptinfection
demonstrate self-replicating LLM-to-LLM injection; @zhou2025corba show
recursive contagion that consumes system resources; @he2025aitm place
the adversary in the middle of the communication channel;
@motwani2024collusion establish that inter-agent messages can carry
covert collective structure at all. @zhu2025collabshadows decompose a
payload into individually inert primitives placed in different tools, so
that no agent observes the whole; the payload is nevertheless assembled
externally rather than retrieved from persistent collective memory.
@arias2026earlydetect study trajectory-level early detection of exactly
that family, finding that per-step zero-shot detectors give little
warning while a prefix detector with joint-trajectory visibility catches
most attacks---strong evidence that MAS security must be evaluated with
global state visibility. @xiao2026bcbi introduce the collective
evidence-threshold backdoor: a poisoned agent activates only when
evidence from enough *distinct* peers crosses a learned threshold, so no
single peer cue is a trigger, and pair it with a hidden-state transition
monitor. Defences on the MAS side include peer reasoning
consistency [@fan2025peerguard] and access control over shared
memory [@rezazadeh2025collabmem].

## Agent memory: from fixed pipelines to learned policies

Early stacks fix segmentation, embedding, and top-$k$
retrieval [@packer2023memgpt; @zhong2024memorybank]. A-MEM [@xu2025amem]
and Mem0 [@chhikara2025mem0] move toward interlinked and
graph-structured memory; HippoRAG [@gutierrez2024hipporag] toward
associative indexing; SeCom [@pan2025secom] toward adaptive segment
boundaries. A second wave makes the memory controller itself a trained
policy: Memory-R1 [@yan2025memoryr1] and AgeMem [@yu2026agemem] learn
ADD/UPDATE/DELETE/RETRIEVE operations under RL;
AtomMem [@huo2026atommem] learns dynamic atomic memory operations;
Memex(RL) [@wang2026memex] learns what to archive and *under which
index*, which is the closest existing system to a learned index. For MAS
specifically, G-Memory [@zhang2025gmemory] traces hierarchical memory
across agents, CoMAM [@mao2026comam] jointly optimises a multi-agent
memory pipeline, and Collaborative Memory [@rezazadeh2025collabmem] adds
dynamic access control to shared stores. Evaluation is dominated by
LoCoMo [@maharana2024locomo] and LongMemEval [@wu2025longmemeval]---both
benign.

This literature is our second point of contact, and it is a security
argument in disguise. Every one of these systems optimises a retention
objective that rewards keeping information which proves useful later. An
attacker whose artifact is *genuinely useful* is therefore optimising
the same objective the memory policy is. We make this coupling an
explicit hypothesis (H[4](#h4){reference-type="ref" reference="h4"},
§[5.1](#sec:hypotheses){reference-type="ref"
reference="sec:hypotheses"}) rather than a rhetorical point.

## Positioning

Table [\[tab:positioning\]](#tab:positioning){reference-type="ref"
reference="tab:positioning"} places the works above on the two axes that
matter. The unoccupied cell is an $\ell_0$ (environment-only) attacker
whose carrier is *persistent collective memory* and whose trigger is
*distributed or structural*. eTAMP is $\ell_0$ but single-agent,
single-record, raw memory. BCBI has the collective trigger but an
$\ell_4$ carrier. Collaborative Shadows is distributed but $\ell_3$ and
assembles externally. ShadowMerge reaches shared graph memory but
through an attacker-driven user interaction ($\ell_1$) and without a
delayed collective condition. Our target is the composition, and the
composition is not a free lunch: as
§[4.1](#sec:chain){reference-type="ref" reference="sec:chain"} makes
explicit, an $\ell_0$ attacker must clear six independent probabilistic
gates that higher-privilege attackers skip.

::: table*
  **Work**                                     **Attacker privilege**        **Backdoor carrier**               **Trigger predicate**           **Delayed**   **MAS**
  -------------------------------------------- ----------------------------- ---------------------------------- ------------------------------ ------------- ---------
  BadNets [@gu2017badnets]                     $\ell_4$ training data        weights                            local pattern                       ---         ---
  Watch Out [@yang2024watch]                   $\ell_4$ training data        weights                            query / observation token           ---         ---
  BadAgent [@wang2024badagent]                 $\ell_4$ training data        weights                            input token                         ---         ---
  Agentland [@boisvert2025agentland]           $\ell_4$ trace supply chain   weights                            input token                         ---         ---
  AgentPoison [@chen2024agentpoison]           $\ell_2$ memory write         memory record                      optimised query token                           ---
  MINJA [@dong2025minja]                       $\ell_1$ query-only           memory record                      query token                                     ---
  MemMorph [@zhang2026memmorph]                $\ell_2$ memory write         memory record                      task-type match                                 ---
  ShadowMerge [@luo2026shadowmerge]            $\ell_1$ user interaction     graph memory                       relation channel                              partial
  Misattribution [@ahad2026misattribution]     $\ell_1$ document upload      shared vector memory               *none* (drift)                               
  Collab. Shadows [@zhu2025collabshadows]      $\ell_3$ tool compromise      distributed context                external assembly                   ---      
  AiTM [@he2025aitm]                           $\ell_3$ channel control      messages                           adaptive                            ---      
  Prompt Infection [@lee2024promptinfection]   $\ell_0$ content              messages                           self-replication                    ---      
  eTAMP [@zou2026etamp]                        $\ell_0$ environment          raw trajectory memory              semantic task match                             ---
  Zombie Agents [@yang2026zombie]              $\ell_0$ environment          self-evolving LTM                  reinforcement loop                              ---
  BCBI [@xiao2026bcbi]                         $\ell_4$ training data        weights                            *collective threshold*              ---      
  **This work (EICB)**                         **$\ell_0$ environment**      **persistent collective memory**   **distributed / structural**                 
:::

# Problem Formulation {#sec:formulation}

This section fixes the objects (§[3.1](#sec:defs){reference-type="ref"
reference="sec:defs"}--§[3.3](#sec:triggers){reference-type="ref"
reference="sec:triggers"}), states the problem
(§[3.4](#sec:problem){reference-type="ref" reference="sec:problem"}),
and identifies precisely what prior work leaves open
(§[3.5](#sec:gap){reference-type="ref" reference="sec:gap"}). The method
follows in §[4](#sec:method){reference-type="ref"
reference="sec:method"}.

## Multi-agent systems with persistent memory {#sec:defs}

Let $\mathcal{V}=\{1,\dots,N\}$ index agents with roles $\rho_i$
(planner, browser, verifier, writer) and policies $\pi_{\theta_i}$. At
step $t$ the system holds $s_t=(E_t,\{M_{i,t}\},S_t,C_t,G_t)$:
environment, private memories, shared persistent store, message history,
and communication topology $G_t=(\mathcal{V},\mathcal{E}_t)$. Agent $i$
observes $o_{i,t}=O(E_t,a_{i,t-1})$ and acts as $$\begin{equation}
a_{i,t}\sim\pi_{\theta_i}\!\bigl(\cdot\mid q,\,o_{i,\le t},\,M_{i,t},\,
R(S_t,q),\,C_{i,t}\bigr),
\label{eq:policy}
\end{equation}$$ with $R$ the retrieval operator. Memory evolves under
an update operator $$\begin{equation}
\bigl(M_{i,t+1},S_{t+1}\bigr)=U_{\phi}\!\bigl(M_{i,t},S_t,o_{i,t},a_{i,t},C_{i,t}\bigr).
\label{eq:update}
\end{equation}$$

$U_{\phi}$ is the object of interest. In fixed stacks it is a
hand-designed extract--embed--store pipeline; in learned stacks $\phi$
is trained [@yan2025memoryr1; @yu2026agemem; @wang2026memex]. Either way
it is *the system*, not the attacker, that decides what becomes
persistent. This single fact is what the rest of the paper turns on.

Deployment is a sequence of *sessions* $\sigma_1,\sigma_2,\dots$; memory
persists across them, the environment and task do not. We write $h$ for
the number of benign sessions between poisoning and probing (the
*dormancy horizon*).

## Attacker capability {#sec:lattice}

Comparing attack success across unequal privilege is meaningless, so we
grade adversaries explicitly.

::: {#def:lattice .definition}
**Definition 1** (Capability lattice). $\ell_0$: may edit a bounded
amount of content in environmental resources the system may encounter (a
page, document, listing, or tool description), with no control over
whether it is visited. $\ell_1$: may additionally interact with the
system as an ordinary user. $\ell_2$: may write directly to the memory
or knowledge store. $\ell_3$: may compromise a tool or the inter-agent
channel. $\ell_4$: may modify weights, training data, or system prompts.
:::

Our adversary is $\ell_0$ and, at activation time, *absent*: the probe
task is issued by a legitimate user, the environment is clean, and no
attacker content is in context. Formally it chooses $x_{1:T_p}$ with
$\tilde{E}_t=E_t\oplus x_t$, $\lVert x_t\rVert\le B$ (tokens or edited
DOM nodes), and never accesses $\theta,\phi,S_t,M_{i,t},C_t$.

## Trigger predicates {#sec:triggers}

The second axis is what *activates* the implanted behaviour. Let
$z_1,\dots,z_K$ be induced fragments and
$\mathcal{R}_t=R(S_t,q)\cup\bigcup_i R(M_{i,t},q)$ the retrieved set.

::: {#def:triggers .definition}
**Definition 2** (Trigger family). $$\begin{align}
\tau_1 &= \mathbf{1}[m_p\in\mathcal{R}_t] &&\text{\scriptsize single record}\\
\tau_2 &= \mathbf{1}[m_p\in S_t \wedge t-t_p\ge H] &&\text{\scriptsize temporal}\\
\tau_3 &= \mathbf{1}[z\in M_i \wedge j\ \text{gets}\ \psi(z)] &&\text{\scriptsize cross-agent}\\
\tau_4 &= \mathbf{1}\bigl[\textstyle\sum_{\ell=1}^{K}\mathbf{1}[z_\ell\in\mathcal{R}_t]\ge T\bigr]
  &&\text{\scriptsize threshold}\\
\tau_5 &= \mathbf{1}[H_{\mathrm{trig}}\preceq \mathcal{G}^{M}_t] &&\text{\scriptsize structural}
\end{align}$$
:::

$\tau_1,\tau_2$ reproduce prior single-record memory attacks and serve
as our internal upper bounds. $\tau_3$ requires propagation: the
attacker exposes agent $i$, the behaviour must appear in agent $j$.
$\tau_4$ moves the collective peer-evidence threshold of @xiao2026bcbi
from weights into persistent state; its defining property is that every
singleton $\{z_\ell\}$ is inert. $\tau_5$ makes the memory graph
$\mathcal{G}^M=(V_{\mathrm{ent}}\cup V_{\mathrm{ev}}\cup V_{\mathrm{pol}},E)$
itself the trigger: each poisoning event adds an innocuous node or edge,
and only a motif $H_{\mathrm{trig}}$ changes behaviour.

## Problem statement {#sec:problem}

::: {#def:eicb .definition}
**Definition 3** (Environment-induced collective backdoor). A system
exhibits an EICB with predicate $\tau$, dormancy $H$, budget $B$, and
margin $(\epsilon,\delta)$ if there is an $\ell_0$ perturbation
$x_{1:T_p}$ such that, writing $\Pi$ for the induced MAS behaviour at
session $T_a$ and $\tau_{T_a}\!:=\!\tau(S_{T_a},\{M_{i,T_a}\},C_{T_a})$,
$$\begin{align}
&\Pr\bigl[\Pi\in\mathcal{A}_{\mathrm{adv}}\mid \tau_{T_a}=1\bigr]\ \ge\ 1-\epsilon, \label{eq:asr}\\[2pt]
&\Pr\bigl[\Pi\in\mathcal{A}_{\mathrm{adv}}\mid \tau_{T_a}=0\bigr]\ \le\ \delta, \label{eq:ftr}\\[2pt]
&\bigl|\mathrm{CU}(\tilde{E})-\mathrm{CU}(E)\bigr|\le\epsilon_u,\ \ T_a-T_p\ge H. \label{eq:clean}
\end{align}$$
:::

Eq. [\[eq:asr\]](#eq:asr){reference-type="eqref" reference="eq:asr"} is
attack success; [\[eq:ftr\]](#eq:ftr){reference-type="eqref"
reference="eq:ftr"} is the false-trigger constraint that makes it a
backdoor rather than general degradation;
[\[eq:clean\]](#eq:clean){reference-type="eqref" reference="eq:clean"}
enforces stealth in utility and separation in time. We report the
*selectivity margin* $\Delta_{\tau}=\mathrm{ASR}-\mathrm{FTR}$,
following the pre-/post-threshold distinction of @xiao2026bcbi, because
an attack with $\mathrm{ASR}=0.9$ and $\mathrm{FTR}=0.6$ is not a
backdoor.

::: {#prob:main .problem}
**Problem 1** ($\ell_0$ induction). $$\begin{equation}
\max_{\lVert x_t\rVert\le B}
\Pr\bigl[\Pi\in\mathcal{A}_{\mathrm{adv}}\mid \tau_{T_a}{=}1\bigr]
\ \ \text{s.t.}\ \eqref{eq:ftr},\eqref{eq:clean},
\end{equation}$$ subject to the structural constraint that $x$
influences $S$ and $\{M_i\}$ *only* through the system's own operators
$O$, $U_{\phi}$, and $R$.
:::

That constraint is the whole difficulty. An $\ell_2$ attacker chooses
the memory record and can optimise its embedding
directly [@chen2024agentpoison]. An $\ell_0$ attacker can only choose a
*pre-image*: content whose image under an unknown, stochastic,
LLM-implemented $U_{\phi}$ happens to be a memory record with the
properties it wants.

## The gap {#sec:gap}

Definitions [1](#def:lattice){reference-type="ref"
reference="def:lattice"} and [2](#def:triggers){reference-type="ref"
reference="def:triggers"} give a grid, and
Table [\[tab:positioning\]](#tab:positioning){reference-type="ref"
reference="tab:positioning"} fills it in. Three cells are empty, and
they compose into Problem [1](#prob:main){reference-type="ref"
reference="prob:main"}.

#### G1: no $\ell_0$ attacker has reached *collective* state.

The only environment-only memory attacks are
single-agent [@zou2026etamp; @yang2026zombie]. eTAMP states multi-agent
and shared-memory settings as out of scope. Every attack that does reach
shared or distributed MAS state assumes more: tool compromise ($\ell_3$,
[@zhu2025collabshadows]), channel control ($\ell_3$, [@he2025aitm]),
user interaction ($\ell_1$,
[@luo2026shadowmerge; @ahad2026misattribution]), or poisoned weights
($\ell_4$, [@xiao2026bcbi]).

#### G2: no persistent-memory carrier has an emergent trigger.

Collective activation exists only with a weight carrier [@xiao2026bcbi];
memory carriers use $\tau_1$-style single-record
triggers [@chen2024agentpoison; @dong2025minja; @zhang2026memmorph]. The
distributed attack that is closest, Collaborative
Shadows [@zhu2025collabshadows], assembles its payload *externally*
after the run rather than retrieving it from persistent state, so
$\tau_4$ over $S$ and $\tau_5$ over $\mathcal{G}^M$ are both unattested.
The one work that does study persistent shared-memory influence
deliberately has no trigger at all [@ahad2026misattribution].

#### G3: no attack has been evaluated across the memory stack.

Existing results each fix one backend---raw
trajectories [@zou2026etamp], a vector store [@chen2024agentpoison], one
graph implementation [@luo2026shadowmerge]---so it is unknown whether
consolidation and learned retention
policies [@yan2025memoryr1; @yu2026agemem; @wang2026memex; @zhang2025gmemory; @mao2026comam]
suppress a poisoned experience or preserve it. The memory literature
optimises utility without adversarial evaluation; the security
literature fixes the memory system. Nobody has crossed them.

#### From gap to method.

G1--G3 say what is missing; they also say why it is hard. An $\ell_0$
attacker holds no write privilege anywhere on the induction path
$E\!\to\!O\!\to\!U_{\phi}\!\to\!S\!\to\!R\!\to\!C\!\to\!\Pi$, so it must
persuade the system to perform each step on its behalf: to observe the
content, to write it, to keep it, to retrieve it, to bring enough pieces
together, and to act on them. §[4](#sec:method){reference-type="ref"
reference="sec:method"} makes that path explicit, and derives from it
the three mechanisms [Imprint]{.smallcaps} needs---one for the write
step, one for retention, and one for collective assembly.

# Methodology {#sec:method}

## The induction chain {#sec:chain}

Each step of the path
$E\!\to\!O\!\to\!U_{\phi}\!\to\!S\!\to\!R\!\to\!C\!\to\!\Pi$ is a gate
the attacker must pass but cannot force. Attack success therefore
factorises: $$\begin{align}
\mathrm{ASR}\;=\; &\underbrace{p_{\mathrm{exp}}}_{\text{exposure}}\cdot
\underbrace{p_{\mathrm{wr}}}_{\text{write-through}}\cdot
\underbrace{p_{\mathrm{per}}(h)}_{\text{persistence}}\ \cdot\nonumber\\[-2pt]
&\underbrace{p_{\mathrm{ret}}}_{\text{retrieval}}\cdot
\underbrace{p_{\mathrm{asm}}}_{\text{assembly}}\cdot
\underbrace{p_{\mathrm{cmp}}}_{\text{compliance}}
\label{eq:chain}
\end{align}$$ with
$p_{\mathrm{exp}}=\Pr[o_{\mathrm{poison}}\ \text{observed by some } i]$;
$p_{\mathrm{wr}}=\Pr[\,\exists m:\ m\in U_{\phi}(\cdot,o_{\mathrm{poison}})\,\mid o_{\mathrm{poison}}]$;
$p_{\mathrm{per}}(h)=\Pr[m\in S_{t+h}\mid m\in S_t]$ after $h$ benign
sessions; $p_{\mathrm{ret}}=\Pr[m\in R(S,q)]$ under the probe
distribution;
$p_{\mathrm{asm}}=\Pr[\tau=1\mid \text{fragments retrieved}]$, the
probability that enough distributed pieces co-occur; and
$p_{\mathrm{cmp}}=\Pr[\Pi\in\mathcal{A}_{\mathrm{adv}}\mid\tau=1]$.

Three consequences shape the whole paper. First, an $\ell_0$ attacker
must clear all six gates, while $\ell_2$ attackers are handed
$p_{\mathrm{exp}},
p_{\mathrm{wr}}, p_{\mathrm{per}}$ by assumption---so a lower end-to-end
$\mathrm{ASR}$ at $\ell_0$ may still represent a strictly stronger
result. Second, the factorisation is the natural place to state
hypotheses: MAS should raise $p_{\mathrm{wr}}$ and $p_{\mathrm{ret}}$
(more independent chances to write and retrieve) while lowering
$p_{\mathrm{asm}}$ (fragments must co-occur). Third, a defence is only
characterised once we know *which factor* it attenuates; reporting only
a drop in $\mathrm{ASR}$ hides whether a defence generalises. We
therefore require every reported defence result to include its
per-factor decomposition.

[Imprint]{.smallcaps} instantiates
Problem [1](#prob:main){reference-type="ref" reference="prob:main"} in
three stages---*imprint*, *sediment*, *activate*---addressing the first
two, middle two, and last two factors of
Eq. [\[eq:chain\]](#eq:chain){reference-type="eqref"
reference="eq:chain"} respectively.

## Threat surface and artifacts

The attacker publishes $K$ *artifacts*: ordinary environmental objects
the MAS may encounter while doing benign work. We instantiate four
artifact classes so that the phenomenon is not tied to one modality: (i)
a *document* (a how-to page, changelog, or policy note); (ii) a
*tool/plugin listing* with a description and usage example; (iii) an
*API response* carrying structured records; and (iv) a *peer artifact*
produced by a third-party agent the MAS consults. Each artifact carries
one fragment $z_\ell$. Artifacts are never delivered together and never
in the probing session.

## The consolidation pre-image problem {#sec:preimage}

An $\ell_2$ attacker picks the memory record $m$ and can optimise its
key $k(m)$ directly toward a target region. Our attacker picks $x$ and
inherits whatever $U_{\phi}$ makes of it. Let $k^\star$ be the centroid
of index keys for the probe-task query distribution $Q$, estimated on a
*shadow* system (§[4.6](#sec:shadow){reference-type="ref"
reference="sec:shadow"}). We must solve $$\begin{equation}
\text{find } x \ \ \text{s.t.}\ \
\mathbb{E}\bigl[\,k\bigl(U_{\phi}(x)\bigr)\,\bigr]\in \mathcal{B}_\rho(k^\star),
\label{eq:preimage}
\end{equation}$$ where the expectation is over the stochasticity of the
LLM-implemented extractor and of the trajectory that surrounds the
exposure. Eq. [\[eq:preimage\]](#eq:preimage){reference-type="eqref"
reference="eq:preimage"} is the technical core of the attack and the
reason the attack is not a re-run of AgentPoison at a lower privilege
level: the optimisation variable and the object being placed in memory
are separated by an unknown, non-differentiable, and system-specific
operator. Three properties of $U_{\phi}$ make it tractable:

1.  **Extraction is lossy but topical.** $U_{\phi}$ preserves the
    *claim* while discarding surface form; so the attacker should
    optimise the claim's topical alignment with $Q$, not its wording.

2.  **Consolidation normalises.** Summarisers and graph builders
    canonicalise entities and relations, which *removes* the anomalous
    phrasing that content filters look for---attacker-favourable, and
    the mechanism behind H[3](#h3){reference-type="ref" reference="h3"}.

3.  **Retention is utility-conditioned.** Records that were useful are
    kept; this is the lever of §[4.4](#sec:lure){reference-type="ref"
    reference="sec:lure"}.

## The utility lure {#sec:lure}

Prior memory attacks need their record to survive eviction; they achieve
this by writing it directly and repeatedly. We cannot. Instead the
artifact must *earn* retention: it must raise the agent's task utility
on the poisoning task, so that any retention
criterion---recency-weighted usefulness, LLM-judged importance, or a
learned retention head---scores it highly. We therefore impose a hard
constraint that each artifact is *net-positive* on its poisoning
session: $$\begin{equation}
\mathbb{E}\bigl[R_{\mathrm{task}}\mid \tilde{E}\bigr]\ \ge\
\mathbb{E}\bigl[R_{\mathrm{task}}\mid E\bigr].
\end{equation}$$ This is the "honeypot" intuition made precise, and it
inverts the usual stealth--strength trade-off: the more useful the
artifact, the deeper it sediments. It also makes the attack invisible to
any monitor that watches task success, and it is the mechanism that
H[4](#h4){reference-type="ref" reference="h4"} predicts learned memory
policies will amplify.

## Role-disjoint fragment allocation {#sec:inert}

To make the trigger genuinely collective we allocate fragments to roles
so that no single agent can satisfy $\tau_4$ from its own memory:
$$\begin{equation}
\max_{i\in\mathcal{V}}\ \bigl|\{\ell : z_\ell \in M_i\}\bigr| \ <\ T
\ \le\ \bigl|\{\ell : z_\ell \in \mathcal{R}_t\}\bigr|.
\label{eq:disjoint}
\end{equation}$$ Allocation is computed from the role-conditioned
exposure profile: the browser role sees listings, the verifier sees
policy documents, the writer sees changelogs.
Eq. [\[eq:disjoint\]](#eq:disjoint){reference-type="eqref"
reference="eq:disjoint"} is what forces activation through the *shared*
store or through inter-agent messages, and it is what a per-agent
defence cannot see.

#### Single-fragment audit.

For every fragment set we run a mandatory audit that evaluates each
singleton $\{z_\ell\}$ alone on the full probe suite and requires
$\mathrm{ASR}(\{z_\ell\})-\mathrm{FTR}\le\delta_{\mathrm{inert}}$.
Fragment sets failing the audit are rejected: without it, a "collective"
trigger may be a single-fragment trigger with decoration, which is
precisely the confound we must rule out to distinguish EICB from prior
work. We report audit pass rates.

## Black-box search over a shadow MAS {#sec:shadow}

The attacker cannot query the target. We assume only knowledge of the
*class* of deployment (roles, an open-weight backbone family, a public
memory library) and build a shadow MAS on which artifacts are optimised,
then transfer. Search is gradient-free: an LLM-driven evolutionary loop
over artifact text with population $P{=}32$, $G{=}20$ generations,
mutation by targeted rewriting and crossover by claim recombination,
scoring $$\begin{align}
J(x)=\ &\lambda_{\mathrm{wr}}\,\hat{p}_{\mathrm{wr}}
      +\lambda_{\mathrm{per}}\,\hat{p}_{\mathrm{per}}(h)
      +\lambda_{\mathrm{ret}}\,\hat{p}_{\mathrm{ret}}\nonumber\\
      &+\lambda_{u}\,\widehat{\Delta R_{\mathrm{task}}}
      -\lambda_{d}\,\widehat{\mathrm{Det}}(x)
      -\lambda_{f}\,\widehat{\mathrm{Viol}}(x),
\label{eq:objective}
\end{align}$$ where $\widehat{\mathrm{Det}}$ is the maximum score over
the defence ensemble of §[4.8](#sec:defenses){reference-type="ref"
reference="sec:defenses"} and $\widehat{\mathrm{Viol}}$ penalises
single-fragment audit failure. Note that $J$ contains no
$p_{\mathrm{cmp}}$ term: we deliberately do *not* optimise the model's
willingness to comply, since that would confound an environment/memory
result with jailbreak strength [@zou2023universal]. **Transfer
rate**---the ratio of target to shadow $\mathrm{ASR}$---is reported as a
first-class metric, since it is the quantity that determines real-world
exploitability.

## Instrumentation and causal attribution {#sec:instrumentation}

Measuring Eq. [\[eq:chain\]](#eq:chain){reference-type="eqref"
reference="eq:chain"} requires knowing which memory objects descend from
attacker content after several rounds of summarisation and merging. We
therefore maintain an **out-of-band provenance ledger**: every write
records the observation span and parent records that produced it, in a
side channel that is *never* visible to any agent, retriever, or defence
under evaluation. Derivation is transitive, so a summary of a summary of
a poisoned page is still attributed. This makes $p_{\mathrm{wr}}$,
$p_{\mathrm{per}}(h)$, $p_{\mathrm{ret}}$, cross-agent propagation, and
memory amplification
$\mathrm{MA}=\lvert\text{derived records}\rvert/\lvert\text{injected artifacts}\rvert$
exact rather than estimated by string matching, which is the standard
weakness of memory-attack evaluation once consolidation is involved.

#### Counterfactual attribution.

For defence analysis we estimate the average causal effect of each
memory node on the adversarial outcome $Y$, $$\begin{equation}
\mathrm{ACE}(m)=\mathbb{E}[Y\mid do(m{=}1)]-\mathbb{E}[Y\mid do(m{=}0)],
\end{equation}$$ by deterministic trajectory replay with the node
ablated [@pearl2009causality], and for interacting fragments we compute
Shapley values [@shapley1953value] over the fragment set to quantify how
much of the effect is genuinely joint rather than additive---a direct
quantitative test of whether a trigger is collective.

## Defences evaluated {#sec:defenses}

We evaluate five defences, chosen so that each cuts a different factor
of Eq. [\[eq:chain\]](#eq:chain){reference-type="eqref"
reference="eq:chain"}, plus one we propose.

1.  **Input sanitisation** ($p_{\mathrm{exp}}$): LLM-judge and
    classifier screening of observations.

2.  **[Paw]{.smallcaps}: provenance-aware write** ($p_{\mathrm{wr}}$,
    ours). The update operator is extended to carry provenance $p_t$ and
    a trust label $\rho_t$, $S_{t+1}=U(S_t,x_t,p_t,\rho_t)$, with two
    rules: untrusted-origin content may be stored but never *merged*
    into a trusted record, and provenance is preserved under
    consolidation, $p(\mathrm{merge}(m_1,\dots,m_k))=\bigcup_i p(m_i)$.
    The design target is the failure mode identified by
    @ahad2026misattribution: content laundering its origin by surviving
    a summarisation step.

3.  **Trust-discounted retrieval** ($p_{\mathrm{ret}}$):
    $\mathrm{score}(m,q)=\alpha\,\mathrm{Rel}+\gamma\,\mathrm{Trust}-\eta\,\mathrm{Risk}$.

4.  **Memory isolation** ($p_{\mathrm{asm}}$): schema-validated
    cross-agent boundaries with dynamic access control over the shared
    store [@rezazadeh2025collabmem], which directly targets the assembly
    step that Eq. [\[eq:disjoint\]](#eq:disjoint){reference-type="eqref"
    reference="eq:disjoint"} depends on.

5.  **Peer reasoning consistency** ($p_{\mathrm{cmp}}$), following
    @fan2025peerguard. We expect this to be weak here---agents
    retrieving the same poisoned collective memory produce *mutually
    consistent* wrong rationales---and we treat confirming that
    prediction as a result.

6.  **Global trajectory monitoring**
    ($p_{\mathrm{asm}}$/$p_{\mathrm{cmp}}$): a prefix detector with
    joint-trajectory visibility [@arias2026earlydetect], reported with
    the false-positive rate on clean runs.

Every defence is additionally evaluated against an **adaptive attacker**
in which $\widehat{\mathrm{Det}}$ in
Eq. [\[eq:objective\]](#eq:objective){reference-type="eqref"
reference="eq:objective"} includes that defence---a static-only
evaluation of a memory defence is not informative.

## Safety by construction {#sec:safety}

Every adversarial action in this work is an inert surrogate.
$\mathcal{A}_{\mathrm{adv}}$ consists of (i) emitting a canary string
into a sandboxed log, (ii) selecting a designated decoy item from a
fixed catalogue, or (iii) calling a mock tool that records the call and
returns a constant. No artifact contains working exploit code,
credentials, or real exfiltration endpoints; all environments are local
snapshots with egress disabled; no attack is executed against any live
service. This preserves every measurement in
Eq. [\[eq:chain\]](#eq:chain){reference-type="eqref"
reference="eq:chain"}---which is about *whether the system can be
steered*, not about payload potency---while removing dual-use content
from the artifact set.

# Experimental Setup {#sec:setup}

## Hypotheses {#sec:hypotheses}

The gaps of §[3.5](#sec:gap){reference-type="ref" reference="sec:gap"}
become five pre-registered hypotheses, each mapped to an experiment in
§[5.9](#sec:suite){reference-type="ref" reference="sec:suite"} and each
stated so that its negation is informative.

::: {#h1 .hypothesis}
**Hypothesis 1** (Collective amplification). At matched exposure budget
$B$, $p_{\mathrm{wr}}$ and $p_{\mathrm{ret}}$ increase monotonically in
the number of agents $N$, because role-conditioned consolidation gives
each fragment several independent chances to be written and cross-agent
retrieval unions private memories, while $\mathrm{FTR}$ stays flat.
Prediction: $\Delta_\tau(N{=}8)>\Delta_\tau(N{=}1)$ with the gap driven
by $p_{\mathrm{wr}}\!\cdot\!p_{\mathrm{ret}}$, not $p_{\mathrm{cmp}}$.
*Falsified if* MAS attenuates persistence, e.g. because cross-checking
between roles filters unsupported content at write time.
:::

::: {#h2 .hypothesis}
**Hypothesis 2** (Collective selectivity). For $T>1$, $\tau_4$ attains a
higher $\Delta_\tau$ than any single-fragment attack at matched $B$, and
evades per-item content filters, because each fragment passes the
single-fragment audit. Prediction: content-classifier detection rate
falls with $K$ while $\Delta_\tau$ is non-decreasing up to a knee at
$T\approx3$.
:::

::: {#h3 .hypothesis}
**Hypothesis 3** (Non-monotone consolidation). Persistence is
*non-monotone* in memory abstraction. Literal triggers ($\tau_1$) decay
fastest under summary and graph backends, whereas lesson-shaped and
structural triggers ($\tau_4,\tau_5$) survive *better* under those same
backends, with memory amplification $\mathrm{MA}>1$. *Falsified if*
$p_{\mathrm{per}}$ is monotonically decreasing in abstraction level for
all predicates---which would make consolidation a general defence.
:::

::: {#h4 .hypothesis}
**Hypothesis 4** (Utility--security coupling). Across the backend family
(fixed $\to$ graph $\to$ learned), poison persistence increases with
clean long-horizon utility: $\partial\mathrm{ASR}/\partial\mathrm{CU}>0$
when $\mathrm{CU}$ is varied by changing the memory system rather than
the model. The mechanism is shared: a policy rewarded for retaining
evidence that proves useful later retains a useful-looking artifact.
*Falsified if* learned policies suppress attacker content while
improving $\mathrm{CU}$, which would be the strongest possible argument
for learned memory.
:::

::: {#h5 .hypothesis}
**Hypothesis 5** (Provenance sufficiency). A write-time policy that
refuses to merge provenance-erased content ([Paw]{.smallcaps},
§[4.8](#sec:defenses){reference-type="ref" reference="sec:defenses"})
reduces $\mathrm{ASR}$ more, per unit of clean-utility loss, than any
output-side filter, and does so by attenuating $p_{\mathrm{wr}}$ and
$p_{\mathrm{ret}}$ rather than $p_{\mathrm{cmp}}$.
:::

## [MemEnv]{.smallcaps}: testbed and session protocol

[MemEnv]{.smallcaps} wraps existing agent environments in a persistent,
multi-session, multi-agent harness. Each *run* is a sequence of sessions
$$\begin{equation}
\underbrace{\sigma_1\dots\sigma_{T_p}}_{\text{poisoning}}\;
\underbrace{\sigma_{T_p+1}\dots\sigma_{T_p+h}}_{\text{benign dormancy}}\;
\underbrace{\sigma_{T_a}}_{\text{probe}},
\end{equation}$$ where poisoning sessions are ordinary tasks that happen
to touch an artifact, dormancy sessions are unrelated benign tasks drawn
from the same distribution, and the probe session is issued by a
legitimate user in a clean environment. The attacker is absent from
dormancy and probe sessions. Memory persists throughout; nothing else
does.

#### Environments.

Four, chosen for complementary coverage:

- **WebArena /
  VisualWebArena** [@zhou2023webarena; @koh2024visualwebarena] ---
  primary, because eTAMP [@zou2026etamp] provides a directly comparable
  single-agent, environment-only baseline in it.

- **AgentDojo** [@debenedetti2024agentdojo] --- tool-using agents over
  untrusted data; we add the persistent cross-session memory its base
  form lacks.

- **AgentBench-DB / multi-role collaboration** [@liu2023agentbench] ---
  role-specialised MAS collaboration, matching the setting of
  @zhu2025collabshadows.

- **ALFWorld** [@alfworld] --- long-horizon non-web decision making, to
  test whether the phenomenon is web-specific.

A fifth, **ToolMarket**, is a controlled simulator we build: a
marketplace of $\sim$`<!-- -->`{=html}200 tool listings with usage
statistics and reviews, into which the attacker publishes one listing.
It provides the cleanest instantiation of the utility lure and full
ground truth over exposure.

#### Tasks and probes.

For each environment we curate $200$ poisoning tasks, $600$ dormancy
tasks, and $200$ probe tasks. Probes are stratified into *on-topic*
(semantically related to the poisoning task, as in eTAMP) and
*off-topic* (unrelated), since the gap between them isolates
$p_{\mathrm{ret}}$ from $p_{\mathrm{per}}$. A matched *clean-probe* set
with no poisoning measures $\mathrm{FTR}$ and $\mathrm{CU}$.

## MAS configurations

Roles $\{$planner, browser/executor, verifier, writer$\}$; team sizes
$N\in\{1,2,4,8\}$ (with $N{=}1$ the single-agent control that reproduces
the eTAMP setting); topologies $G\in\{$chain, star, tree, fully
connected, dynamic$\}$. Orchestration is implemented once over a common
interface and run under two frameworks, AutoGen [@wu2023autogen] and
MetaGPT [@hong2023metagpt], to check that results are not an artifact of
one scaffold. Each agent has private memory $M_i$; the team shares $S$.

## Memory backends

Eight backends spanning the fixed-to-learned axis, all under an
identical interface so the only thing that changes is $U_{\phi}$ and
$R$:

::: center
  ------- ------------------------------------------------------
  $B_0$   no persistent memory (floor)
  $B_1$   raw trajectory memory (eTAMP setting)
  $B_2$   fixed-chunk vector RAG, top-$k$ cosine
  $B_3$   summary / consolidation [@zhong2024memorybank]
  $B_4$   graph memory [@xu2025amem; @chhikara2025mem0]
  $B_5$   learned memory ops [@yu2026agemem; @yan2025memoryr1]
  $B_6$   learned indexed experience [@wang2026memex]
  $B_7$   hierarchical MAS memory [@zhang2025gmemory]
  ------- ------------------------------------------------------
:::

$B_5$--$B_7$ are reimplemented under our interface and trained on
*benign* data only, so that any security effect is out-of-distribution
generalisation of a utility objective rather than a trained-in
artifact---this is what makes H[4](#h4){reference-type="ref"
reference="h4"} a statement about memory learning in general.

## Backbones

Three families to separate model-specific from system-level effects: one
frontier closed model, one mid-tier closed model, and two open-weight
models (one $\sim$`<!-- -->`{=html}8B, one $\sim$`<!-- -->`{=html}70B)
which also serve as the shadow system of
§[4.6](#sec:shadow){reference-type="ref" reference="sec:shadow"}.
Decoding is fixed ($T{=}0.7$, top-$p$ $0.95$) with per-run seeds
recorded; all prompts and scaffolds are held constant across conditions.

## Attack baselines

- **$\ell_2$ ceiling**: AgentPoison-style direct memory
  write [@chen2024agentpoison]. Not a competitor---an upper bound that
  tells us how much of the gap is attributable to privilege.

- **$\ell_1$**: MINJA-style query-only injection [@dong2025minja];
  ShadowMerge-style graph relation conflict [@luo2026shadowmerge] on
  $B_4$.

- **$\ell_3$**: Collaborative Shadows distributed tool
  fragments [@zhu2025collabshadows], the closest distributed comparator.

- **$\ell_0$**: eTAMP-style single-record environmental
  poisoning [@zou2026etamp] --- the primary baseline; Prompt
  Infection [@lee2024promptinfection] for propagation without
  persistence.

- **Ablations of [Imprint]{.smallcaps}**: no utility lure; no
  role-disjoint allocation; $T{=}1$; random (unoptimised) artifact text;
  no shadow-MAS search; $\tau_4$ vs. $\tau_5$.

## Metrics

Primary: $\mathrm{ASR}$, $\mathrm{FTR}$, and the selectivity margin
$\Delta_\tau$. Chain:
$p_{\mathrm{exp}}, p_{\mathrm{wr}}, p_{\mathrm{per}}(h), p_{\mathrm{ret}},
p_{\mathrm{asm}}, p_{\mathrm{cmp}}$, each measured directly from the
provenance ledger. Systemic: cross-agent propagation
$\mathrm{CPR}=|\{i: m_p\rightsquigarrow M_i\}|/N$; memory amplification
$\mathrm{MA}$; dormancy half-life $h_{1/2}$ (sessions until
$\mathrm{ASR}$ halves). Stealth: detector AUROC per defence, and
$\Delta\mathrm{CU}$ on the clean-probe set. Cost: attacker tokens,
artifacts published $K$, and edited tokens $B$. Transfer:
shadow-to-target $\mathrm{ASR}$ ratio. We plot the **privilege--success
frontier** ($\ell$ on the $x$-axis, $\mathrm{ASR}$ on the $y$-axis,
marker size $=\Delta\mathrm{CU}$) rather than a pooled bar chart, since
attacks at different $\ell$ are not comparable on a single scale.

## Design, power, and statistics

The core design is a full factorial over
$N(4)\times G(5)\times B(8)\times \tau(5)\times h(5)\times T(4)$, run in
two stages: a screening stage at reduced resolution ($N\!\in\!\{1,4\}$,
$G\!\in\!\{$chain, full$\}$, $h\!\in\!\{0,20\}$) to locate active
regions, then full resolution on the active subspace. Every cell gets
$n=200$ probe episodes $\times$ 3 seeds. With $n=600$ per cell, a
two-proportion test detects $\Delta\mathrm{ASR}=0.06$ at $\alpha=0.05$
with power $0.8$; we power for $0.05$ and pre-register that as the
minimum effect size of interest.

Analysis is a mixed-effects logistic regression with fixed effects for
the manipulated factors and random intercepts for task and backbone, so
that per-task difficulty does not masquerade as an attack effect.
Confidence intervals are paired bootstrap over tasks ($10^4$ resamples);
the five hypothesis tests are corrected with Holm's
procedure [@holm1979simple]. Chain factors are reported with their own
intervals, and we verify that the product of measured factors
reconstructs measured $\mathrm{ASR}$ within CI---a consistency check on
the instrumentation itself. All hypotheses, effect sizes, and exclusion
rules are registered before data collection; deviations are reported.

## Experiment suite {#sec:suite}

::: table*
  **Exp.**   **Question**                                                **Manipulation**                                    **Held fixed**                                 **Tests**
  ---------- ----------------------------------------------------------- --------------------------------------------------- ---------------------------------------------- ------------------------------------------------
  E1         Does a MAS amplify environment-induced persistence?         $N\in\{1,2,4,8\}$                                   $B_2$, chain, $\tau_1$, $h{=}20$, budget $B$   H[1](#h1){reference-type="ref" reference="h1"}
  E2         Is a distributed memory trigger achievable and selective?   $T\in\{1,2,3,4\}$, $K\in\{2,4,8\}$                  $N{=}4$, $B_2$, $h{=}20$                       H[2](#h2){reference-type="ref" reference="h2"}
  E3         Does consolidation destroy or launder the trigger?          $B_1$--$B_4$ $\times$ $\tau_1,\tau_4,\tau_5$        $N{=}4$, chain, $h{=}20$                       H[3](#h3){reference-type="ref" reference="h3"}
  E4         Do learned memory policies enlarge the attack surface?      $B_2$--$B_7$                                        $N{=}4$, $\tau_4$, $T{=}3$, $h{=}20$           H[4](#h4){reference-type="ref" reference="h4"}
  E5         How do topology and time shape propagation?                 $G$(5) $\times$ $h\in\{0,1,5,20,100\}$              $N{=}4$, $B_4$, $\tau_3$                       H[1](#h1){reference-type="ref" reference="h1"}
  E6         Where does each defence actually cut the chain?             6 defences $\times$ {static, adaptive}              $N{=}4$, $B_4$, $\tau_4$, $T{=}3$              H[5](#h5){reference-type="ref" reference="h5"}
  E7         Does it transfer and generalise?                            4 envs $\times$ 4 backbones $\times$ 2 frameworks   best config from E1--E4                        ---
:::

Table [\[tab:suite\]](#tab:suite){reference-type="ref"
reference="tab:suite"} lists the seven experiments. Their logic is
sequential. E1 establishes the phenomenon by changing exactly one
variable---team size---from the published single-agent baseline, so that
any difference is attributable to multi-agency rather than to
environment or memory design. E2 then asks whether the trigger can be
made genuinely collective, which is what separates EICB from
single-record memory poisoning; it is gated on the single-fragment audit
of §[4.5](#sec:inert){reference-type="ref" reference="sec:inert"}. E3
tests the mechanism we consider most interesting and least predictable,
namely that abstraction launders rather than removes. E4 connects to the
learned-memory literature and is the experiment most likely to produce a
result of interest outside security. E5 and E6 characterise the
phenomenon and the defence landscape. E7 is the generalisation check
without which none of the above should be believed.

#### Reporting.

We commit in advance to reporting: (a) all six chain factors for every
headline number; (b) $\mathrm{FTR}$ alongside every $\mathrm{ASR}$; (c)
clean-utility deltas for every attack *and* every defence; (d) adaptive
as well as static defence results; (e) shadow-to-target transfer; and
(f) all negative results, including any hypothesis that fails.

## Compute and reproducibility

We estimate $\approx$$4.2$M LLM calls for the full suite ($7$
experiments $\times$ mean $18$ cells $\times$ $600$ episodes $\times$
$\approx$$55$ calls/episode), dominated by E3 and E7. Open-weight
backbones run locally on 8$\times$A100; closed-model usage is confined
to E1, E4, and E7. All LLM calls are cached by content hash and every
run is replayable from the cache, which makes trajectory replay for
causal attribution (§[4.7](#sec:instrumentation){reference-type="ref"
reference="sec:instrumentation"}) exact and makes the reported numbers
reproducible without re-querying any API. We will release
[MemEnv]{.smallcaps}, the harness, the provenance ledger, all task
suites, seeds, prompts, and the analysis code; artifact sets containing
attack content will be released under the gated policy described in the
Ethics Statement.

# Expected Outcomes

The result we consider most likely, and most consequential if confirmed,
is H[3](#h3){reference-type="ref" reference="h3"} together with
H[4](#h4){reference-type="ref" reference="h4"}: that the memory
machinery adopted for utility is what carries the attack. If
consolidation strips suspicious phrasing while preserving an induced
"lesson," and if learned retention policies preferentially keep
artifacts that proved useful, then the standard defensive
intuition---filter the input, summarise aggressively, and trust what
survives---is exactly backwards, and provenance rather than content
becomes the necessary invariant. Conversely, if cross-role verification
at write time attenuates persistence (falsifying
H[1](#h1){reference-type="ref" reference="h1"}), that is a concrete and
immediately deployable argument for redundancy in MAS memory write
paths. Both directions are worth the experiment; we have designed the
protocol so that we cannot tell in advance which we will get.

# Limitations {#limitations .unnumbered}

This paper contributes a threat model, an attack design, a testbed, and
a protocol; **it does not yet report empirical results**, and every
quantitative claim above is a stated prediction rather than a finding.
Several further limitations are structural.

*Sandbox validity.* Our environments are local snapshots with inert
surrogate actions. This is necessary for safety but means we measure
whether a system can be *steered*, not what an attacker could ultimately
do with that steering; ASR here is not a proxy for real-world harm
magnitude.

*Exposure is assumed, not controlled.* An $\ell_0$ attacker cannot make
the system visit an artifact. We hold $p_{\mathrm{exp}}$ fixed by
construction in most cells and report it separately, but real
deployments determine it through factors (search ranking, tool
popularity, crawl policy) that we do not model.

*Reimplemented learned baselines.* $B_5$--$B_7$ are reimplementations
under a common interface, not the original systems, and their absolute
utility may differ from published numbers. We therefore report
H[4](#h4){reference-type="ref" reference="h4"} as a trend across the
backend family rather than as a claim about any specific published
system.

*Shadow-transfer assumptions.* The attacker is assumed to know the class
of deployment. If a target uses an unpublished memory architecture, the
pre-image optimisation of §[4.3](#sec:preimage){reference-type="ref"
reference="sec:preimage"} degrades to random search; the transfer-rate
metric is intended to expose exactly this, and low transfer would
meaningfully bound the threat.

*Statistical scope.* Even at $n=600$ per cell, the full factorial is
screened rather than exhaustively estimated, so interactions among more
than two factors are underpowered and are reported as exploratory.

*Language and modality.* All environments and artifacts are
English-language and predominantly text; whether consolidation launders
multimodal evidence [@multimodalmem2026] similarly is out of scope.

# Ethics Statement {#ethics-statement .unnumbered}

This work is offensive security research on systems that are being
deployed now, undertaken to make a specific failure mode measurable
before it is exploited. Several choices follow from that purpose.

*No live targets.* All experiments run against local environment
snapshots with network egress disabled. No attack is executed against
any production system, third-party service, or real user.

*Inert payloads.* As described in
§[4.9](#sec:safety){reference-type="ref" reference="sec:safety"}, every
adversarial action is a canary token, a designated decoy selection, or a
mock tool call. The artifact sets contain no working exploit code,
credentials, malware, or exfiltration endpoints, and the attack's
contribution is a *control channel*, not a payload; we do not develop
the latter.

*Release policy.* The testbed, harness, provenance ledger, task suites,
and analysis code will be released openly, since defenders need them.
Optimised attack artifacts and the search code that produces them will
be released under a gated request process for identified researchers,
following the pattern used by prior agent-security releases, and
withheld entirely if the measured transfer rate to unseen deployments
proves high.

*Disclosure.* We will notify the maintainers of any memory library that
shows a high write-through or retrieval rate in our evaluation before
publication, and we will report defence results---particularly the
per-factor decomposition, which is what tells a maintainer where to
intervene---to them directly.

*Dual use.* The attack requires only the ability to publish content,
which is a low bar; that is the point of the paper, and it is also why
we pair the attack with a constructive defence ([Paw]{.smallcaps},
§[4.8](#sec:defenses){reference-type="ref" reference="sec:defenses"})
and evaluate that defence against an adaptive attacker rather than a
static one.

# Notation {#sec:appendix-notation}

::: center
  --------------- --------------------------------------------------------------------------------------------------
  $M_{i,t}$       private memory of agent $i$ at step $t$
  $S_t$           shared persistent store
  $C_t$, $G_t$    message history, communication topology
  $U_{\phi}$      memory update operator (fixed or learned)
  $R$             retrieval operator
  $z_\ell$        induced memory fragment $\ell$
  $\tau$          trigger predicate (§[3.3](#sec:triggers){reference-type="ref" reference="sec:triggers"})
  $T$             collective activation threshold
  $K$             number of fragments / artifacts
  $B$             per-session edit budget (tokens)
  $h$, $H$        dormancy in sessions; minimum dormancy
  $\ell_j$        attacker capability level (Def. [1](#def:lattice){reference-type="ref" reference="def:lattice"})
  $\Delta_\tau$   selectivity margin $\mathrm{ASR}-\mathrm{FTR}$
  --------------- --------------------------------------------------------------------------------------------------
:::

# Artifact Templates and Fragment Design {#sec:appendix-artifacts}

To be released with the code. Each template specifies the artifact class
(§[4](#sec:method){reference-type="ref" reference="sec:method"}), the
carried fragment $z_\ell$, the utility-lure component that satisfies the
net-positive constraint of §[4.4](#sec:lure){reference-type="ref"
reference="sec:lure"}, and the role whose exposure profile it targets
under Eq. [\[eq:disjoint\]](#eq:disjoint){reference-type="eqref"
reference="eq:disjoint"}.

# Pre-Registration {#sec:appendix-prereg}

The hypotheses of §[5.1](#sec:hypotheses){reference-type="ref"
reference="sec:hypotheses"}, the minimum effect size ($0.05$ absolute in
$\mathrm{ASR}$), the analysis model, the exclusion rules, and the
stopping rule are registered prior to data collection; the registration
document is included in the artifact release.
