from http.client import HTTPException
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.params import Depends
from db import get_db
from helpers.pdf import PdfHelper
from helpers.session import require_role
from dtos import CapstoneResponse
from models.capstone import Capstone
from sqlalchemy.orm import Session


def register_api_update_capstone_route(app: FastAPI):
    
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
                PdfHelper.delete_pdf(capstone.pdf_file)
            capstone.pdf_file = PdfHelper.save_pdf(pdf, title)
        
        text_for_embedding = f"{title} {abstract or ''}"
        capstone.set_embedding(text_for_embedding)
        db.commit()
        db.refresh(capstone)
        return capstone

