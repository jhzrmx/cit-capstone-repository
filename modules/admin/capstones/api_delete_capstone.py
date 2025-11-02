from fastapi import Depends, FastAPI, HTTPException

from db import get_db
from helpers.pdf import PdfHelper
from helpers.session import require_role
from models.capstone import Capstone
from sqlalchemy.orm import Session


def register_api_delete_capstone_route(app: FastAPI):
    
    @app.delete("/api/capstones/{capstone_id}")
    def delete_capstone(capstone_id: int, db: Session = Depends(get_db), claims=Depends(require_role(["Admin", "Staff"]))):
        capstone = db.query(Capstone).filter(Capstone.id == capstone_id).first()
        if not capstone:
            raise HTTPException(status_code=404, detail="Capstone not found")

        if capstone.pdf_file:
            PdfHelper.delete_pdf(capstone.pdf_file)

        db.delete(capstone)
        db.commit()
        return {"message": "Capstone deleted successfully"}
