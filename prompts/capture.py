"""Build the prompt archive (PI requirement 2026-10-10: every prompt used in the pipeline is archived for reproducibility).

For every call site the pipeline has, this script
  1. writes the TEMPLATE (verbatim text; placeholders in {braces}) to prompts/templates/<id>.txt|.json, taken from the
     code objects themselves (constants are imported, inline message builders are called with placeholder strings);
  2. rebuilds one or more REAL requests exactly as the experiment built them and proves byte-identity offline against
     the response cache (infra.llm.cache_lookup: no network, no cost). A request found in the cache is exactly what
     was sent; the full payload is written to prompts/exemplars/<id>.json with verified=true.
Library-internal prompts (Mem0, LangMem/trustcall, LlamaIndex, LangChain, Nemori) are archived by export_library.py.
Output also: prompts/registry.json (index used to generate README tables).
Run with the fw-env python:  python prompts/capture.py
"""
import glob, json, os, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "framework_study/src", ROOT / "framework_study/stimuli", ROOT / "benchmark_audit", ROOT / "benchmark_audit/official", ROOT / "method"):  # noqa
    sys.path.insert(0, str(p))
from infra.llm import cache_lookup

P = Path(os.environ.get("PROMPTS_OUT", ROOT / "prompts"))   # check_prompts.py rebuilds into a temp dir
(P / "templates").mkdir(parents=True, exist_ok=True)
(P / "exemplars").mkdir(parents=True, exist_ok=True)
REG = []
QWEN, LLAMA, OSS, GEMMA, LOCAL = ("qwen.qwen3-235b-a22b-2507-v1:0", "meta.llama3-3-70b-instruct-v1:0", "openai.gpt-oss-120b-1:0",
                                  "google.gemma-3-27b-it", "local:qwen3-8b")


def template(pid, obj, stage, source, note=""):
    f = P / "templates" / (f"{pid}.txt" if isinstance(obj, str) else f"{pid}.json")
    f.write_text(obj if isinstance(obj, str) else json.dumps(obj, indent=1, ensure_ascii=False))
    REG.append(dict(kind="template", id=pid, stage=stage, source=source, file=str(f.relative_to(P)), note=note))


def exemplar(pid, stage, used_for, source, model, messages, **params):
    resp, payload = cache_lookup(model, messages, **params)
    f = P / "exemplars" / f"{pid}.json"
    f.write_text(json.dumps(dict(id=pid, stage=stage, used_for=used_for, source=source, verified_in_cache=resp is not None,
                                 payload=payload, cached_response_excerpt=(resp or {}).get("text", "")[:400]), indent=1, ensure_ascii=False))
    REG.append(dict(kind="exemplar", id=pid, stage=stage, used_for=used_for, source=source, model=model,
                    params={k: v for k, v in params.items()}, verified=resp is not None, file=str(f.relative_to(P))))
    return resp


def call_capture(fn, *a, **k):
    """Run a message builder that calls self.llm / chat and capture the messages instead of sending them."""
    box = {}

    def fake(messages, max_tokens=2048):
        box["messages"], box["max_tokens"] = messages, max_tokens
        return "{NEW_MEMORY}"
    return box, fake


