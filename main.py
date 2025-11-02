from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from jose import JWTError, jwt
from sqlalchemy import String
from sqlalchemy.orm import Session
from helpers.embedding import encode_text, load_embedding
from helpers.password import hash_password, verify_password
from helpers.pdf import PdfHelper
from helpers.session import get_current_user, require_role, require_role_frontend
from models import Capstone, User
from db import get_db
from config import PathConfig, AuthConfig
from modules.admin.capstones import configure_admin_capstone_module
from modules.admin.users import configure_admin_users_module
from modules.auth import configure_auth_module
from modules.capstones import configure_capstone_module
from modules.home import configure_home_module
from repositories.user import UserRepository

# ------------------------------
# FastAPI app setup
# ------------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=str(PathConfig.UPLOAD_DIR)), name="uploads")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Routes (Frontend pages)
# ------------------------------

configure_home_module(app)
configure_capstone_module(app)
configure_auth_module(app)
configure_admin_users_module(app)
configure_admin_capstone_module(app)

