
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Response
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from config import AuthConfig
from db import get_db
from helpers.session import authenticate_user, create_access_token

def register_api_login_route(app: FastAPI):
    @app.post("/api/login")
    def login(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
    ):
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        access_token_expires = timedelta(minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "role": user.role},
            expires_delta=access_token_expires
        )

        response = JSONResponse(content={
            "message": "Login successful",
            "status": "ok",
            "data": {
                "access_token": access_token,
                "access_token_expires": access_token_expires.total_seconds(),
                "user": {
                    "email": user.email,
                    "role": user.role
                }
            }
        })
        return response

