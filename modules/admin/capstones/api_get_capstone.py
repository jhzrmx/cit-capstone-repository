from fastapi import Depends, FastAPI, HTTPException
from db import get_db
from dtos import CapstoneResponse
from models import Capstone
from sqlalchemy.orm import Session


def register_api_get_capstone_route(app: FastAPI):
    
    @app.get("/api/capstones/{capstone_id}", response_model=CapstoneResponse)
    def read_capstone(capstone_id: int, db: Session = Depends(get_db)):
        capstone = db.query(Capstone).filter(Capstone.id == capstone_id).first()
        if not capstone:
            raise HTTPException(status_code=404, detail="Capstone not found")
        return capstone
