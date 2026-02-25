from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from app.db.base import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    customer_id = Column(Integer, ForeignKey("users.id"))

    rating = Column(Integer, nullable=False)
    review_text = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    