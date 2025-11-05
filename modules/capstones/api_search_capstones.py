from typing import Dict
from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db
from rag.retrieval import hybrid_retrieve


def register_api_search_capstones_routes(app: FastAPI):
    @app.get("/api/search")
    def search(q: str = Query(...), k: int = 30, db: Session = Depends(get_db)):
        hits = hybrid_retrieve(db, q, k=k)
        grouped: Dict[int, Dict] = {}
        for h in hits:
            grouped.setdefault(h["project_id"], {"title": h["title"], "similarity": h["sim"], "year": h["year"], "snippets": []})
            grouped[h["project_id"]]["snippets"].append(h["content"])
            authors = [r[0] for r in db.execute(text("SELECT full_name FROM authors WHERE project_id=:pid"), {"pid": h["project_id"]}).fetchall()]
            keywords = [r[0] for r in db.execute(text("SELECT keyword FROM project_keywords WHERE project_id=:pid"), {"pid": h["project_id"]}).fetchall()]
            grouped[h["project_id"]]["authors"] = authors
            grouped[h["project_id"]]["keywords"] = keywords
        results = [{"project_id": pid, **meta} for pid, meta in grouped.items()]
        return {"query": q, "results": results}
