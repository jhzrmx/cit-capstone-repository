from typing import Optional
from pydantic import BaseModel

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