# =================================================================== A. benchmark audit: closed book (benchmark_audit/closed_book.py)
def section_closed_book():
    import closed_book as CB
    from lme_prompts import get_anscheck_prompt
    st = "closed-book audit"
    template("cb_natural_system", CB.NAT_SYS, st, "benchmark_audit/closed_book.py NAT_SYS")
    template("cb_forced_system", CB.FORCED_SYS, st, "benchmark_audit/closed_book.py FORCED_SYS (also method draw F0)")
    items = CB.load_lme() + CB.load_locomo() + CB.load_mab() + CB.load_prefeval()
    first = {}
    for x in items:
        first.setdefault(x["bench"], x)
    for m, tag in ((QWEN, "qwen"), (LLAMA, "llama")):
        for b, x in first.items():
            if b == "PrefEval":
                exemplar(f"cb_prefeval_{tag}", st, "PrefEval memoryless answer (FINDINGS §8)", "closed_book.py main", m,
                         [{"role": "user", "content": x["q"]}], temperature=0.0, max_tokens=600)
                continue
            for proto, sysmsg in (("natural", CB.NAT_SYS), ("forced", CB.FORCED_SYS)):
                exemplar(f"cb_{b.lower()}_{proto}_{tag}", st, f"closed-book {proto} answer, {b} (FINDINGS §8)", "closed_book.py main", m,
                         [{"role": "system", "content": sysmsg}, {"role": "user", "content": x["q"]}], temperature=0.0, max_tokens=150)
    # official judges
    for task in ("single-session-user", "temporal-reasoning", "knowledge-update", "single-session-preference"):
        template(f"judge_lme_{task}", get_anscheck_prompt(task, "{question}", "{answer}", "{response}"), "judging",
                 "benchmark_audit/official/lme_prompts.py (verbatim LongMemEval evaluate_qa.py, MIT)",
                 "single-session-assistant and multi-session use the single-session-user template")
    template("judge_lme_abstention", get_anscheck_prompt("single-session-user", "{question}", "{explanation}", "{response}", abstention=True),
             "judging", "benchmark_audit/official/lme_prompts.py", "LoCoMo cat 5 uses explanation = 'The conversation does not contain this information.'")
    rows = {(r["bench"], r["proto"], r["id"]): r for r in map(json.loads, open(ROOT / "benchmark_audit/results/closed_book_qwen3-235b-a22b-2507.jsonl"))}
    lx = first["LongMemEval"]; r = rows[("LongMemEval", "forced", lx["id"])]
    exemplar("judge_lme_closed_book", "judging", "LongMemEval official judge (closed-book run)", "closed_book.py main", OSS,
             [{"role": "user", "content": get_anscheck_prompt(lx["qtype"], lx["q"].split("Question: ", 1)[1], lx["gold"], r["pred"], abstention=lx["abstention"])}],
             temperature=0.0, max_tokens=600, reasoning_effort="low")
    cx = first["LoCoMo"]; r = rows[("LoCoMo", "forced", cx["id"])]
    exemplar("judge_locomo_closed_book", "judging", "LoCoMo judge = LongMemEval generic prompt (closed-book run)", "closed_book.py main", OSS,
             [{"role": "user", "content": get_anscheck_prompt("single-session-user", cx["q"].split("Question: ", 1)[1], cx["gold"], r["pred"])}],
             temperature=0.0, max_tokens=600, reasoning_effort="low")
    c5 = next(x for x in items if x["bench"] == "LoCoMo" and x["abstention"]); r = rows[("LoCoMo", "natural", c5["id"])]
    exemplar("judge_locomo_cat5_closed_book", "judging", "LoCoMo category 5 (unanswerable) judge", "closed_book.py main", OSS,
             [{"role": "user", "content": get_anscheck_prompt("single-session-user", c5["q"].split("Question: ", 1)[1],
                                                              "The conversation does not contain this information.", r["pred"], abstention=True)}],
             temperature=0.0, max_tokens=600, reasoning_effort="low")
    viol = open(ROOT / "benchmark_audit/official/prefeval_check_violation.txt").read()
    helpf = open(ROOT / "benchmark_audit/official/prefeval_check_helpful.txt").read()
    template("judge_prefeval_violation", viol, "judging", "benchmark_audit/official/prefeval_check_violation.txt (verbatim PrefEval)")
    template("judge_prefeval_helpful", helpf, "judging", "benchmark_audit/official/prefeval_check_helpful.txt (verbatim PrefEval)")
    jsys = "You are a helpful assistant in evaluating an AI assistant's reponse. You should be fair and strict and follow the user's instruction"
    template("judge_prefeval_system", jsys, "judging", "closed_book.py main (system message of the PrefEval judge calls)")
    px = first["PrefEval"]; r = rows[("PrefEval", "natural", px["id"])]
    for name, tpl in (("violation", viol), ("helpful", helpf)):
        p = tpl.replace("{preference}", px["preference"]).replace("{question}", px["q"]).replace("{end_generation}", r["pred"])
        exemplar(f"judge_prefeval_{name}", "judging", f"PrefEval official {name} check", "closed_book.py main", OSS,
                 [{"role": "system", "content": jsys}, {"role": "user", "content": p}], temperature=0.0, max_tokens=800, reasoning_effort="low")


