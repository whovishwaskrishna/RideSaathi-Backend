from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"))
    customer_id = Column(Integer, ForeignKey("users.id"))
    from_city_id = Column(Integer, ForeignKey("cities.id"))
    to_city_id = Column(Integer, ForeignKey("cities.id"))
    seats_booked = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String, default="CONFIRMED")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    