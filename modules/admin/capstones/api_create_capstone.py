
from fastapi import FastAPI, UploadFile
from fastapi import Form
from fastapi.params import Depends

from db import get_db
from helpers.pdf import PdfHelper
from helpers.session import require_role
from dtos import CapstoneResponse
from sqlalchemy.orm import Session

from models.capstone import Capstone


def register_api_create_capstone_route(app: FastAPI):
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
            pdf_filename = PdfHelper.save_pdf(pdf, title)

        capstone = Capstone(
            title=title,
            abstract=abstract,
            authors=authors,
            year=year,
            external_link=external_link,
            pdf_file=pdf_filename,
        )
        text_for_embedding = f"{title} {abstract or ''}"
        capstone.set_embedding(text_for_embedding)
        db.add(capstone)
        db.commit()
        db.refresh(capstone)
        return capstone
