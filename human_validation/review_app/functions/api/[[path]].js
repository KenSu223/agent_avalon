// Pair-review API (Cloudflare Pages Function, D1 binding DB).
//   GET  /api/session?r=TOKEN      items for this reviewer + saved answers + state
//   PUT  /api/answer               {r, uid, payload, seconds}
//   POST /api/training             {r, result}
//   POST /api/submit               {r}
// The bundle holds only Version A / Version B texts; which one is congruent is never sent to or stored by the server.
import bundle from "../../data/bundle.json";

const now = () => new Date().toISOString();
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

function reviewerFor(token) {
  return token && Object.prototype.hasOwnProperty.call(bundle.reviewers, token) ? bundle.reviewers[token] : null;
}

const oneOf = (v, allowed) => v === null || allowed.includes(v);
const str = (v, max) => typeof v === "string" && v.length <= max;

// Returns [cleanPayload, complete] or throws a message.
function validate(p, item) {
  if (!p || typeof p !== "object") throw "payload must be an object";
  const scale = [1, 2, 3, 4, 5];
  const opts = [...item.options, "cant_tell"];
  const q = {
    q1_natural: { A: p.q1_natural?.A ?? null, B: p.q1_natural?.B ?? null },
    q2_minimal: p.q2_minimal ?? null,
    q2_note: p.q2_note ?? "",
    q3_expected: p.q3_expected ?? null,
    q4_answer: { A: p.q4_answer?.A ?? null, B: p.q4_answer?.B ?? null },
    q5_plausible: { A: p.q5_plausible?.A ?? null, B: p.q5_plausible?.B ?? null },
    q6_cue: p.q6_cue ?? null,
    q7_comment: p.q7_comment ?? "",
    flagged: !!p.flagged,
    flag_reason: p.flag_reason ?? "",
  };
  if (!oneOf(q.q1_natural.A, scale) || !oneOf(q.q1_natural.B, scale)) throw "q1_natural must be 1-5";
  if (!oneOf(q.q2_minimal, ["yes", "no"])) throw "q2_minimal";
  if (!str(q.q2_note, 1000)) throw "q2_note";
  if (!oneOf(q.q3_expected, ["A", "B", "both", "neither"])) throw "q3_expected";
  if (!oneOf(q.q4_answer.A, opts) || !oneOf(q.q4_answer.B, opts)) throw "q4_answer";
  const pl = ["yes", "unsure", "no"];
  if (!oneOf(q.q5_plausible.A, pl) || !oneOf(q.q5_plausible.B, pl)) throw "q5_plausible";
  if (!oneOf(q.q6_cue, ["none", "A", "B", "both"])) throw "q6_cue";
  if (!str(q.q7_comment, 2000) || !str(q.flag_reason, 1000)) throw "comment too long";
  const complete =
    q.q1_natural.A !== null && q.q1_natural.B !== null && q.q2_minimal !== null &&
    (q.q2_minimal === "yes" || q.q2_note.trim().length > 0) && q.q3_expected !== null &&
    q.q4_answer.A !== null && q.q4_answer.B !== null && q.q5_plausible.A !== null && q.q5_plausible.B !== null &&
    q.q6_cue !== null && (!q.flagged || q.flag_reason.trim().length > 0);
  return [q, complete];
}

async function touch(db, reviewer) {
  const t = now();
  await db.prepare(
    "INSERT INTO reviewer_state (reviewer, first_seen_at, last_seen_at) VALUES (?1, ?2, ?2) " +
    "ON CONFLICT(reviewer) DO UPDATE SET last_seen_at = ?2").bind(reviewer, t).run();
  return db.prepare("SELECT * FROM reviewer_state WHERE reviewer = ?1").bind(reviewer).first();
}

export async function onRequest({ request, env, params }) {
  const route = (params.path || []).join("/");
  const url = new URL(request.url);
  const db = env.DB;
  try {
    if (route === "session" && request.method === "GET") {
      const rv = reviewerFor(url.searchParams.get("r"));
      if (!rv) return json({ error: "Unknown review link. Please check the link you were sent." }, 404);
      const state = await touch(db, rv.reviewer);
      const rows = await db.prepare("SELECT uid, payload, complete, seconds FROM answers WHERE reviewer = ?1")
        .bind(rv.reviewer).all();
      const answers = {};
      for (const r of rows.results) answers[r.uid] = { payload: JSON.parse(r.payload), complete: !!r.complete, seconds: r.seconds };
      return json({
        reviewer: rv.reviewer, app_version: bundle.app_version, guideline_version: bundle.guideline_version,
        items: rv.items, practice: bundle.practice, answers,
        training_done: !!state.training_done_at, submitted: !!state.submitted_at,
      });
    }

    const body = request.method === "GET" ? {} : await request.json().catch(() => ({}));
    const rv = reviewerFor(body.r);
    if (!rv) return json({ error: "unknown token" }, 404);
    const state = await touch(db, rv.reviewer);

    if (route === "answer" && request.method === "PUT") {
      if (state.submitted_at) return json({ error: "Answers were already submitted and are locked." }, 409);
      const item = rv.items.find((i) => i.uid === body.uid);
      if (!item) return json({ error: "item not assigned to this reviewer" }, 400);
      const seconds = Number(body.seconds);
      if (!Number.isFinite(seconds) || seconds < 0 || seconds > 86400) return json({ error: "seconds" }, 400);
      let clean, complete;
      try { [clean, complete] = validate(body.payload, item); } catch (m) { return json({ error: `invalid answer: ${m}` }, 400); }
      const t = now(), p = JSON.stringify(clean);
      await db.batch([
        db.prepare(
          "INSERT INTO answers (reviewer, uid, payload, complete, seconds, app_version, guideline_version, created_at, updated_at) " +
          "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?8) ON CONFLICT(reviewer, uid) DO UPDATE SET payload = ?3, complete = ?4, " +
          "seconds = ?5, app_version = ?6, guideline_version = ?7, updated_at = ?8")
          .bind(rv.reviewer, body.uid, p, complete ? 1 : 0, seconds, bundle.app_version, bundle.guideline_version, t),
        db.prepare("INSERT INTO answer_log (reviewer, uid, payload, seconds, at) VALUES (?1, ?2, ?3, ?4, ?5)")
          .bind(rv.reviewer, body.uid, p, seconds, t),
      ]);
      return json({ ok: true, complete, saved_at: t });
    }

    if (route === "training" && request.method === "POST") {
      const result = JSON.stringify(body.result ?? null);
      if (result.length > 20000) return json({ error: "too large" }, 400);
      await db.prepare("UPDATE reviewer_state SET training_done_at = ?2, training_result = ?3 WHERE reviewer = ?1")
        .bind(rv.reviewer, now(), result).run();
      return json({ ok: true });
    }

    if (route === "submit" && request.method === "POST") {
      if (state.submitted_at) return json({ ok: true, submitted_at: state.submitted_at });
      const row = await db.prepare("SELECT COUNT(*) AS n FROM answers WHERE reviewer = ?1 AND complete = 1")
        .bind(rv.reviewer).first();
      if (row.n < rv.items.length)
        return json({ error: `${rv.items.length - row.n} item(s) are not complete yet.` }, 400);
      const t = now();
      await db.prepare("UPDATE reviewer_state SET submitted_at = ?2 WHERE reviewer = ?1").bind(rv.reviewer, t).run();
      return json({ ok: true, submitted_at: t });
    }

    return json({ error: "not found" }, 404);
  } catch (e) {
    return json({ error: "server error", detail: String(e && e.message || e) }, 500);
  }
}
