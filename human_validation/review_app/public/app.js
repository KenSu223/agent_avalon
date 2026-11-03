// Pair Review client. Talks to /api/* (functions/api/[[path]].js). All answers are in Version A / Version B terms.
"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, "");
    else if (v !== false && v != null) el.setAttribute(k, v);
  }
  for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  return el;
};

// ---------------------------------------------------------------- question definitions (shown in item view and guide)
const Q = {
  q1: { title: "Q1. How natural does each version sound?",
        help: "Rate it as a message a colleague might really type in a work chat. Judge the wording, not whether the fact is surprising.",
        anchors: "1 = clearly unnatural · 3 = acceptable · 5 = completely natural" },
  q2: { title: "Q2. Do the two versions differ only in the key fact?",
        help: "Differences are highlighted. Answer No if anything else differs too: extra details, different wording, a different tone." },
  q3: { title: "Q3. At a typical workplace, which version would you expect to be true?",
        help: "Imagine you know nothing about Sam's company. Which one matches how things usually are? There is no right answer; give your own view." },
  q4: { title: "Q4. Answer the question as if Sam had said only that version.",
        help: "Use only what Sam said. Choose \"Can't tell\" if the question has no single clear answer from that version." },
  q5: { title: "Q5. Could this be real somewhere?",
        help: "Could this be a genuine rule, procedure or preference at some workplace or for some person, even if it is unusual? Answer No only if it is nonsensical or impossible." },
  q6: { title: "Q6. Does either version signal surprise or give a reason?",
        help: "For example \"actually\", \"surprisingly\", \"believe it or not\", \"unlike most places\", or a \"because …\" clause." },
  q7: { title: "Q7. Anything else? (optional)", help: "Typos, odd phrasing, anything that could confuse a reader." },
};

// ---------------------------------------------------------------- state
const S = {
  token: new URLSearchParams(location.search).get("r"),
  data: null, answers: {}, idx: 0, screen: "loading",
  practiceIdx: 0, practiceAnswers: {}, practiceChecked: {},
  activeUid: null, lastActivity: Date.now(), pending: new Set(), saveTimer: null,
};
const LS_KEY = () => `pairreview:${S.token}`;
function lsSave() {
  try { localStorage.setItem(LS_KEY(), JSON.stringify({ answers: S.answers, pending: [...S.pending] })); } catch (e) { /* storage may be unavailable */ }
}
function lsLoad() {
  try { return JSON.parse(localStorage.getItem(LS_KEY()) || "null"); } catch (e) { return null; }
}

function emptyAnswer() {
  return { q1_natural: { A: null, B: null }, q2_minimal: null, q2_note: "", q3_expected: null,
           q4_answer: { A: null, B: null }, q5_plausible: { A: null, B: null }, q6_cue: null, q7_comment: "",
           flagged: false, flag_reason: "" };
}
function isComplete(p) {
  return p.q1_natural.A !== null && p.q1_natural.B !== null && p.q2_minimal !== null &&
    (p.q2_minimal === "yes" || p.q2_note.trim() !== "") && p.q3_expected !== null &&
    p.q4_answer.A !== null && p.q4_answer.B !== null && p.q5_plausible.A !== null && p.q5_plausible.B !== null &&
    p.q6_cue !== null && (!p.flagged || p.flag_reason.trim() !== "");
}
function entry(uid) {
  if (!S.answers[uid]) S.answers[uid] = { payload: emptyAnswer(), complete: false, seconds: 0 };
  return S.answers[uid];
}

// ---------------------------------------------------------------- server
async function api(path, method = "GET", body) {
  const res = await fetch(`/api/${path}`, { method, headers: body ? { "content-type": "application/json" } : {},
                                           body: body ? JSON.stringify(body) : undefined });
  const out = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
  if (!res.ok) throw new Error(out.error || `HTTP ${res.status}`);
  return out;
}
function setSaveState(text, bad = false) {
  const el = $("#savestate"); el.textContent = text; el.classList.toggle("bad", bad);
}
function queueSave(uid) {
  S.pending.add(uid); lsSave(); setSaveState("Saving…");
  clearTimeout(S.saveTimer); S.saveTimer = setTimeout(flush, 500);
}
async function flush() {
  if (S.data?.submitted) return;
  for (const uid of [...S.pending]) {
    const e = S.answers[uid];
    try {
      const r = await api("answer", "PUT", { r: S.token, uid, payload: e.payload, seconds: Math.round(e.seconds) });
      e.complete = r.complete; S.pending.delete(uid);
    } catch (err) {
      setSaveState("Not saved – will retry (kept in this browser)", true); lsSave();
      setTimeout(flush, 5000); return;
    }
  }
  lsSave(); setSaveState("All changes saved");
  if ($("#overview")) screenOverview();            // the Submit button depends on pending saves
}

