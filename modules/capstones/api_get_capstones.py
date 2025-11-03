from fastapi import FastAPI
from fastapi.params import Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from db import get_db
from dtos import ProjectOut
from sqlalchemy import text

def register_api_get_capstones_route(app: FastAPI):
    @app.get("/api/capstones", response_model=List[ProjectOut])
    def list_projects(q: Optional[str] = Query(None), limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
        if q:
            rows = db.execute(
                text("""SELECT p.id, p.title, p.year, p.abstract, p.course, p.host, p.doc_type
                        FROM projects p JOIN projects_fts f ON f.rowid = p.id
                        WHERE f MATCH :q ORDER BY bm25(f) LIMIT :lim OFFSET :off"""),
                {"q": q, "lim": limit, "off": offset}
            ).fetchall()
        else:
            rows = db.execute(
                text("SELECT id, title, year, abstract, course, host, doc_type FROM projects ORDER BY id DESC LIMIT :lim OFFSET :off"),
                {"lim": limit, "off": offset}
            ).fetchall()

        out = []
        for pid, title, year, abstract, course, host, doc_type in rows:
            authors = [r[0] for r in db.execute(text("SELECT full_name FROM authors WHERE project_id=:pid"), {"pid": pid}).fetchall()]
            keywords = [r[0] for r in db.execute(text("SELECT keyword FROM project_keywords WHERE project_id=:pid"), {"pid": pid}).fetchall()]
            out.append(ProjectOut(id=pid, title=title, year=year, abstract=abstract, authors=authors,
                                course=course, host=host, doc_type=doc_type, keywords=keywords))
        return out