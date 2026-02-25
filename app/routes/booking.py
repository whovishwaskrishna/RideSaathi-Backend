from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func
from datetime import datetime, timezone
from app.db.database import get_db
from app.models.route import Route
from app.models.city import City
from app.models.route_stop import RouteStop
from app.models.booking import Booking
from app.models.user import User
from app.core.dependencies import get_current_user, require_role
from app.schemas.booking import BookingCreate
from app.services.route_completion import auto_complete_route

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("/")
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("CUSTOMER"))
):
    route = (
        db.query(Route)
        .filter(Route.id == data.route_id)
        .with_for_update()
        .first()
    )

    if not route:
        raise HTTPException(404, "Route not found")

    # 🔥 Booking allowed only before start
    if route.status != "SCHEDULED":
        raise HTTPException(400, "Booking not allowed at this stage")

    if datetime.utcnow() >= route.departure_time:
        raise HTTPException(400, "Booking closed")

    stops = db.query(RouteStop).filter(
        RouteStop.route_id == route.id
    ).order_by(RouteStop.stop_order).all()

    start_order = None
    end_order = None

    for stop in stops:
        if stop.city_id == data.from_city_id:
            start_order = stop.stop_order
        if stop.city_id == data.to_city_id:
            end_order = stop.stop_order

    if not start_order or not end_order or start_order >= end_order:
        raise HTTPException(400, "Invalid city selection")

    existing_bookings = (
        db.query(Booking)
        .filter(
            Booking.route_id == route.id,
            Booking.status == "CONFIRMED"
        )
        .with_for_update()
        .all()
    )

    for segment in range(start_order, end_order):
        seats_used = 0

        for booking in existing_bookings:

            booking_start = None
            booking_end = None

            for stop in stops:
                if stop.city_id == booking.from_city_id:
                    booking_start = stop.stop_order
                if stop.city_id == booking.to_city_id:
                    booking_end = stop.stop_order

            if booking_start and booking_end:
                if booking_start <= segment < booking_end:
                    seats_used += booking.seats_booked

        if seats_used + data.seats_booked > route.available_seats:
            raise HTTPException(400, "Seats not available")

    total_price = route.price_per_seat * data.seats_booked

    booking = Booking(
        route_id=route.id,
        customer_id=current_user.id,
        from_city_id=data.from_city_id,
        to_city_id=data.to_city_id,
        seats_booked=data.seats_booked,
        total_price=total_price,
        status="CONFIRMED"
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "message": "Booking successful",
        "booking_id": booking.id,
        "total_price": total_price
    }


@router.put("/{booking_id}/cancel")
def cancel_booking(
    booking_id:int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("CUSTOMER"))
):
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    if booking.status != "CONFIRMED":
        raise HTTPException(status_code=400, detail="Booking cannot be cancelled")
    
    booking.status = "CANCELLED"

    db.commit()
    db.refresh(booking)

    return {
        "message":"Booking cancelled successfully",
        "booking_id": booking.id
    }


@router.get("/my")
def my_bookings(
    status: str = Query("ALL"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),    
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("CUSTOMER"))
):
    from_city = aliased(City)
    to_city = aliased(City)

    query = (
        db.query(
            Booking.id.label("booking_id"),
            Booking.route_id,
            from_city.name.label("from_city"),
            to_city.name.label("to_city"),
            Route.departure_time,
            Booking.seats_booked,
            Booking.total_price,
            Booking.status,
            Booking.created_at
        )
        .join(Route, Booking.route_id == Route.id)
        .join(from_city, Booking.from_city_id == from_city.id)
        .join(to_city, Booking.to_city_id == to_city.id)
        .filter(Booking.customer_id == current_user.id)        
    )

    now = datetime.utcnow()

    if status == "CONFIRMED":
        query = query.filter(
            Booking.status == "CONFIRMED",
            Route.departure_time > now
        )
    elif status == "COMPLETED":
        query = query.filter(Booking.status == "COMPLETED")
    elif status == "CANCELLED":
        query = query.filter(Booking.status == "CANCELLED")
    elif status != "ALL":
        raise HTTPException(status_code=400, detail="Invalid status filter")
    
    total_records = query.count()
    offset = (page - 1) * limit

    bookings = (
        query.order_by(Booking.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    result = []

    for row in bookings:
        result.append({
            "booking_id":row.booking_id,
            "route_id":row.route_id,
            "from_city":row.from_city,
            "to_city":row.to_city,
            "departure_time":row.departure_time,
            "seats_booked": row.seats_booked,
            "total_price": row.total_price,
            "status": row.status,
            "created_at": row.created_at
        })

    return {
        "page":page,
        "limit":limit,
        "total_records": total_records,
        "total_pages": (total_records + limit - 1) // limit,
        "data": result
    }