// ---------------------------------------------------------------- timing: active seconds on the current item
setInterval(() => {
  if (!S.activeUid || document.visibilityState !== "visible" || Date.now() - S.lastActivity > 120000) return;
  entry(S.activeUid).seconds += 1;
}, 1000);
["mousemove", "keydown", "click", "scroll", "touchstart"].forEach((ev) =>
  addEventListener(ev, () => { S.lastActivity = Date.now(); }, { passive: true }));

// ---------------------------------------------------------------- rendering helpers
function segs(list) { return list.map((s) => (s.d ? h("mark", {}, s.t) : document.createTextNode(s.t))); }
function versionCard(name, turns) {
  return h("div", { class: "version" }, h("div", { class: "vlabel" }, `Version ${name}`),
    turns.map((t) => [
      t.label ? h("div", { class: "turnlabel" }, t.label) : null,
      h("div", { class: "bubble sam" }, h("span", { class: "who" }, "Sam: "), segs(t.user)),
      h("div", { class: "bubble asst" }, h("span", { class: "who" }, "Assistant: "), segs(t.assistant)),
    ]));
}
function seg(options, current, onPick) {
  // options: [[value, label], ...]
  const box = h("div", { class: "seg", role: "group" });
  for (const [v, label] of options) {
    box.append(h("button", { type: "button", "aria-pressed": String(current === v),
      onclick: () => { if (current !== v) onPick(v); } }, label));
  }
  return box;
}
function qBlock(key, missing, ...body) {
  return h("div", { class: `q${missing ? " missing" : ""}` },
    h("div", { class: "qtitle" }, Q[key].title), h("div", { class: "qhelp" }, Q[key].help),
    Q[key].anchors ? h("div", { class: "scale-anchors" }, Q[key].anchors) : null, body);
}
const optLabel = (o) => (o === "cant_tell" ? "Can't tell" : o);

// The item view: both versions plus the seven questions. `p` is mutated; `changed` is called after every edit.
function itemView(item, p, changed, { showMissing = false } = {}) {
  const rerender = () => { changed(); };
  const scale = [1, 2, 3, 4, 5].map((n) => [n, String(n)]);
  const q4opts = [...item.options.map((o) => [o, o]), ["cant_tell", "Can't tell"]];
  const miss = (cond) => showMissing && cond;
  const form = h("div", {},
    qBlock("q1", miss(p.q1_natural.A === null || p.q1_natural.B === null),
      ["A", "B"].map((v) => h("div", { class: "qrow" }, h("span", { class: "rowlabel" }, `Version ${v}`),
        seg(scale, p.q1_natural[v], (x) => { p.q1_natural[v] = x; rerender(); })))),
    qBlock("q2", miss(p.q2_minimal === null || (p.q2_minimal === "no" && !p.q2_note.trim())),
      seg([["yes", "Yes – only the key fact differs"], ["no", "No – something else differs too"]], p.q2_minimal,
        (x) => { p.q2_minimal = x; rerender(); }),
      p.q2_minimal === "no" ? h("div", { class: "qrow" }, h("textarea", { placeholder: "What else differs? (required)",
        oninput: (e) => { p.q2_note = e.target.value; changed(true); } }, p.q2_note)) : null),
    qBlock("q3", miss(p.q3_expected === null),
      seg([["A", "Version A"], ["B", "Version B"], ["both", "Both equally"], ["neither", "Neither"]], p.q3_expected,
        (x) => { p.q3_expected = x; rerender(); })),
    qBlock("q4", miss(p.q4_answer.A === null || p.q4_answer.B === null),
      ["A", "B"].map((v) => h("div", { class: "qrow" }, h("span", { class: "rowlabel" }, `Only ${v}`),
        seg(q4opts, p.q4_answer[v], (x) => { p.q4_answer[v] = x; rerender(); })))),
    qBlock("q5", miss(p.q5_plausible.A === null || p.q5_plausible.B === null),
      ["A", "B"].map((v) => h("div", { class: "qrow" }, h("span", { class: "rowlabel" }, `Version ${v}`),
        seg([["yes", "Yes"], ["unsure", "Unsure"], ["no", "No"]], p.q5_plausible[v],
          (x) => { p.q5_plausible[v] = x; rerender(); })))),
    qBlock("q6", miss(p.q6_cue === null),
      seg([["none", "No cue"], ["A", "Cue in A"], ["B", "Cue in B"], ["both", "Cue in both"]], p.q6_cue,
        (x) => { p.q6_cue = x; rerender(); })),
    qBlock("q7", false, h("textarea", { placeholder: "Optional", oninput: (e) => { p.q7_comment = e.target.value; changed(true); } },
      p.q7_comment)),
  );
  return h("div", {},
    h("div", { class: "panel" },
      item.A.length > 1
        ? h("div", { class: "context" }, "Sam is chatting with an AI assistant at work. In an earlier message Sam mentions a fact in " +
            "passing, and in a later session Sam says that it has changed. Below are two versions of these messages; the words " +
            "that differ are highlighted. For Q3 and Q5, judge the situation after the change.")
        : h("div", { class: "context" }, "Sam is chatting with an AI assistant at work. In this message Sam asks for something unrelated " +
            "and mentions a fact in passing. Below are two versions of the same message; the words that differ are highlighted."),
      h("div", { class: "versions" }, versionCard("A", item.A), versionCard("B", item.B)),
      h("div", { class: "question" }, h("strong", {}, "Later, the assistant is asked: "), item.question)),
    h("div", { class: "panel" }, form));
}

