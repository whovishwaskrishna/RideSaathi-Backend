from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey("routes.id"))
    customer_id = Column(Integer, ForeignKey("users.id"))
    from_city_id = Column(Integer, ForeignKey("cities.id"))
    to_city_id = Column(Integer, ForeignKey("cities.id"))
    seats_booked = Column(Integer)
    status = Column(String, default="CONFIRMED")