# =================================================================== B. benchmark re-scoring (benchmark_audit/rescore.py)
def section_rescore():
    import rescore as RS
    from lme_prompts import get_anscheck_prompt
    st = "benchmark re-scoring"
    template("rescore_answer_system_piA", RS.ANSWER_SYS, st, "benchmark_audit/rescore.py ANSWER_SYS (native protocol pi_A)")
    template("rescore_locomo_turn_format", "[{session_date_time}] {speaker}: {text}   (+ ' [shares a photo: {blip_caption}]' when the turn has an image caption)",
             st, "benchmark_audit/rescore.py locomo_episodes (speaker_a -> role user, speaker_b -> role assistant; one ingest per session)")
    template("rescore_mab_chunk_format", [{"role": "user", "content": "Here is the next part of a document I want you to remember:\n\n{next 1,000 words}"},
                                          {"role": "assistant", "content": "Got it."}], st, "benchmark_audit/rescore.py mab_ruler_episodes (one ingest per chunk)")
    v2 = {r["id"]: r for r in map(json.loads, open(ROOT / "benchmark_audit/results_v2/rescore_locomo_codex.jsonl"))}
    r = v2["c0q0"]
    exemplar("rescore_answer_piA_locomo_codex", st, "native-protocol answer from a system's context (§11, Step 2)", "rescore.py run_episode", QWEN,
             [{"role": "system", "content": RS.ANSWER_SYS.format(ctx=r["ctx"])}, {"role": "user", "content": r["question"]}], temperature=0.0, max_tokens=120)
    # threshold-triggered compaction / full history (METHOD §10.6)
    import threshold_compaction as TC
    template("rescore_threshold_context_format", "{current summary}\n\n" + TC.TAIL_HEADER + "\n{role}: {content}\n{role}: {content}\n...",
             st, "benchmark_audit/threshold_compaction.py ThresholdCompaction.dump (systems '<adapter>@thr64k'; T = 64,000 estimated tokens = chars/4)",
             "full_history = the turns only, one '{role}: {content}' line each, no header")
    for name, bench_file in (("codex@thr64k", "rescore_mab_ruler_codex@thr64k.jsonl"), ("full_history", "rescore_locomo_full_history.jsonl")):
        f = ROOT / "benchmark_audit/results_v2" / bench_file
        if f.exists():
            rr = json.loads(open(f).readline())
            exemplar(f"rescore_answer_piA_{name.replace('@', '_')}", st, "native-protocol answer, threshold robustness check (METHOD §10.6)",
                     "rescore.py run_episode", QWEN, [{"role": "system", "content": RS.ANSWER_SYS.format(ctx=rr["ctx"])}, {"role": "user", "content": rr["question"]}],
                     temperature=0.0, max_tokens=120)
    exemplar("judge_locomo_rescore", "judging", "LoCoMo judge in re-scoring", "rescore.py judge", OSS,
             [{"role": "user", "content": get_anscheck_prompt("single-session-user", r["question"], r["gold"], r["pred"])}],
             temperature=0.0, max_tokens=600, reasoning_effort="low")


