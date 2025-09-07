import re
import csv
import uuid
import json
import numpy as np
from io import StringIO
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sentence_transformers import SentenceTransformer

# ------------------------------
# Database setup
# ------------------------------
DATABASE_URL = "sqlite:///./capstones.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Capstone(Base):
    __tablename__ = "capstones"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    abstract = Column(Text, nullable=True)
    authors = Column(String)
    year = Column(Integer)
    external_link = Column(String, nullable=True)
    pdf_file = Column(String, nullable=True)
    embedding = Column(Text, nullable=True)


Base.metadata.create_all(bind=engine)

# ------------------------------
# DIR setup
# ------------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"

# ------------------------------
# FastAPI app setup
# ------------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ------------------------------
# AI Model for smart search
# ------------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

# ------------------------------
# Pydantic schemas
# ------------------------------
class CapstoneCreate(BaseModel):
    title: str
    abstract: Optional[str] = None
    authors: str
    year: int
    external_link: Optional[str] = None

class CapstoneResponse(BaseModel):
    id: int
    title: str
    abstract: Optional[str]
    authors: str
    year: int
    external_link: Optional[str]
    pdf_file: Optional[str]

    class Config:
        from_attributes = True


class SearchQuery(BaseModel):
    text: str


# ------------------------------
# Dependency
# ------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def encode_text(text: str):
    return model.encode(text, convert_to_tensor=False).astype(np.float32)

def save_embedding(capstone: Capstone, text: str):
    embedding = encode_text(text).tolist()
    capstone.embedding = json.dumps(embedding)

def load_embedding(json_str: str):
    return np.array(json.loads(json_str), dtype=np.float32)

def generate_pdf_filename(title: str, original_filename: str) -> str:
    ext = Path(original_filename).suffix or ".pdf"
    safe_title = re.sub(r'[^a-zA-Z0-9_-]', "_", title.strip().lower())
    safe_title = safe_title[:50].rstrip("_")
    if not safe_title:
        safe_title = "capstone"
    rand_str = uuid.uuid4().hex[:8]
    return f"{safe_title}_{rand_str}{ext}"

def save_pdf(file: UploadFile, title: str) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = generate_pdf_filename(title, file.filename)
    path = UPLOAD_DIR / filename
    with open(path, "wb") as f:
        f.write(file.file.read())
    return filename

def delete_pdf(filename: str):
    if filename:
        path = UPLOAD_DIR / filename
        if path.exists():
            path.unlink()


# ------------------------------
# Routes (Frontend pages)
# ------------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse(TEMPLATES_DIR / "index.html")

@app.get("/manage", response_class=HTMLResponse)
def manage_page():
    return FileResponse(TEMPLATES_DIR / "manage.html")

# ------------------------------
# CRUD API
# ------------------------------
@app.post("/capstones", response_model=CapstoneResponse)
async def create_capstone(
    title: str = Form(...),
    abstract: str = Form(None),
    authors: str = Form(...),
    year: int = Form(...),
    external_link: str = Form(None),
    pdf: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    pdf_filename = None
    if pdf and pdf.filename:
        pdf_filename = save_pdf(pdf, title)

    capstone = Capstone(
        title=title,
        abstract=abstract,
        authors=authors,
        year=year,
        external_link=external_link,
        pdf_file=pdf_filename,
    )
    text_for_embedding = f"{title} {abstract or ''}"
    save_embedding(capstone, text_for_embedding)
    db.add(capstone)
    db.commit()
    db.refresh(capstone)
    return capstone


@app.post("/capstones/import-csv")
async def import_capstones_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    contents = (await file.read()).decode("utf-8")
    reader = csv.DictReader(StringIO(contents))

    inserted = []
    skipped = []

    for row in reader:
        title = row.get("title")
        if not title or not row.get("authors") or not row.get("year"):
            skipped.append({"title": title, "reason": "missing required fields"})
            continue

        exists = db.query(Capstone).filter(Capstone.title == title).first()
        if exists:
            skipped.append({"title": title, "reason": "duplicate"})
            continue

        capstone = Capstone(
            title=title,
            abstract=row.get("abstract", ""),
            authors=row["authors"],
            year=int(row["year"]),
            external_link=row.get("external_link") or None,
            pdf_file=None
        )
        
        text_for_embedding = f"{capstone.title} {capstone.abstract}"
        save_embedding(capstone, text_for_embedding)

        db.add(capstone)
        inserted.append(title)

    db.commit()

    return {
        "message": f"Imported {len(inserted)} capstones, skipped {len(skipped)}",
        "inserted": inserted,
        "skipped": skipped,
    }


@app.get("/capstones")
def list_capstones(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    search: str = Query(default=None),
):
    query = db.query(Capstone)

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


@app.get("/capstones/{capstone_id}", response_model=CapstoneResponse)
def read_capstone(capstone_id: int, db: Session = Depends(get_db)):
    capstone = db.query(Capstone).filter(Capstone.id == capstone_id).first()
    if not capstone:
        raise HTTPException(status_code=404, detail="Capstone not found")
    return capstone


@app.put("/capstones/{capstone_id}", response_model=CapstoneResponse)
async def update_capstone(
    capstone_id: int,
    title: str = Form(...),
    abstract: str = Form(None),
    authors: str = Form(...),
    year: int = Form(...),
    external_link: str | None = Form(None),
    pdf: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    capstone = db.query(Capstone).filter(Capstone.id == capstone_id).first()
    if not capstone:
        raise HTTPException(status_code=404, detail="Capstone not found")

    capstone.title = title
    capstone.abstract = abstract
    capstone.authors = authors
    capstone.year = year
    capstone.external_link = external_link

    if pdf and pdf.filename.strip():
        if capstone.pdf_file:
            delete_pdf(capstone.pdf_file)
        capstone.pdf_file = save_pdf(pdf, title)
    
    text_for_embedding = f"{title} {abstract or ''}"
    save_embedding(capstone, text_for_embedding)
    db.commit()
    db.refresh(capstone)
    return capstone


@app.delete("/capstones/{capstone_id}")
def delete_capstone(capstone_id: int, db: Session = Depends(get_db)):
    capstone = db.query(Capstone).filter(Capstone.id == capstone_id).first()
    if not capstone:
        raise HTTPException(status_code=404, detail="Capstone not found")

    if capstone.pdf_file:
        delete_pdf(capstone.pdf_file)

    db.delete(capstone)
    db.commit()
    return {"message": "Capstone deleted successfully"}


# ------------------------------
# AI Search Endpoint
# ------------------------------
@app.post("/search")
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

