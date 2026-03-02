from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    vehicle_type = Column(String, nullable=False)
    vehicle_number = Column(String, nullable=False)

    is_approved = Column(Boolean, default=False)

    user = relationship("User")
    