# =================================================================== C. PCME method (method/)
def section_method():
    import common as C
    from reask import FOLLOW
    from prior_draws import messages as draw_messages, eval_question
    st = "PCME method (Steps 1-2)"
    template("pcme_answer_system_piF", C.ANSWER_SYS_F, st, "method/common.py ANSWER_SYS_F (forced protocol pi_F)")
    template("pcme_prior_F1_system", C.F1_SYS, st, "method/common.py F1_SYS (closed-book draw F1)")
    template("pcme_prior_F2_user", C.F2_USER, st, "method/common.py F2_USER (closed-book draw F2, no system prompt)")
    template("pcme_followup_user", FOLLOW, st, "method/reask.py FOLLOW (compliance follow-up, pi_F+R)")
    from abstention_judge import PROMPT as AJ
    template("pcme_abstention_judge", AJ, "judging", "method/abstention_judge.py PROMPT (METHOD §10.4)")
    vs = ROOT / "method/results/abstention_validation_sample.jsonl"
    if vs.exists():
        r = json.loads(open(vs).readline())
        exemplar("pcme_abstention_judge", "judging", "abstention classification (validation sample + all answers)", "method/abstention_judge.py classify", OSS,
                 [{"role": "user", "content": AJ.format(question=r["question"], response=r["response"])}], temperature=0.0, max_tokens=400, reasoning_effort="low")
    items = {x["id"]: x for x in C.answerable_items()}
    draws = [json.loads(l) for l in open(ROOT / "method/results/prior_draws_qwen3-235b-a22b-2507.jsonl")]
    T = {"F1_T0": (0.0, 0), "F2_T0": (0.0, 0), "F0_T1_s1": (1.0, 1), "F0_T1_s2": (1.0, 2), "F0_T1_s3": (1.0, 3)}
    done = set()
    for d in draws:
        if (d["bench"], d["draw"]) in done:
            continue
        done.add((d["bench"], d["draw"]))
        x = items[d["id"]]; t, s = T[d["draw"]]
        exemplar(f"pcme_prior_{d['bench'].lower()}_{d['draw']}", st, "closed-book prior draw (E1.1, METHOD §2.1)", "method/prior_draws.py",
                 QWEN, draw_messages(d["draw"], x["q"]), temperature=t, max_tokens=150, sample_idx=s)
    done = set()
    for d in map(json.loads, open(ROOT / "method/results/prior_draws_qwen3-235b-a22b-2507_evalprompt.jsonl")):
        if d["bench"] in done:
            continue
        done.add(d["bench"])
        x = items[d["id"]]
        exemplar(f"pcme_prior_eval_{d['bench'].lower()}_{d['draw']}", st, "eval-prompt prior draw g' (remedy a, METHOD v1.1/v1.2)",
                 "method/prior_draws.py --variant eval", QWEN, draw_messages(d["draw"], eval_question(x)), temperature=1.0, max_tokens=120,
                 sample_idx=int(d["draw"][-1]))
    for s in ("empty", "oracle", "bm25_ev", "bm25_noev"):
        rows = [json.loads(l) for l in open(ROOT / f"method/results/refsys_{s}_F.jsonl")]
        for b in ("LoCoMo", "MemoryAgentBench"):
            r = next((r for r in rows if r["bench"] == b), None)
            if r:
                exemplar(f"pcme_refsys_{s}_{b.lower()}", st, "reference system under pi_F (E1.2, METHOD §6)", "method/reference_systems.py", QWEN,
                         [{"role": "system", "content": C.ANSWER_SYS_F.format(ctx=r["ctx"])}, {"role": "user", "content": r["question"]}],
                         temperature=0.0, max_tokens=120)
        if s == "empty":
            rr = next(r for r in map(json.loads, open(ROOT / "method/results/refsys_empty_Freask.jsonl")) if r.get("reasked"))
            exemplar("pcme_followup_refsys_empty", st, "compliance follow-up (remedy b, METHOD v1.1)", "method/reask.py", QWEN,
                     [{"role": "system", "content": C.ANSWER_SYS_F.format(ctx=rr["ctx"])}, {"role": "user", "content": rr["question"]},
                      {"role": "assistant", "content": rr["pred_original"]}, {"role": "user", "content": FOLLOW}],
                     temperature=0.0, max_tokens=120, sample_idx=100)
    pf = ROOT / "method/results/protocols_locomo_codex.jsonl"
    if pf.exists():
        ctx = {r["id"]: r["ctx"] for r in map(json.loads, open(ROOT / "benchmark_audit/results_v2/rescore_locomo_codex.jsonl"))}
        rows = [json.loads(l) for l in open(pf)]
        r = next(r for r in rows if r["answerable"])
        msgs = [{"role": "system", "content": C.ANSWER_SYS_F.format(ctx=ctx[r["id"]])}, {"role": "user", "content": r["question"]}]
        exemplar("pcme_protocol_piF_locomo_codex", st, "Step 2 forced-protocol answer", "method/protocols.py", QWEN, msgs, temperature=0.0, max_tokens=120)
        r = next(r for r in rows if r["answerable"] and r.get("abst_F_regex"))
        msgs = [{"role": "system", "content": C.ANSWER_SYS_F.format(ctx=ctx[r["id"]])}, {"role": "user", "content": r["question"]},
                {"role": "assistant", "content": r["pred_F"]}, {"role": "user", "content": FOLLOW}]
        exemplar("pcme_protocol_piFR_locomo_codex", st, "Step 2 pi_F+R follow-up", "method/protocols.py", QWEN, msgs, temperature=0.0, max_tokens=120, sample_idx=100)


