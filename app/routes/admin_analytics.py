from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.models.user import User
from app.models.route import Route
from app.models.booking import Booking
from app.models.driver import Driver
from app.models.reviews import Review
from app.core.dependencies import require_role

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])

@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    total_users = db.query(func.count(User.id)).scalar()
    total_drivers = db.query(func.count(Driver.id)).scalar()
    total_routes = db.query(func.count(Route.id)).scalar()

    completed_rides = db.query(func.count(Route.id)).filter(
        Route.status == "COMPLETED"
    ).scalar()

    total_bookings = db.query(func.count(Booking.id)).scalar()

    total_revenue = db.query(
        func.coalesce(func.sum(Booking.total_price), 0)
    ).filter(
        Booking.status == "COMPLETED"
    ).scalar()

    avg_rating = db.query(
        func.coalesce(func.avg(Review.rating), 0)
    ).scalar()

    return {
        "total_users": total_users,
        "total_drivers": total_drivers,
        "total_routes": total_routes,
        "completed_rides": completed_rides,
        "total_bookings": total_bookings,
        "total_revenue": float(total_revenue),
        "average_platform_rating": round(float(avg_rating), 2)
    }


@router.get("/daily-rides")
def daily_rides(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("AMIN"))
):
    data = db.query(
        func.date_trunc("day", Route.departure_time).label("day"),
        func.count(Route.id)
    ).group_by("day").order_by("day").all()

    return [
        {
            "date": row.day.strftime("%Y-%m-%d"),
            "rides":row[1]
        }
        for row in data
    ]


@router.get("/popular-routes")
def popular_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN"))
):
    routes = db.query(
        Route.start_city_id,
        Route.end_city_id,
        func.count(Booking.id).label("total_bookings")
    ).join(Booking, Booking.route_id == Route.id).filter(
        Booking.status == "COMPLETED"
    ).group_by(
        Route.start_city_id,
        Route.end_city_id
    ).order_by(
        func.count(Booking.id).desc()
    ).all()

    return [
        {
            "start_city_id":r.start_city_id,
            "end_city_id":r.end_city_id,
            "total_bookings":r.total_bookings
        }
        for r in routes
    ]



