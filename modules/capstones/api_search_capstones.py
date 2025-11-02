from fastapi import FastAPI
from fastapi.params import Depends, Query
import numpy as np

from db import get_db
from helpers.embedding import encode_text, load_embedding
from dtos import SearchQuery
from models.capstone import Capstone
from sqlalchemy.orm import Session


def register_api_search_capstones_route(app: FastAPI):
    
    # ------------------------------
    # AI Search Endpoint
    # ------------------------------
    @app.post("/api/search")
    def search_capstones(
        query: SearchQuery,
        db: Session = Depends(get_db),
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=10, ge=1, le=50),
    ):
        text = query.text.strip()
        if not text:
            return {"results": [], "total": 0, "page": page, "per_page": per_page}

        capstones = db.query(Capstone).all()
        if not capstones:
            return {"results": [], "total": 0, "page": page, "per_page": per_page}

        query_emb = encode_text(text)

        results = []
        for cap in capstones:
            if not cap.embedding:
                continue
            emb = load_embedding(cap.embedding)
            score = float(np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb)))
            if score >= 0.15:  # threshold
                results.append({
                    "id": cap.id,
                    "title": cap.title,
                    "abstract": cap.abstract,
                    "authors": cap.authors,
                    "year": cap.year,
                    "external_link": cap.external_link,
                    "pdf_file": cap.pdf_file,
                    "similarity": score,
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)

        total = len(results)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = results[start:end]

        return {"results": paginated, "total": total, "page": page, "per_page": per_page}