# =================================================================== D. framework study (framework_study/)
def section_framework():
    import validate as V
    import v3_reproduction as V3
    import make_distractors as MD
    import probe as PR
    import sessions as SE
    import frameworks as FW
    from build_items import user_turn
    st = "framework study"
    items = [json.loads(l) for l in open(ROOT / "framework_study/stimuli/items.jsonl")]
    rule = next(x for x in items if x["type"] == "rule"); pref = next(x for x in items if x["type"] == "preference")
    # data-construction templates
    template("fw_user_turn_rule", "{task} {lead}{clause}.", "stimuli", "framework_study/stimuli/build_items.py user_turn (rule / procedure)")
    template("fw_user_turn_preference", "{lead}{clause}.", "stimuli", "build_items.py user_turn (preference; preceded by a filler question in sessions)")
    template("fw_seed_session", [{"role": "user", "content": "Hi Atlas!"}, {"role": "assistant", "content": "Hi Sam, how can I help today?"},
                                 {"role": "user", "content": "{user_turn(item 1)}"}, {"role": "assistant", "content": "{reply(item 1)}"},
                                 {"role": "user", "content": "{user_turn(item 2)}"}, {"role": "assistant", "content": "{reply(item 2)}"}],
             "stimuli", "framework_study/src/sessions.py build_history / item_exchange",
             "preference items: user = '{filler question} {user_turn}', assistant = '{filler answer} Got it.'")
    template("fw_distractor_generation", MD.PROMPT, "stimuli", "framework_study/src/make_distractors.py PROMPT (Qwen3-235B, T=0.8)")
    exemplar("fw_distractor_generation", "stimuli", "distractor sessions (stimuli/distractors.json)", "make_distractors.py", MD.GEN,
             [{"role": "user", "content": MD.PROMPT.format(task=MD.TASKS[0])}], temperature=0.8, max_tokens=500, sample_idx=0)
    users = SE.make_users(43); ds = SE.load_distractors()
    hist = SE.build_history(users[0], ds, n_distract=12, seed=0)
    (P / "exemplars" / "fw_user0_history.json").write_text(json.dumps(hist, indent=1, ensure_ascii=False))
    REG.append(dict(kind="exemplar", id="fw_user0_history", stage="stimuli", used_for="the full session sequence ingested by every framework for user 0",
                    source="sessions.build_history(make_users(43)[0], n_distract=12, seed=0)", verified=True, file="exemplars/fw_user0_history.json"))
    # V1 / V2
    template("fw_world_system", V.WORLD, "validation + probe", "framework_study/src/validate.py WORLD")
    template("fw_v1_prefix_rule", "You have no specific information about this. Give your best guess about what is most likely.\n", "validation",
             "validate.py v1 (rule / procedure items)")
    template("fw_v1_prefix_preference", "Sam has told you a preference about this, but you do not know which one. Give your best guess about which is more likely.\n",
             "validation", "validate.py v1 (preference items)")
    template("fw_forced_choice_question", V.ask("{question}", ["{option_1}", "{option_2}"], 0), "validation + probe",
             "validate.py ask (order 0; order 1 swaps the options)")
    for m, tag in ((QWEN, "qwen"), (LLAMA, "llama"), (OSS, "gptoss")):
        ex = {"max_tokens": 600, "reasoning_effort": "low"} if "gpt-oss" in m else {"max_tokens": 12}
        exemplar(f"fw_v1_{tag}", "validation", "V1 prior strength (20 draws per item)", "validate.py v1", m,
                 [{"role": "system", "content": V.WORLD}, {"role": "user", "content": "You have no specific information about this. Give your best guess about what is most likely.\n" + V.ask(rule["question"], rule["options"], 0)}],
                 temperature=1.0, sample_idx=0, **ex)
        exemplar(f"fw_v2_{tag}", "validation", "V2 comprehension", "validate.py v2", m,
                 [{"role": "system", "content": V.WORLD}, {"role": "user", "content": user_turn(rule, "I")}, {"role": "assistant", "content": rule["reply"]},
                  {"role": "user", "content": V.ask(rule["question"], rule["options"], 0)}], temperature=0.0, **ex)
    # V3
    template("fw_v3_system", V3.SYSTEM, "validation (V3 Bartlett positive control)", "framework_study/src/v3_reproduction.py SYSTEM")
    for fn in ("first_notes", "retell", "gist", "expand"):
        arg = {"first_notes": "{transcript}", "retell": "{notes}", "gist": "{notes}", "expand": "{gist}"}[fn]
        template(f"fw_v3_{fn}", getattr(V3, fn)(arg), "validation (V3)", f"v3_reproduction.py {fn}() (B = {V3.B} words)")
    template("fw_memory_state_judge", V3.JUDGE_PROMPT, "judging", "v3_reproduction.py JUDGE_PROMPT (memory-state coding; also probe.py)")
    sets = V3.make_sets()
    exemplar("fw_v3_first_notes", "validation (V3)", "V3 generation 0", "v3_reproduction.py run_chains", V3.COMPACTOR,
             V3.first_notes(V3.chat_transcript(sets[0])), temperature=1.0, max_tokens=400, sample_idx=0)
    # probe
    template("fw_probe_qa_system", PR.QA_SYSTEM, "probe", "framework_study/src/probe.py QA_SYSTEM (belief probe)")
    snaps = [json.loads(l) for l in open(ROOT / "framework_study/results/snapshots_codex.jsonl")]
    s = next(x for x in snaps if x["ckpt"] == 12)
    iid, v = s["assign"][0]; x = SE.ITEMS[iid]
    for j in V3.JUDGES:
        exemplar(f"fw_probe_judge_{'gptoss' if 'gpt-oss' in j else 'gemma'}", "judging", "memory-state coding of a framework dump", "probe.py main", j,
                 [{"role": "user", "content": V3.JUDGE_PROMPT.format(notes=s["dump"] or "(empty)", question=x["question"], a=x["options"][0], b=x["options"][1])}],
                 temperature=0.0, **({"max_tokens": 600, "reasoning_effort": "low"} if "gpt-oss" in j else {"max_tokens": 12}))
    ctx = s["contexts"].get(iid, s["dump"]) or "(nothing)"
    exemplar("fw_probe_belief", "probe", "belief probe (forced choice from the framework's context)", "probe.py main", QWEN,
             [{"role": "system", "content": PR.QA_SYSTEM.format(ctx=ctx)},
              {"role": "user", "content": f"{x['question']}\nAnswer with exactly one of these options and nothing else: {x['options'][0]} / {x['options'][1]}"}],
             temperature=0.0, max_tokens=12)
    # product compactors: template (placeholders) + verified replay of user 0's first sessions
    for name in ("codex", "openhands", "aider", "gemini_cli", "anthropic_api", "langchain_summary", "neutral_roll"):
        ad = FW.ADAPTERS[name](QWEN, temperature=0.0)
        box = {}

        def fake(messages, max_tokens=2048, box=box):
            box["messages"], box["max_tokens"] = messages, max_tokens
            return "<summary>{NEW_MEMORY}</summary><state_snapshot>{NEW_MEMORY}</state_snapshot>"
        ad.llm = fake
        turns = [{"role": "user", "content": "{SESSION_USER_TURN}"}, {"role": "assistant", "content": "{SESSION_ASSISTANT_TURN}"}]
        ad.ingest(turns)          # first session (no previous memory)
        t1 = box["messages"]
        ad.ingest(turns)          # second session (previous memory present)
        template(f"fw_compactor_{name}", {"first_session": t1, "later_sessions": box["messages"], "max_tokens": box["max_tokens"],
                                          "note": "{NEW_MEMORY} stands for the memory produced at the previous session"},
                 "framework compaction", f"framework_study/src/frameworks.py {type(ad).__name__}.ingest (verbatim product prompt + framing)")
        for model, tag in ((QWEN, "qwen235b"), (LOCAL, "qwen8b_local")):
            if model == LOCAL and name == "langchain_summary" and False:
                continue
            ad = FW.ADAPTERS[name](model, temperature=0.0)
            ok = {"n": 0, "found": 0}

            def lookup(messages, max_tokens=2048, ad=ad, ok=ok, tag=tag, name=name, model=model):
                k = ok["n"]; ok["n"] += 1
                resp = exemplar(f"fw_replay_{name}_{tag}_call{k}", "framework compaction", f"user 0, session {k + 1}", f"frameworks.py {type(ad).__name__}.ingest",
                                model, messages, temperature=0.0, max_tokens=max_tokens)
                if resp is None:
                    raise LookupError("not in cache")
                ok["found"] += 1
                return resp["text"]
            ad.llm = lookup
            try:
                for sess in hist[:3]:
                    ad.ingest(sess["messages"])
            except LookupError:
                pass
            print(f"  replay {name:18s} {tag:13s}: {ok['found']}/{ok['n']} calls verified")
    import langchain.agents.middleware.summarization as S
    template("lib_langchain_default_summary_prompt", S.DEFAULT_SUMMARY_PROMPT, "framework compaction (library default)",
             "langchain 1.4.3 langchain/agents/middleware/summarization.py DEFAULT_SUMMARY_PROMPT")


