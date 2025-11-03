from fastapi import FastAPI, BackgroundTasks
from fastapi.params import Depends, Query
import numpy as np

from db import get_db
from helpers.embedding import encode_text, load_embedding
from helpers.rag import get_cache_key, generate_and_cache_summary
from dtos import SearchQuery, AbstractWithMetadata
from models.capstone import Capstone
from sqlalchemy.orm import Session
from config import RAGConfig


def register_api_search_capstones_route(app: FastAPI):
    
    # ------------------------------
    # AI Search Endpoint with RAG Summary
    # ------------------------------
    @app.post("/api/search")
    async def search_capstones(
        query: SearchQuery,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=10, ge=1, le=50),
    ):
        text = query.text.strip()
        if not text:
            return {
                "results": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "query_id": None
            }

        capstones = db.query(Capstone).all()
        if not capstones:
            return {
                "results": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "query_id": None
            }

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

        query_id = None
        if RAGConfig.RAG_ENABLE_SUMMARY == "true" and results:
            top_k = int(RAGConfig.RAG_TOP_K)
            top_results_for_summary = results[:top_k]
            
            capstone_ids = [r["id"] for r in top_results_for_summary]
            cache_key = get_cache_key(capstone_ids, text)
            query_id = cache_key
            
            abstracts = [
                AbstractWithMetadata(
                    capstone_id=r["id"],
                    title=r["title"],
                    authors=r["authors"],
                    year=r["year"],
                    abstract=r["abstract"] or ""
                )
                for r in top_results_for_summary
                if r["abstract"]
            ]
            
            if abstracts:
                background_tasks.add_task(
                    generate_and_cache_summary,
                    abstracts,
                    text,
                    cache_key
                )

        # Paginate results
        total = len(results)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = results[start:end]

        return {
            "results": paginated,
            "total": total,
            "page": page,
            "per_page": per_page,
            "query_id": query_id
        }

