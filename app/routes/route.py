from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, aliased
from datetime import datetime, date
from sqlalchemy import func, desc,asc
from app.db.database import get_db, SessionLocal
from app.models.route import Route
from app.models.city import City
from app.models.route_stop import RouteStop
from app.models.driver import Driver
from app.models.user import User
from app.models.reviews import Review
from app.models.booking import Booking
from app.core.dependencies import get_current_user, require_role
from app.core.ws_manager import ConnectionManager
from app.core.jwt import verify_token
from app.schemas.route import RouteCreate
from app.services.route_completion import auto_complete_route

router = APIRouter(prefix="/routes", tags=["Routes"])

@router.post("/")
def create_route(route: RouteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()

    if not driver:
        raise HTTPException(status_code=400, detail="Driver profile not found")
    
    if not driver.is_approved:
        raise HTTPException(status_code=403, detail="Driver not approved")
    
    new_route = Route(
        driver_id=driver.id,
        start_city_id=route.start_city_id,
        end_city_id=route.end_city_id,
        departure_time=route.departure_time,
        estimated_duration_minutes=route.estimated_duration_minutes,
        available_seats=route.available_seats,
        price_per_seat=route.price_per_seat,
        status="ACTIVE"
    )

    print("Departure time type:", type(route.departure_time))

    db.add(new_route)
    db.commit()
    db.refresh(new_route)

    order = 1

    db.add(RouteStop(
        route_id= new_route.id,
        city_id=route.start_city_id,
        stop_order=order
    ))
    order += 1

    for city_id in route.stops:
        db.add(RouteStop(
            route_id=new_route.id,
            city_id=city_id,
            stop_order=order
        ))
        order += 1

    db.add(RouteStop(
        route_id=new_route.id,
        city_id=route.end_city_id,
        stop_order=order
    ))

    db.commit()
    return {"message":"Route created successfully", "route_id":new_route.id}


@router.get("/{route_id}/bookings")
def get_route_bookings(
    route_id:int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("DRIVER"))
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()

    if not driver:
        raise HTTPException(status_code=400, detail="Driver profile not found")
    
    route = db.query(Route).filter(Route.id == route_id).first()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    if route.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    bookings = db.query(Booking).filter(
        Booking.route_id == route.id,
        Booking.status == "CONFIRMED"
    ).all()

    return {
        "route_id": route.id,
        "total_bookings": len(bookings),
        "booking": bookings
    }


@router.get("/{route_id}/summary")
def route_summary(
    route_id:int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("DRIVER"))
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()

    if not driver:
        raise HTTPException(status_code=400, detail="Driver profile not found")
    
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    if route.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    auto_complete_route(db, route)

    db.refresh(route)
    
    summary = db.query(
        func.coalesce(func.sum(Booking.seats_booked), 0).label("seats_sold"),
        func.coalesce(func.sum(Booking.total_price), 0).label("total_revenue")
    ).filter(
        Booking.route_id == route.id,
        Booking.status == "COMPLETED"
    ).first()

    seats_sold = summary.seats_sold
    total_revenue = summary.total_revenue
    remaining_seats = route.available_seats - seats_sold

    return {
        "route_id":route.id,
        "total_capacity": route.available_seats,
        "seats_sold": seats_sold,
        "remaining_seats": remaining_seats,
        "total_revenue": total_revenue
    }


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

@router.put("/{router_id}/start")
def start_route(
    route_id:int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("DRIVER"))
):
    
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(400, "Driver profile not found")

    route = db.query(Route).filter(
        Route.id == route_id,
        Route.driver_id == driver.id
    ).first()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    if route.status != "SCHEDULED":
        raise HTTPException(status_code=400, detail="Route cannot be started")
    
    route.status = "STARTED"
    db.commit()

    return {"message":"Ride started"}


@router.put("/{route_id}/complete")
def complete_route(
    route_id:int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("DRIVER"))
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(400, "Driver profile not found")

    route = db.query(Route).filter(
        Route.id == route_id,
        Route.driver_id == driver.id
    ).first()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    if route.status != "STARTED":
        raise HTTPException(status_code=400, detail="Route not in progress")
    
    route.status = "COMPLETED"

    db.query(Booking).filter(
        Booking.route_id == route.id,
        Booking.status == "CONFIRMED"
    ).update({"status": "COMPLETED"})

    db.commit()

    return {"message": "Ride Completed"}

# ws://localhost:8000/routes/ws/routes/1/driver?token=YOUR_JWT
@router.websocket("/ws/routes/{route_id}/driver")
async def dricer_tracking(websocket: WebSocket, route_id: int):

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close()
        return
     
    payload = verify_token(token)
    if not payload:
        await websocket.close()
        return
     
    user_id = int(payload.get("sub"))

    db = SessionLocal()
    try:
        driver = db.query(Driver).filter(
            Driver.user_id == user_id
        ).first()

        route = db.query(Route).filter(
            Route.id == route_id
        ).first()

        if not driver or not route or route.driver_id != driver.id:
            await websocket.close()
            return
        
        if route.status != "STARTED":
            await websocket.close()
            return
        
        await websocket.accept()
        await ConnectionManager.connect(route_id, websocket)

        while True:
            data = await websocket.receive_json()

            await ConnectionManager.broadcast(route_id, {
                "latitude": data["latitude"],
                "longitude": data["longitude"]
            })
    except WebSocketDisconnect:
        ConnectionManager.disconnect(route_id, websocket)
    finally:
        db.close()

# ws://localhost:8000/routes/ws/routes/1?token=YOUR_JWT
@router.websocket("/ws/routes/{route_id}")
async def customer_traking(websocket:WebSocket, route_id:int):

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close()
        return
    
    payload = verify_token(token)
    if not payload:
        await websocket.close()
        return
    
    user_id = int(payload.get("sub"))

    db = SessionLocal()

    try:
        booking = db.query(Booking).filter(
            Booking.route_id - route_id,
            Booking.customer_id == user_id,
            Booking.status.in_(["CONFIRMED", "COMPLETED"])
        ).first()

        route = db.query(Route).filter(
            Route.id == route_id
        ).first()

        if not booking or not route or route.status != "STARTED":
            await websocket.close()
            return
        
        await websocket.accept()
        await ConnectionManager.connect(route_id, websocket)

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        ConnectionManager.disconnect(route_id, websocket)
    finally:
        db.close()