// ---------------------------------------------------------------- screens
function setTop() {
  const d = S.data;
  $("#topinfo").textContent = d ? `Reviewer ${d.reviewer}` : "";
  $("#topnav").hidden = !d || S.screen !== "review";
}
function show(...nodes) { const app = $("#app"); app.replaceChildren(...nodes); setTop(); window.scrollTo(0, 0); }

function guideContent() {
  return h("div", { class: "guide" },
    h("h2", {}, "What you are doing"),
    h("p", {}, "We are building a test of whether AI assistants remember what users tell them. Each item shows two versions " +
      "of one message from a user, Sam, to a work assistant. In the message, Sam asks for something unrelated and mentions a " +
      "fact in passing. The two versions should be identical except for that fact. Later the assistant is asked a question " +
      "about the fact. Your job is to check that each pair is well made."),
    h("h2", {}, "The questions"),
    h("ul", {}, Object.values(Q).map((q) => h("li", {}, h("strong", {}, q.title), " ", q.help))),
    h("h2", {}, "Rules"),
    h("ul", {},
      h("li", {}, "Work on your own. Do not discuss items with other reviewers and do not use AI tools or web search."),
      h("li", {}, "Q1, Q3 and Q5 ask for your own judgment; there is no right answer. Q2, Q4 and Q6 are checks with a clear answer."),
      h("li", {}, "Expect about one minute per item. Take breaks whenever you like."),
      h("li", {}, "Answers save automatically. You can close the page and come back with the same link."),
      h("li", {}, "If something about an item looks wrong in a way the questions do not cover, use \"Flag this item\"."),
      h("li", {}, "Keyboard: ", h("span", { class: "kbd" }, "←"), " / ", h("span", { class: "kbd" }, "→"), " previous / next item.")));
}
function screenWelcome() {
  S.screen = "welcome";
  show(h("div", { class: "panel" }, h("h1", {}, "Welcome"), guideContent(),
    h("p", {}, `You will first do ${S.data.practice.length} practice items. After each one you will see our answers and why. ` +
      `Then you will review ${S.data.items.length} items.`),
    h("button", { class: "primary", onclick: () => screenPractice(0) }, "Start practice")));
}

