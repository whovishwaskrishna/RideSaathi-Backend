from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from datetime import date
from app.db.database import get_db
from app.models.route import Route
from app.models.driver import Driver
from app.models.user import User
from app.models.reviews import Review
from app.models.booking import Booking

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.get("/search")
def search_routes(
    from_city_id: int,
    to_city_id: int,
    travel_date: date,

    min_rating: float = Query(None),
    only_verified: bool = Query(False),

    sort_by: str = Query("departure_time"),
    order: str = Query("asc"),

    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),

    db: Session = Depends(get_db)
):

    # ⭐ Rating subquery
    rating_subq = (
        db.query(
            Review.driver_id.label("driver_id"),
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("total_reviews")
        )
        .group_by(Review.driver_id)
        .subquery()
    )

    # 💺 Seats subquery
    seats_subq = (
        db.query(
            Booking.route_id.label("route_id"),
            func.sum(Booking.seats_booked).label("seats_sold")
        )
        .filter(Booking.status == "CONFIRMED")
        .group_by(Booking.route_id)
        .subquery()
    )

    query = (
        db.query(
            Route.id,
            Route.departure_time,
            Route.price_per_seat,
            Route.available_seats,
            Route.status,
            Driver.vehicle_type,
            User.name.label("driver_name"),
            User.is_verified,
            func.coalesce(rating_subq.c.avg_rating, 0).label("avg_rating"),
            func.coalesce(rating_subq.c.total_reviews, 0).label("total_reviews"),
            func.coalesce(seats_subq.c.seats_sold, 0).label("seats_sold"),
        )
        .join(Driver, Route.driver_id == Driver.id)
        .join(User, Driver.user_id == User.id)
        .outerjoin(rating_subq, Driver.id == rating_subq.c.driver_id)
        .outerjoin(seats_subq, Route.id == seats_subq.c.route_id)
        .filter(Route.status.in_(["SCHEDULED", "ACTIVE"]))
    )

    # 🎯 Rating filter (FIXED)
    if min_rating:
        query = query.filter(
            func.coalesce(rating_subq.c.avg_rating, 0) >= min_rating
        )

    # ✔ Verified filter
    if only_verified:
        query = query.filter(User.is_verified == True)

    # 🔃 Sorting
    if sort_by == "price":
        sort_column = Route.price_per_seat
    elif sort_by == "rating":
        sort_column = rating_subq.c.avg_rating
    else:
        sort_column = Route.departure_time

    if order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # 📄 Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    results = []

    for row in query.all():

        remaining = row.available_seats - row.seats_sold
        if remaining <= 0:
            continue

        results.append({
            "route_id": row.id,
            "driver_name": row.driver_name,
            "vehicle_type": row.vehicle_type,
            "departure_time": row.departure_time,
            "price_per_seat": row.price_per_seat,
            "remaining_seats": remaining,
            "average_rating": round(float(row.avg_rating), 2),
            "total_reviews": row.total_reviews,
            "is_verified": row.is_verified,
            "status": row.status
        })

    return {
        "page": page,
        "limit": limit,
        "results": results
    }