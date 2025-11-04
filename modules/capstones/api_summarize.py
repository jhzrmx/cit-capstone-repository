from fastapi import Depends, FastAPI

from config import OpenAiConfig
from db import get_db
from dtos import SummarizeIn
from rag.retrieval import hybrid_retrieve
from rag.summarizer import summarize_with_ollama, summarize_with_openai
from sqlalchemy.orm import Session

def register_api_summarize_route(app: FastAPI):
    @app.post("/api/summarize")
    def summarize(body: SummarizeIn, db: Session = Depends(get_db)):
        hits = hybrid_retrieve(db, body.query, k=body.k)
        # Limit context mass for small models
        top = hits[:min(body.k, 10)]
        if OpenAiConfig.OPENAI_KEY:
            print("############# USING OPENAI ##############")
            summary = summarize_with_openai(body.query, top)
        else:
            print("############# USING OLLAMA ##############")
            summary = summarize_with_ollama(body.query, top)
        # build cited list
        sources = []
        for idx, h in enumerate(top, start=1):
            sources.append({
                "index": idx,
                "project_id": h["project_id"],
                "title": h["title"],
                "year": h["year"]
            })
        return {"query": body.query, "summary": summary, "used_sources": sources}