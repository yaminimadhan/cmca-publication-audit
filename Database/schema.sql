-- CMCA Publication Audit — COMPLETE SQLite Schema
-- Matches CMCA authors to PDF authors BY NAME (not by ID) using a helper table and views.

PRAGMA foreign_keys = ON;

-- =========================================================
-- 1) users
-- =========================================================
CREATE TABLE IF NOT EXISTS users (
  user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,  -- store a hash, not plaintext
  user_type     TEXT NOT NULL CHECK (user_type IN ('admin','analyst','viewer')),
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =========================================================
-- 2) projects
-- =========================================================
CREATE TABLE IF NOT EXISTS projects (
  project_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  project_name TEXT NOT NULL UNIQUE,
  created_by   INTEGER NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE RESTRICT
);

-- =========================================================
-- 3) pdfs
-- (authors kept as free-text for provenance; per-author rows live in pdf_authors)
-- =========================================================
CREATE TABLE IF NOT EXISTS pdfs (
  pdf_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  title                  TEXT,
  authors                TEXT,   -- original free-text list (for provenance)
  affiliation            TEXT,
  doi                    TEXT UNIQUE,
  instruments_json       TEXT,   -- optional cache (JSON array of instrument_id or strings)
  cosine_similarity      REAL,
  num_pages              INTEGER,
  upload_date            TEXT,   -- ISO 8601 string
  publish_date           TEXT,   -- ISO 8601 string
  uploaded_by            INTEGER,   -- -> users.user_id
  project_id             INTEGER,   -- -> projects.project_id
  cmca_result            TEXT CHECK (cmca_result IN ('Yes','No')), -- belongs to CMCA?
  results_json           TEXT,   -- JSON blob for labeling/evidence/etc
  cmca_author_ids_json   TEXT,   -- optional legacy cache; name-matching uses pdf_authors
  FOREIGN KEY (uploaded_by) REFERENCES users(user_id)       ON DELETE SET NULL,
  FOREIGN KEY (project_id) REFERENCES projects(project_id)  ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_pdfs_project     ON pdfs(project_id);
CREATE INDEX IF NOT EXISTS idx_pdfs_uploaded_by ON pdfs(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_pdfs_doi         ON pdfs(doi);

-- =========================================================
-- 4) instruments
-- =========================================================
CREATE TABLE IF NOT EXISTS instruments (
  instrument_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  instrument_name TEXT NOT NULL UNIQUE
);

-- =========================================================
-- 5) cmca_authors  (author master list)
-- =========================================================
CREATE TABLE IF NOT EXISTS cmca_authors (
  cmca_author_id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name      TEXT NOT NULL,   -- e.g., "John Smith"
  email          TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_cmca_authors_name ON cmca_authors(full_name COLLATE NOCASE);

-- =========================================================
-- 6) gold_standards
-- =========================================================
CREATE TABLE IF NOT EXISTS gold_standards (
  gold_id         INTEGER PRIMARY KEY AUTOINCREMENT,
  instrument_name TEXT NOT NULL,
  vendor          TEXT,
  model           TEXT,
  instrument_code TEXT,
  platform        TEXT
);

-- =========================================================
-- 7) embeddings
-- =========================================================
CREATE TABLE IF NOT EXISTS embeddings (
  embedding_id INTEGER PRIMARY KEY AUTOINCREMENT,
  pdf_id       INTEGER NOT NULL,              -- -> pdfs.pdf_id
  chunk_label  TEXT,
  vector_json  TEXT NOT NULL,                 -- store vector as JSON array for portability
  model        TEXT,
  dim          INTEGER,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (pdf_id) REFERENCES pdfs(pdf_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_pdf ON embeddings(pdf_id);

-- =========================================================
-- Helper table for NAME-BASED matching (per-paper author rows)
-- =========================================================
CREATE TABLE IF NOT EXISTS pdf_authors (
  pdf_id       INTEGER NOT NULL,              -- -> pdfs.pdf_id
  author_name  TEXT    NOT NULL,              -- e.g., "John Smith"
  author_order INTEGER,                       -- optional: 1,2,3...
  PRIMARY KEY (pdf_id, author_name),
  FOREIGN KEY (pdf_id) REFERENCES pdfs(pdf_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pdf_authors_name ON pdf_authors(author_name COLLATE NOCASE);

-- =========================================================
-- Views for NAME-BASED CMCA author matching
-- Normalization removes punctuation/dashes and lowercases both sides.
-- =========================================================

-- Matches between pdf_authors and cmca_authors by normalized name
CREATE VIEW IF NOT EXISTS v_pdf_cmca_matches AS
SELECT
  p.pdf_id,
  p.title,
  pa.author_name       AS pdf_author_name,
  ca.cmca_author_id,
  ca.full_name         AS cmca_full_name,
  ca.email
FROM pdf_authors pa
JOIN pdfs p  ON p.pdf_id = pa.pdf_id
JOIN cmca_authors ca
  ON lower(
       replace(replace(replace(replace(replace(pa.author_name,'.',''),'-',''),'–',''),',',''),'  ',' ')
     ) =
     lower(
       replace(replace(replace(replace(replace(ca.full_name,'.',''),'-',''),'–',''),',',''),'  ',' ')
     );

-- Per-PDF flag if any CMCA author matched by name
CREATE VIEW IF NOT EXISTS v_pdf_has_cmca_author AS
SELECT
  p.pdf_id,
  p.title,
  CASE
    WHEN EXISTS (SELECT 1 FROM v_pdf_cmca_matches m WHERE m.pdf_id = p.pdf_id)
    THEN 'Yes' ELSE 'No'
  END AS has_cmca_author
FROM pdfs p;
