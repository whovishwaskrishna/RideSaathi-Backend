from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.models.driver import Driver
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.route import RouteCreate

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
        available_seats=route.available_seats,
        price_per_seat=route.price_per_seat,
        status="ACTIVE"
    )

    print("Departure time type:", type(route.departure_time))

    db.add(new_route)
    db.commit()
    db.refresh(new_route)

    order = 1
    for city_id in route.stops:
        stop = RouteStop(
            route_id=new_route.id,
            city_id=city_id,
            stop_order=order
        )
        db.add(stop)
        order += 1

    db.commit()
    return {"message":"Route created successfully"}