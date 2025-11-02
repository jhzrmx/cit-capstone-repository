from fastapi import FastAPI, Query
from fastapi.params import Depends
from sqlalchemy import String

from db import get_db
from helpers.session import require_role
from models.capstone import Capstone
from sqlalchemy.orm import Session


def register_api_get_all_capstones_route(app: FastAPI):
    
    @app.get("/api/capstones")
    def list_capstones(
        db: Session = Depends(get_db),
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=10, ge=1, le=50),
        search: str = Query(default=None),
        claims=Depends(require_role(["Admin", "Staff"]))
    ):
        query = db.query(Capstone).order_by(Capstone.year.desc())

        if search:
            keyword = f"%{search}%"
            query = query.filter(
                (Capstone.title.ilike(keyword))
                | (Capstone.abstract.ilike(keyword))
                | (Capstone.authors.ilike(keyword))
                | (Capstone.year.cast(String).ilike(keyword))
            )

        total = query.count()
        capstones = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "results": capstones,
        }

