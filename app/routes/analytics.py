from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.models.route import Route
from app.models.booking import Booking
from app.models.reviews import Review
from app.models.driver import Driver
from app.models.user import User
from app.core.dependencies import require_role

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/driver/dashboard")
def driver_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("DRIVER"))
):
    driver = db.query(Driver).filter(
        Driver.user_id == current_user.id
    ).first()
    if not driver:
        HTTPException(status_code=404, detail="Driver not found")

    total_routes = db.query(func.count(Route.id)).filter(
        Route.driver_id == driver.id
    ).scalar()

    completed_routes = db.query(func.count(Route.id)).filter(
        Route.driver_id == driver.id,
        Route.status == "COMPLETE"
    ).scalar()

    total_revenue = db.query(
        func.coalesce(func.sum(Booking.seats_booked), 0)
    ).join(Route, Booking.route_id == Route.id).filter(
        Route.driver_id == driver.id,
        Booking.status == "COMPLETED"
    ).scalar()

    total_passengers = db.query(
        func.coalesce(func.sum(Booking.seats_booked), 0)
    ).join(Route, Booking.route_id == Route.id).filter(
        Route.driver_id == driver.id,
        Booking.status == "COMPLETED"
    ).scalar()

    avg_rating = db.query(
        func.coalesce(func.avg(Review.rating), 0)
    ).filter(
        Review.driver_id == driver.id
    ).scalar()

    return {
        "total_routes": total_routes,
        "completed_routes": completed_routes,
        "total_revenue": float(total_revenue),
        "total_passengers": int(total_passengers),
        "total_revenue": round(float(avg_rating), 2)
    }


@router.get("driver/monthly-revenue")
def driver_monthly_revenue(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("DRIVER"))
):
    driver = db.query(Driver).filter(
        Driver.user_id == current_user.id
    ).first()
    if not driver:
        HTTPException(status_code=404, detail="Driver not found")

    monthly_data = db.query(
        func.date_trunc("month", Booking.created_at).label("month"),
        func.sum(Booking.total_price)
    ).join(Route, Booking.route_id == Route.id).filter(
        Route.driver_id == driver.id,
        Booking.status == "COMPLETED"
    ).group_by("month").order_by("month").all()

    return[
        {
            "month":row.month.strtime("%Y-%m"),
            "revenue": float(row[1])
        }
        for row in monthly_data
    ]


@router.get("driver/route-performance")
def route_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("DRIVER"))
):
    driver = db.query(Driver).filter(
        Driver.user_id == current_user.id        
    ).first()
    if not driver:
        HTTPException(status_code=404, detail="Driver not found")

    routes = db.query(
        Route.id,
        func.count(Booking.id).label("bookings"),
        func.coalesce(func.sum(Booking.total_price), 0).label("revenue")
    ).outerjoin(Booking, Booking.route_id == Route.id).filter(
        Route.driver_id == driver.id
    ).group_by(Route.id).all()

    return [
        {
            "route_id":r.id,
            "total_booking" : r.bookings,
            "total_revenue": float(r.revenue)
        }
        for r in routes
    ]
