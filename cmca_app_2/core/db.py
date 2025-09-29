from __future__ import annotations
from typing import List, Dict, Any
from tinydb import TinyDB, Query
from pathlib import Path
import json, uuid, shutil, datetime as dt

DB_DIR = Path(".cmca_store")
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "cmca.json"
UPLOAD_DIR = DB_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
SAMPLE_PATH = Path(__file__).resolve().parent.parent / "sample_data.json"

# 初始化：导入示例数据（含 projects & pdfs）
if not DB_PATH.exists():
    seed = {"pdfs": [], "projects": []}
    if SAMPLE_PATH.exists():
        with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
            seed = json.load(f)
    db = TinyDB(DB_PATH)
    db.table("projects").insert_multiple(
        [{"name": p["name"], "year": p.get("year") } for p in seed.get("projects", [])]
    )
    db.table("pdfs").insert_multiple(seed.get("pdfs", []))

db = TinyDB(DB_PATH)
PDFS = db.table("pdfs")
PROJECTS = db.table("projects")

# ---------- Project APIs ----------

def list_projects() -> List[Dict[str, Any]]:
    items = PROJECTS.all()
    # 去重并按名称排序
    items.sort(key=lambda x: (x.get("year") or "", x.get("name") or ""))
    return items


def add_project(name: str, year: str | None = None) -> Dict[str, Any]:
    name = name.strip()
    if not name:
        raise ValueError("Project name is required")
    q = Query()
    exists = PROJECTS.search((q.name == name) & (q.year == (year or None)))
    if exists:
        return exists[0]
    rec = {"name": name, "year": year}
    PROJECTS.insert(rec)
    return rec

# ---------- PDF APIs ----------

def list_pdfs(filters: Dict[str, Any] | None = None, sort_by: str | None = None) -> List[Dict[str, Any]]:
    items = PDFS.all()
    # 过滤
    if filters:
        def ok(it):
            for k, v in filters.items():
                if v in (None, "", "All"):
                    continue
                if k == "instruments":
                    # instruments 为多选，若 filters 给出值则需要交集
                    if not set(v).issubset(set(it.get("instruments", []))):
                        return False
                else:
                    if str(it.get(k, "")).lower() != str(v).lower():
                        return False
            return True
        items = [it for it in items if ok(it)]
    # 排序
    if sort_by == "Date (Oldest First)":
        items.sort(key=lambda x: x.get("upload_date", ""))
    elif sort_by == "Title A→Z":
        items.sort(key=lambda x: x.get("title", "").lower())
    else:  # Date (Newest First)
        items.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
    return items


def get_pdf(pdf_id: str) -> Dict[str, Any] | None:
    q = Query()
    res = PDFS.search(q.id == pdf_id)
    return res[0] if res else None


def update_pdf(pdf_id: str, patch: Dict[str, Any]) -> bool:
    q = Query()
    return bool(PDFS.update(patch, q.id == pdf_id))


def delete_pdf(pdf_id: str) -> bool:
    q = Query()
    rec = get_pdf(pdf_id)
    if rec and rec.get("file_path"):
        try:
            Path(rec["file_path"]).unlink(missing_ok=True)
        except Exception:
            pass
    return bool(PDFS.remove(q.id == pdf_id))


def stats():
    items = PDFS.all()
    total = len(items)
    yes = sum(1 for x in items if str(x.get("cmca_use", "")).lower() == "yes")
    no = total - yes
    return {"total": total, "yes": yes, "no": no}


def add_pdf(file_bytes: bytes | None, filename: str | None, meta: Dict[str, Any]) -> Dict[str, Any]:
    pid = meta.get("id") or f"pdf_{uuid.uuid4().hex[:8]}"
    saved_path = None
    if file_bytes and filename:
        ext = Path(filename).suffix.lower() or ".pdf"
        saved_path = str(UPLOAD_DIR / f"{pid}{ext}")
        with open(saved_path, "wb") as f:
            f.write(file_bytes)
    rec = {
        "id": pid,
        "title": meta.get("title") or (filename or "Untitled"),
        "authors": meta.get("authors", []),
        "affiliations": meta.get("affiliations", []),
        "doi": meta.get("doi", ""),
        "instruments": meta.get("instruments", []),
        "project": meta.get("project", ""),
        "uploaded_by": meta.get("uploaded_by", "Unknown"),
        "size": meta.get("size", "-"),
        "upload_date": meta.get("upload_date") or dt.date.today().isoformat(),
        "year": meta.get("year"),
        "cosine": float(meta.get("cosine", 0.0)),
        "cmca_use": meta.get("cmca_use", "No"),
        "file_path": saved_path,
    }
    PDFS.insert(rec)
    return rec