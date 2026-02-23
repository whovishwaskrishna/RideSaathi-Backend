from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base

class DriverDocument(Base):
    __tablename__ = "driver_documents"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"))

    document_type = Column(String, nullable=False)
    document_url = Column(String, nullable=False)
    