# =================================================================== E. step 3 gates on the expanded item set
def section_step3():
    import validate_v2 as G
    from validate import ask, WORLD
    st = "dataset gates (step 3)"
    items = {x["id"]: x for x in G.ITEMS}
    upd = next(x for x in G.ITEMS if x["type"] == "update")
    ph = dict(upd, initial_task="{initial_task}", initial_reply="{initial_reply}", initial_lead="{initial_lead}", task="{task}", reply="{reply}",
              lead="{lead}", C=dict(upd["C"], initial="{initial value statement}", clause="{update statement}"))
    template("v2_update_dialogue", [{"role": "system", "content": "{WORLD}"}] + G.item_turns(ph, "C") +
             [{"role": "user", "content": ask("{question}", ["{option_1}", "{option_2}"], 0)}],
             st, "framework_study/src/validate_v2.py item_turns (knowledge updates: initial value, then the update, then the question)")
    template("v2_preference_filler", list(G.PREF_FILLER), st, "framework_study/src/validate_v2.py PREF_FILLER (as in validate.v2)")
    first_new = next(x for x in G.ITEMS if x["origin"] == "v2" and x["type"] == "rule")
    for m in G.V1_MODELS:
        exemplar(f"v1_expanded_{G.tag(m)}", st, "V1 prior strength on the expanded set (20 draws per item)", "validate_v2.py requests", m,
                 [{"role": "system", "content": WORLD}, {"role": "user", "content": G.V1_PREFIX + ask(first_new["question"], first_new["options"], 0)}],
                 temperature=1.0, sample_idx=0, **G.extra(m))
    for t in ("rule", "preference", "update", "neutral"):
        x = next(x for x in G.ITEMS if x["type"] == t and x["origin"] == "v2")
        exemplar(f"v2_expanded_{t}", st, f"V2 comprehension, {t} item", "validate_v2.py requests", G.V2_MODELS[0],
                 [{"role": "system", "content": WORLD}] + G.item_turns(x, "I") + [{"role": "user", "content": ask(x["question"], x["options"], 0)}],
                 temperature=0.0, **G.extra(G.V2_MODELS[0]))

    import v3_reproduction as V3
    ch = json.load(open(ROOT / "framework_study/results/v3_v2_chains.json"))
    final = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "framework_study/stimuli/items_v2_final.jsonl")}
    saved_items = V3.ITEMS
    V3.ITEMS = [final[i] for i in ch["items"]]
    exemplar("v3_expanded_first_notes", st, "V3 positive control on the expanded set, generation 0", "v3_v2.py (v3_reproduction.run_chains)", V3.COMPACTOR,
             V3.first_notes(V3.chat_transcript([tuple(p) for p in ch["sets"][0]])), temperature=1.0, max_tokens=400, sample_idx=0)
    V3.ITEMS = saved_items
    import make_distractors as MD
    import make_distractors_v2 as MD2
    template("distractor_leak_check", MD2.LEAK_PROMPT, st, "framework_study/src/make_distractors_v2.py LEAK_PROMPT (layer 2 of the leak check)")
    exemplar("distractor_generation_v2", st, "new distractor sessions (same generator and prompt as round 1)", "make_distractors_v2.py", MD.GEN,
             [{"role": "user", "content": MD.PROMPT.format(task=MD2.NEW_TASKS[0])}], temperature=0.8, max_tokens=500, sample_idx=0)
    dv = json.load(open(ROOT / "framework_study/stimuli/distractors_v2.json"))
    fp = dv["flagged_pairs"][0]
    pool = {d["task"]: d for d in dv["sessions"] + dv["removed"]}
    exemplar("distractor_leak_check", st, "layer-2 leak check of one flagged (distractor, item) pair", "make_distractors_v2.py", MD2.JUDGE,
             [{"role": "user", "content": MD2.LEAK_PROMPT.format(t=pool[fp["distractor_task"]]["transcript"], q=items[fp["item"]]["question"] if fp["item"] in items else "")}],
             temperature=0.0, max_tokens=400, reasoning_effort="low")


