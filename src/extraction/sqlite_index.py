# src/extraction/sqlite_index.py
from __future__ import annotations
from pathlib import Path
import sqlite3
import json
from typing import Iterable, Dict

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS sentences(
  id TEXT PRIMARY KEY,
  page INTEGER,
  text TEXT NOT NULL,
  bbox TEXT NOT NULL,
  g0 INTEGER NOT NULL,
  g1 INTEGER NOT NULL,
  p0 INTEGER NOT NULL,
  p1 INTEGER NOT NULL,
  hash16 TEXT UNIQUE
);
CREATE VIRTUAL TABLE IF NOT EXISTS sentences_fts USING fts5(
  text, content='sentences', content_rowid='rowid'
);
"""

_INSERT = "INSERT OR REPLACE INTO sentences(id,page,text,bbox,g0,g1,p0,p1,hash16) VALUES (?,?,?,?,?,?,?,?,?)"
_INSERT_FTS = "INSERT INTO sentences_fts(rowid,text) VALUES (?,?)"

class SentIndex:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.con = sqlite3.connect(str(self.db_path))
        self.con.execute("PRAGMA foreign_keys=ON;")
        self.con.executescript(_SCHEMA)
        self._tx = False

    def begin(self):
        if not self._tx:
            self.con.execute("BEGIN")
            self._tx = True

    def commit(self):
        if self._tx:
            self.con.commit()
            self._tx = False

    def close(self):
        self.commit()
        self.con.close()

    def add_batch(self, batch: Iterable[Dict]):
        cur = self.con.cursor()
        for r in batch:
            cur.execute(_INSERT, (
                r["id"], r["page"], r["text"], json.dumps(r["bbox"]),
                r["global_char_start"], r["global_char_end"],
                r["page_char_start"], r["page_char_end"],
                r["hash16"]
            ))
            cur.execute(_INSERT_FTS, (cur.lastrowid, r["text"]))
