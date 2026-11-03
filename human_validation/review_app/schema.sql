-- D1 schema for the pair-review app. Answers are stored in A/B terms; decoding to C/I uses private/key.json locally.

-- latest answer per reviewer and assignment
CREATE TABLE IF NOT EXISTS answers (
  reviewer   TEXT NOT NULL,
  uid        TEXT NOT NULL,
  payload    TEXT NOT NULL,          -- JSON, validated by the API
  complete   INTEGER NOT NULL,       -- 1 if every required field is answered
  seconds    REAL NOT NULL,          -- active time on the item, cumulative
  app_version TEXT NOT NULL,
  guideline_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (reviewer, uid)
);

-- append-only history of every save (audit trail)
CREATE TABLE IF NOT EXISTS answer_log (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  reviewer TEXT NOT NULL,
  uid      TEXT NOT NULL,
  payload  TEXT NOT NULL,
  seconds  REAL NOT NULL,
  at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviewer_state (
  reviewer        TEXT PRIMARY KEY,
  first_seen_at   TEXT,
  last_seen_at    TEXT,
  training_done_at TEXT,
  training_result TEXT,              -- JSON: per practice item, the reviewer's answers and whether they matched
  submitted_at    TEXT
);
