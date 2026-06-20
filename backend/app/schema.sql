CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  display_name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_goals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  exam_type TEXT NOT NULL DEFAULT 'CET-6',
  days_until_exam INTEGER,
  target_score INTEGER,
  daily_minutes INTEGER,
  self_reported_weaknesses TEXT NOT NULL DEFAULT '[]',
  interest_topics TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profile_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  profile_json TEXT NOT NULL,
  evidence_refs TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profile_update_suggestions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ability TEXT NOT NULL,
  direction TEXT NOT NULL,
  reason TEXT NOT NULL,
  evidence_refs TEXT NOT NULL DEFAULT '[]',
  agent_payload TEXT NOT NULL DEFAULT '{}',
  validation_status TEXT NOT NULL DEFAULT 'NEEDS_REVIEW',
  rejection_reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vocabulary_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  text TEXT NOT NULL,
  meaning_zh TEXT,
  tags TEXT NOT NULL DEFAULT '[]',
  source_type TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_vocabulary_items_text
  ON vocabulary_items(text);

CREATE TABLE IF NOT EXISTS reading_documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  file_name TEXT,
  raw_text TEXT NOT NULL,
  analysis_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_vocabulary_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  vocabulary_item_id INTEGER NOT NULL REFERENCES vocabulary_items(id) ON DELETE CASCADE,
  meaning_zh TEXT,
  usage_note TEXT NOT NULL DEFAULT '',
  ability TEXT,
  source_document_id INTEGER REFERENCES reading_documents(id) ON DELETE SET NULL,
  source_context TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, vocabulary_item_id)
);

CREATE TABLE IF NOT EXISTS candidate_vocabulary_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workflow_stage TEXT NOT NULL,
  ability TEXT,
  candidate_items TEXT NOT NULL DEFAULT '[]',
  included_sidequest_signal_ids TEXT NOT NULL DEFAULT '[]',
  selection_reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skill_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_id TEXT NOT NULL,
  version TEXT NOT NULL,
  target_ability TEXT NOT NULL,
  applicable_conditions TEXT NOT NULL DEFAULT '{}',
  difficulty_params TEXT NOT NULL DEFAULT '{}',
  generation_rules TEXT NOT NULL DEFAULT '{}',
  quality_requirements TEXT NOT NULL DEFAULT '{}',
  observable_evidence TEXT NOT NULL DEFAULT '{}',
  common_error_types TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(skill_id, version)
);

CREATE TABLE IF NOT EXISTS training_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  stage TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS generated_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES training_sessions(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  task_type TEXT NOT NULL,
  skill_version_id INTEGER REFERENCES skill_versions(id),
  target_ability TEXT NOT NULL,
  difficulty_params TEXT NOT NULL DEFAULT '{}',
  content_json TEXT NOT NULL DEFAULT '{}',
  quality_requirements TEXT NOT NULL DEFAULT '{}',
  quality_check_result TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generated_task_validations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER REFERENCES generated_tasks(id) ON DELETE CASCADE,
  validation_status TEXT NOT NULL,
  error_codes TEXT NOT NULL DEFAULT '[]',
  error_details TEXT NOT NULL DEFAULT '{}',
  attempt_number INTEGER NOT NULL,
  used_seed_fallback INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id INTEGER REFERENCES training_sessions(id) ON DELETE SET NULL,
  task_id INTEGER REFERENCES generated_tasks(id) ON DELETE SET NULL,
  evidence_type TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sidequest_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  task_name TEXT NOT NULL,
  objective_json TEXT NOT NULL DEFAULT '{}',
  result_json TEXT NOT NULL DEFAULT '{}',
  completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sidequest_signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  sidequest_run_id INTEGER NOT NULL REFERENCES sidequest_runs(id) ON DELETE CASCADE,
  scene TEXT NOT NULL,
  vocabulary_item_id INTEGER REFERENCES vocabulary_items(id) ON DELETE SET NULL,
  expression_text TEXT,
  context_json TEXT NOT NULL DEFAULT '{}',
  signal_type TEXT NOT NULL,
  is_pending_verification INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS isolated_test_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_ability TEXT NOT NULL,
  item_version TEXT NOT NULL,
  item_payload TEXT NOT NULL DEFAULT '{}',
  answer_key TEXT NOT NULL DEFAULT '{}',
  answer_rationale TEXT NOT NULL DEFAULT '{}',
  distractor_rationale TEXT NOT NULL DEFAULT '{}',
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS isolated_test_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id INTEGER REFERENCES training_sessions(id) ON DELETE SET NULL,
  user_answers TEXT NOT NULL DEFAULT '{}',
  score_json TEXT NOT NULL DEFAULT '{}',
  time_spent_seconds INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS isolated_attempt_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id INTEGER NOT NULL REFERENCES isolated_test_attempts(id) ON DELETE CASCADE,
  isolated_test_item_id INTEGER NOT NULL REFERENCES isolated_test_items(id) ON DELETE CASCADE,
  item_order INTEGER NOT NULL,
  item_version TEXT NOT NULL,
  UNIQUE(attempt_id, isolated_test_item_id)
);

CREATE TABLE IF NOT EXISTS tool_call_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  session_id INTEGER REFERENCES training_sessions(id) ON DELETE SET NULL,
  call_name TEXT NOT NULL,
  call_type TEXT NOT NULL,
  input_json TEXT NOT NULL DEFAULT '{}',
  output_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL,
  error_code TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_decision_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  session_id INTEGER REFERENCES training_sessions(id) ON DELETE SET NULL,
  decision_type TEXT NOT NULL,
  input_summary_json TEXT NOT NULL DEFAULT '{}',
  decision_json TEXT NOT NULL DEFAULT '{}',
  evidence_refs TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