# =================================================================== F. step 4 (second model family, expanded items)
def section_step4():
    import frameworks as FW
    import sessions_v2 as S2
    import probe as PR
    import v3_reproduction as V3
    st = "framework study, step 4 (Llama-3.3-70B and Qwen3-235B on the expanded items)"
    template("s4_update_initial_exchange", S2.initial_exchange(next(i for i, x in S2.ITEMS.items() if x["type"] == "update"), "C"), st,
             "framework_study/src/sessions_v2.py initial_exchange (initial value of an update item, placed in seeding session 1)")
    users = S2.make_users(192)
    hist = S2.build_history(users[0], S2.load_distractors(), n_distract=12, seed=0)
    for model, tag in ((LLAMA, "llama"), (QWEN, "qwen")):
        ad = FW.ADAPTERS["codex"](model, temperature=0.0)
        n = {"k": 0}

        def lookup(messages, max_tokens=2048, n=n, tag=tag, model=model):
            resp = exemplar(f"s4_replay_codex_{tag}_call{n['k']}", st, f"step-4 user 0, session {n['k'] + 1}", "frameworks.py Codex.ingest", model,
                            messages, temperature=0.0, max_tokens=max_tokens)
            n["k"] += 1
            if resp is None:
                raise LookupError
            return resp["text"]
        ad.llm = lookup
        try:
            for sess in hist[:2]:
                ad.ingest(sess["messages"])
        except LookupError:
            pass
        snaps = [json.loads(l) for l in open(ROOT / f"framework_study/results/snapshots_codex_s4{tag}.jsonl")]
        sn = next(x for x in snaps if x["ckpt"] == 12)
        iid, v = sn["assign"][0]; x = S2.ITEMS[iid]
        ctx = sn["contexts"].get(iid, sn["dump"]) or "(nothing)"
        exemplar(f"s4_probe_belief_{tag}", st, "belief probe by the family's own answer model", "probe.py main", model,
                 [{"role": "system", "content": PR.QA_SYSTEM.format(ctx=ctx)},
                  {"role": "user", "content": f"{x['question']}\nAnswer with exactly one of these options and nothing else: {x['options'][0]} / {x['options'][1]}"}],
                 temperature=0.0, max_tokens=12)


def main():
    for sec in (section_closed_book, section_rescore, section_method, section_framework, section_step3, section_step4):
        print("==", sec.__name__)
        try:
            sec()
        except Exception as e:
            import traceback; traceback.print_exc()
            REG.append(dict(kind="error", id=sec.__name__, error=repr(e)))
    (P / "registry.json").write_text(json.dumps(REG, indent=1, ensure_ascii=False))
    ex = [r for r in REG if r["kind"] == "exemplar"]
    bad = [r["id"] for r in ex if not r["verified"]]
    print(f"templates {sum(r['kind'] == 'template' for r in REG)}  exemplars {len(ex)}  verified {len(ex) - len(bad)}  NOT verified {len(bad)}: {bad}")
    print("errors:", [r for r in REG if r["kind"] == "error"])


if __name__ == "__main__":
    main()