function screenPractice(i) {
  S.screen = "practice"; S.practiceIdx = i; S.activeUid = null;
  const item = S.data.practice[i];
  const p = (S.practiceAnswers[item.uid] ||= emptyAnswer());
  const checked = S.practiceChecked[item.uid];
  const redraw = (textOnly) => {
    if (!textOnly) { const y = window.scrollY; screenPractice(i); window.scrollTo(0, y); return; }
    const b = $("#check-btn");                       // text edits do not re-render (focus would be lost)
    if (b) { b.disabled = !isComplete(p); b.textContent = isComplete(p) ? "Check my answers" : "Answer all questions to check"; }
  };
  const view = itemView(item, p, redraw, { showMissing: !!checked });
  const fb = checked ? feedback(item, p) : null;
  const last = i === S.data.practice.length - 1;
  show(h("div", { class: "panel" }, h("h1", {}, `Practice ${i + 1} of ${S.data.practice.length}`),
         h("div", { class: "progress" }, h("div", { style: `width:${(100 * i) / S.data.practice.length}%` }))),
    view,
    h("div", { class: "panel" },
      fb,
      h("div", { class: "navrow" },
        i > 0 ? h("button", { class: "ghost", onclick: () => screenPractice(i - 1) }, "← Back") : h("span"),
        !checked
          ? h("button", { class: "primary", id: "check-btn", disabled: !isComplete(p), onclick: () => { S.practiceChecked[item.uid] = true; screenPractice(i); } },
              isComplete(p) ? "Check my answers" : "Answer all questions to check")
          : h("button", { class: "primary", onclick: () => (last ? finishPractice() : screenPractice(i + 1)) },
              last ? "Start the review →" : "Next practice item →"))));
}
function practiceMatches(item, p) {
  const e = item.expect;
  return { q2: p.q2_minimal === e.q2_minimal, q4: p.q4_answer.A === e.q4_answer.A && p.q4_answer.B === e.q4_answer.B,
           q6: p.q6_cue === e.q6_cue };
}
function feedback(item, p) {
  const e = item.expect, m = practiceMatches(item, p);
  const row = (ok, label, ours) => h("div", { class: "row" }, h("span", { class: ok ? "good" : "bad" }, ok ? "✓ " : "✗ "),
    h("strong", {}, label), ` Our answer: ${ours}`);
  const cue = { none: "No cue", A: "Cue in A", B: "Cue in B", both: "Cue in both" };
  return h("div", { class: "feedback" },
    row(m.q2, "Q2.", e.q2_minimal === "yes" ? "Yes – only the key fact differs" : "No – something else differs too"),
    row(m.q4, "Q4.", `only A: ${optLabel(e.q4_answer.A)}; only B: ${optLabel(e.q4_answer.B)}`),
    row(m.q6, "Q6.", cue[e.q6_cue]),
    h("div", { class: "row" }, h("strong", {}, "Q3 (your judgment). "), `Most people would probably say: ${
      { A: "Version A", B: "Version B", both: "both equally", neither: "neither" }[e.q3_expected]}.`),
    h("p", {}, item.explain));
}
async function finishPractice() {
  const result = S.data.practice.map((it) => ({ uid: it.uid, answers: S.practiceAnswers[it.uid], matched: practiceMatches(it, S.practiceAnswers[it.uid]) }));
  try { await api("training", "POST", { r: S.token, result }); } catch (e) { /* not fatal: shown again next time */ }
  S.data.training_done = true;
  const first = S.data.items.findIndex((it) => !entry(it.uid).complete);
  screenReview(first < 0 ? 0 : first);
}

function screenReview(i) {
  if (S.activeUid && S.activeUid !== S.data.items[i]?.uid && S.answers[S.activeUid]) queueSave(S.activeUid); // persist time
  S.screen = "review"; S.idx = i;
  const item = S.data.items[i], e = entry(item.uid), p = e.payload, n = S.data.items.length;
  S.activeUid = item.uid;
  const done = S.data.items.filter((it) => S.answers[it.uid]?.complete).length;
  const changed = (textOnly) => {
    e.complete = isComplete(p); queueSave(item.uid);
    if (!textOnly) return screenReviewKeepScroll(i);
    const st = $("#item-status");                    // text edits do not re-render (focus would be lost)
    if (st) { st.className = e.complete ? "muted" : "status-note"; st.textContent = e.complete ? "✓ Complete" : "Some questions are unanswered"; }
  };
  const view = itemView(item, p, changed, { showMissing: S.showMissing === item.uid });
  const flag = h("div", { class: "flagbox" },
    h("input", { type: "checkbox", id: "flag", checked: p.flagged, onchange: (ev) => { p.flagged = ev.target.checked; changed(); } }),
    h("label", { for: "flag" }, "Flag this item as problematic"));
  show(
    h("div", { class: "panel" },
      h("div", { class: "navrow" }, h("h1", {}, `Item ${i + 1} of ${n}`), h("span", { class: "muted" }, `${done} of ${n} complete`)),
      h("div", { class: "progress" }, h("div", { style: `width:${(100 * done) / n}%` }))),
    view,
    h("div", { class: "panel" },
      flag,
      p.flagged ? h("div", { class: "qrow" }, h("textarea", { placeholder: "Why is this item problematic? (required)",
        oninput: (ev) => { p.flag_reason = ev.target.value; changed(true); } }, p.flag_reason)) : null,
      h("div", { class: "navrow" },
        h("button", { class: "ghost", disabled: i === 0, onclick: () => screenReview(i - 1) }, "← Back"),
        h("span", { id: "item-status", class: isComplete(p) ? "muted" : "status-note" },
          isComplete(p) ? "✓ Complete" : "Some questions are unanswered"),
        i < n - 1
          ? h("button", { class: "primary", onclick: () => { if (!isComplete(p)) S.showMissing = item.uid; screenReview(i + 1); } }, "Next →")
          : h("button", { class: "primary", onclick: screenOverview }, "Finish →"))));
}
function screenReviewKeepScroll(i) { const y = window.scrollY; screenReview(i); window.scrollTo(0, y); }

