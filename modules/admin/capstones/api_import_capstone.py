import csv
from io import StringIO
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile

from db import get_db
from helpers.session import require_role
from models import Capstone
from sqlalchemy.orm import Session


def register_api_import_capstone_route(app: FastAPI):
    
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
            capstone.set_embedding(text_for_embedding)

            db.add(capstone)
            inserted.append(title)

        db.commit()

        return {
            "message": f"Imported {len(inserted)} capstones, skipped {len(skipped)}",
            "inserted": inserted,
            "skipped": skipped,
        }

