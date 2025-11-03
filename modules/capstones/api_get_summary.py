from fastapi import FastAPI, HTTPException
from typing import Optional

from helpers.rag import get_cached_summary
from dtos import AISummary


def register_api_get_summary_route(app: FastAPI):
    
    @app.get("/api/capstones/summary/{query_id}", response_model=Optional[AISummary])
    async def get_summary(query_id: str):
        if not query_id:
            raise HTTPException(
                status_code=400,
                detail="query_id is required"
            )
        summary = get_cached_summary(query_id)
        return summary