function screenOverview() {
  const items = S.data.items, n = items.length;
  const done = items.filter((it) => S.answers[it.uid]?.complete).length;
  const body = h("div", { id: "overview" },
    h("h2", {}, "Overview"),
    h("p", { class: "legend" }, "Green: complete · Orange: started · Red outline: flagged. Click a number to go to that item."),
    h("div", { class: "grid" }, items.map((it, k) => {
      const e = S.answers[it.uid];
      const cls = e?.complete ? "done" : e ? "partial" : "";
      return h("button", { class: `${cls}${e?.payload.flagged ? " flag" : ""}`,
        onclick: () => { $("#overlay").close(); screenReview(k); } }, String(k + 1));
    })),
    h("p", {}, `${done} of ${n} items complete.`),
    S.data.submitted ? h("p", {}, "Your answers are submitted.") :
      h("button", { class: "primary", disabled: done < n || S.pending.size > 0, onclick: submitAll },
        done < n ? `Complete all items to submit (${n - done} left)` : "Submit all answers"));
  $("#overlay-body").replaceChildren(body); if (!$("#overlay").open) $("#overlay").showModal();
}
async function submitAll() {
  if (!confirm("Submit all answers? After submitting you can no longer change them.")) return;
  await flush();
  try { await api("submit", "POST", { r: S.token }); S.data.submitted = true; $("#overlay").close(); screenDone(); }
  catch (e) { alert(`Could not submit: ${e.message}`); }
}
function screenDone() {
  S.screen = "done"; S.activeUid = null;
  show(h("div", { class: "panel" }, h("h1", {}, "Thank you"),
    h("p", {}, "Your answers are submitted and locked. You can download a copy for your records."),
    h("button", { class: "ghost", onclick: download }, "Download my answers")));
}
function download() {
  const out = { reviewer: S.data.reviewer, app_version: S.data.app_version, guideline_version: S.data.guideline_version,
                exported_at: new Date().toISOString(),
                answers: S.data.items.map((it, k) => ({ position: k + 1, uid: it.uid, ...(S.answers[it.uid] || {}) })) };
  const a = h("a", { href: URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: "application/json" })),
                     download: `pair-review-${S.data.reviewer}.json` });
  document.body.append(a); a.click(); a.remove();
}

// ---------------------------------------------------------------- boot
$("#overlay").addEventListener("close", () => $("#overlay-body").replaceChildren());
$("#btn-guide").onclick = () => { $("#overlay-body").replaceChildren(guideContent()); $("#overlay").showModal(); };
$("#btn-overview").onclick = screenOverview;
$("#btn-download").onclick = download;
addEventListener("keydown", (ev) => {
  if (S.screen !== "review" || ["TEXTAREA", "INPUT"].includes(ev.target.tagName) || $("#overlay").open) return;
  if (ev.key === "ArrowRight" && S.idx < S.data.items.length - 1) screenReview(S.idx + 1);
  if (ev.key === "ArrowLeft" && S.idx > 0) screenReview(S.idx - 1);
});
addEventListener("beforeunload", (ev) => { if (S.pending.size) { flush(); ev.preventDefault(); } });

(async function boot() {
  if (!S.token) { show(h("div", { class: "panel" }, h("h1", {}, "Missing review link"), h("p", {}, "Please open the personal link you were sent."))); return; }
  try { S.data = await api(`session?r=${encodeURIComponent(S.token)}`); }
  catch (e) { show(h("div", { class: "panel" }, h("h1", {}, "Cannot open this review"), h("p", {}, e.message))); return; }
  S.answers = S.data.answers || {};
  const local = lsLoad();                      // re-send anything saved only in this browser
  if (local && !S.data.submitted) {
    for (const uid of local.pending || []) if (local.answers[uid]) { S.answers[uid] = local.answers[uid]; S.pending.add(uid); }
    if (S.pending.size) flush();
  }
  setSaveState(S.pending.size ? "Saving…" : "All changes saved");
  if (S.data.submitted) return screenDone();
  if (!S.data.training_done) return screenWelcome();
  const first = S.data.items.findIndex((it) => !S.answers[it.uid]?.complete);
  screenReview(first < 0 ? 0 : first);
})();
