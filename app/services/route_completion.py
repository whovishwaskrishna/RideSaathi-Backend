from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.route import Route
from app.models.booking import Booking

def auto_complete_route(db: Session, route: Route):
    if route.status != "ACTIVE":
        return
    
    completion_time = route.departure_time + timedelta(
        minutes=route.estimated_duration_minutes
    )

    if datetime.utcnow() >= completion_time:
        route.status = "COMPLETED"

        db.query(Booking).filter(
            Booking.route_id == route.id,
            Booking.status == "CONFIRMED"
        ).update({"status":"COMPLETED"})

        db.commit()