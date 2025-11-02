import json
from sqlalchemy import Column, Integer, String, Text

from helpers.embedding import encode_text
from models.base import Base

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
    
    def set_embedding(self, text: str):
        embedding = encode_text(text).tolist()
        self.embedding = json.dumps(embedding)