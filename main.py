import re
import csv
import uuid
import json
import numpy as np
from io import StringIO
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, Query, Depends, HTTPException, Cookie, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
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

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="Staff")

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "Staff"

class UserUpdate(BaseModel):
    email: Optional[str]
    password: Optional[str]
    role: Optional[str]

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    
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
# Auth Utils
# ------------------------------
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def require_role(required_roles: List[str]):
    def role_checker(claims=Depends(get_current_user)):
        if not claims:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if claims.get("role") not in required_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return claims
    return role_checker

def require_role_frontend(required_roles: List[str]):
    def role_checker(claims=Depends(get_current_user)):
        if not claims or claims.get("role") not in required_roles:
            return RedirectResponse(url="/login", status_code=303)
        return claims
    return role_checker

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

def require_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=303,
            detail="Redirecting to login",
            headers={"Location": "/login"}
        )

# ------------------------------
# Routes (Frontend pages)
# ------------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse(TEMPLATES_DIR / "index.html")

@app.get("/capstone", response_class=HTMLResponse)
def capstone_overview():
    return FileResponse(TEMPLATES_DIR / "capstone-overview.html")
    
@app.get("/login", response_class=HTMLResponse)
def login(claims=Depends(get_current_user)):
    if claims:
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(TEMPLATES_DIR / "login.html")

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token", path="/")
    return response

@app.get("/manage-capstones", response_class=HTMLResponse)
def manage_capstones(claims=Depends(require_role_frontend(["Admin", "Staff"]))):
    if isinstance(claims, RedirectResponse):
        return claims
    response = FileResponse(TEMPLATES_DIR / "manage-capstones.html")
    response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/manage-users", response_class=HTMLResponse)
def manage_users(claims=Depends(require_role_frontend(["Admin"]))):
    if isinstance(claims, RedirectResponse):
        return claims
    response = FileResponse(TEMPLATES_DIR / "manage-users.html")
    response.headers["Cache-Control"] = "no-store"
    return response


# ------------------------------
# CRUD API
# ------------------------------
@app.post("/api/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )

    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # set True in production with HTTPS
        samesite="Lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


@app.post("/api/logout")
def logout(response: Response):
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("access_token")
    return response


@app.post("/api/users", response_model=UserResponse)
def create_user(
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("Staff"),
    db: Session = Depends(get_db),
    claims = Depends(require_role(["Admin"]))
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed_pw = get_password_hash(password)
    db_user = User(email=email, password=hashed_pw, role=role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/api/users")
def list_users(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    search: Optional[str] = Query(default=None),
    claims = Depends(require_role(["Admin"]))
):
    query = db.query(User)
    if search:
        keyword = f"%{search}%"
        query = query.filter(User.email.ilike(keyword) | User.role.ilike(keyword))
    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()
    results = [{"id": u.id, "email": u.email, "role": u.role} for u in users]
    return {"total": total, "page": page, "per_page": per_page, "results": results}


@app.get("/api/users/current")
def read_current_user(claims=Depends(get_current_user)):
    if not claims:
        return {"email": None}
    return {"email": claims["sub"], "role": claims["role"]}


@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), claims = Depends(require_role(["Admin"]))):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.put("/api/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    claims = Depends(require_role(["Admin"]))
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if email:
        if email != db_user.email and db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        db_user.email = email

    if password:
        db_user.password = get_password_hash(password)

    if role:
        db_user.role = role

    db.commit()
    db.refresh(db_user)
    return db_user


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), claims = Depends(require_role(["Admin"]))):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": f"User {db_user.email} deleted successfully"}


@app.post("/api/capstones", response_model=CapstoneResponse)
async def create_capstone(
    title: str = Form(...),
    abstract: str = Form(None),
    authors: str = Form(...),
    year: int = Form(...),
    external_link: str = Form(None),
    pdf: UploadFile | None = None,
    db: Session = Depends(get_db),
    claims=Depends(require_role(["Admin", "Staff"]))
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


@app.post("/api/capstones/import-csv")
async def import_capstones_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    claims=Depends(require_role(["Admin", "Staff"]))
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


@app.get("/api/capstones/{capstone_id}", response_model=CapstoneResponse)
def read_capstone(capstone_id: int, db: Session = Depends(get_db)):
    capstone = db.query(Capstone).filter(Capstone.id == capstone_id).first()
    if not capstone:
        raise HTTPException(status_code=404, detail="Capstone not found")
    return capstone


@app.put("/api/capstones/{capstone_id}", response_model=CapstoneResponse)
async def update_capstone(
    capstone_id: int,
    title: str = Form(...),
    abstract: str = Form(None),
    authors: str = Form(...),
    year: int = Form(...),
    external_link: str | None = Form(None),
    pdf: UploadFile = File(None),
    db: Session = Depends(get_db),
    claims=Depends(require_role(["Admin", "Staff"]))
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


@app.delete("/api/capstones/{capstone_id}")
def delete_capstone(capstone_id: int, db: Session = Depends(get_db), claims=Depends(require_role(["Admin", "Staff"]))):
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


# ------------------------------
# Seed default users (Admin & Staff)
# ------------------------------
def seed_default_users():
    db = SessionLocal()
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        def get_password_hash(password: str):
            return pwd_context.hash(password)

        if not db.query(User).filter(User.email == "admin@cit.edu").first():
            admin_user = User(
                email="admin@cit.edu",
                password=get_password_hash("admin123"),
                role="Admin",
            )
            db.add(admin_user)

        if not db.query(User).filter(User.email == "staff@cit.edu").first():
            staff_user = User(
                email="staff@cit.edu",
                password=get_password_hash("staff123"),
                role="Staff",
            )
            db.add(staff_user)

        db.commit()
    finally:
        db.close()

seed_default_users()
