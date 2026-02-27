from sqlalchemy import Column, Integer, ForeignKey, Boolean
from app.db.base import Base

class RouteStop(Base):
    __tablename__ = "route_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"))
    city_id = Column(Integer, ForeignKey("cities.id"))
    stop_order = Column(Integer, nullable=False)
    is_reached = Column(Boolean, default=False)