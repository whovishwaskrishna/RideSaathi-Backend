from sqlalchemy import Column, Integer, ForeignKey, Float, String, DateTime, Enum
from app.db.base import Base

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    start_city_id = Column(Integer, ForeignKey("cities.id"))
    end_city_id = Column(Integer, ForeignKey("cities.id"))
    departure_time = Column(DateTime, nullable=False)
    estimated_duration_minutes = Column(Integer, nullable=True)
    available_seats = Column(Integer, nullable=False)
    price_per_seat = Column(Float, nullable=False)
    status = Column(String, default="SCHEDULED")
    