from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.models.driver import Driver
from app.models.route import Route
from app.models.reviews import Review
from app.models.booking import Booking
from app.models.user import User
from app.models.driver_document import DriverDocument
from app.core.dependencies import get_current_user, require_role
from app.core.email_service import send_email

router = APIRouter(prefix="/driver", tags=["Driver"])

@router.post("/register")
def create_driver_profile(vehicle_type:str,vehicle_number:str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "DRIVER":
        raise HTTPException(status_code=403, detail="Only driver can create profile")
    
    existing = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Driver profile already exists")
    
    driver= Driver(
        user_id=current_user.id,        
        vehicle_type=vehicle_type,
        vehicle_number=vehicle_number
    )

    db.add(driver)
    db.commit()
    db.refresh(driver)

    return {"message": "Driver profile created", "driver_id":driver.id}


@router.post("/upload-documents")
def upload_document(document_type:str,document_url:str,db:Session= Depends(get_db), current_user:User=Depends(get_current_user)):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()

    if not driver:
        raise HTTPException(status_code=400, detail="Driver profile not found")
    
    document = DriverDocument(driver_id=driver.id,document_type=document_type,document_url=document_url)

    db.add(document)
    db.commit()

    return {"message": "Document upload successfully"}

@router.put("/approve/{driver_id}")
def approve_driver(
    driver_id:int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role("ADMIN"))
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    if driver.is_approved:
        raise HTTPException(status_code=400, detail="Driver already approved")
    
    driver.is_approved = True
    db.commit()

    background_tasks.add_task(
        send_email,
        driver.user.email,
        "Driver Account Approved",
        f"Hi {driver.user.name},\n\nCongratulations! Your driver account has been approved.\nYou can now start creating rides."
    )

    return {"message": "Driver approved successfully"}
    

@router.get("/earnings")
def driver_earnings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("DRIVER"))
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    total_routes = db.query(func.count(Route.id)).filter(Route.driver_id == driver.id).scalar()

    complete_routes = db.query(func.count(Route.id)).filter(
        Route.driver_id == driver.id,
        Route.status == "COMPLETED"
    ).scalar()

    active_routes = db.query(func.count(Route.id)).filter(
        Route.driver_id == driver.id,
        Route.status == "ACTIVE"
    ).scalar()

    seats_sold = db.query(
        func.coalesce(func.sum(Booking.seats_booked), 0)
    ).join(Route, Booking.route_id == Route.id).filter(Route.driver_id == driver.id,Booking.status == "COMPLETED").scalar()

    total_earnings = db.query(
        func.coalesce(func.sum(Booking.total_price), 0)
    ).join(Route, Booking.route_id == Route.id).filter(
        Route.driver_id == driver.id,
        Booking.status == "COMPLETED"
    ).scalar()

    return {
        "total_routes": total_routes,
        "completed_routes": complete_routes,
        "active_routes":active_routes,
        "total_seats_sold":seats_sold,
        "total_earning": total_earnings
    }

@router.get("/{driver_id}/profile")
def driver_public_profile(
    driver_id:int,
    review_page: int = Query(1, ge=1),
    review_limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    user = db.query(User).filter(User.id == driver_id).first()

    # Rating summary
    avg_rating = db.query(
        func.coalesce(func.avg(Review.rating), 0)
    ).filter(
        Review.driver_id == driver.id
    ).scalar()

    total_reviews = db.query(
        func.count(Review.id)
    ).filter(
        Review.driver_id == driver.id
    ).scalar()

    total_completed_rides = db.query(
        func.count(Booking.id)
    ).join(
        Route, Booking.route_id == Route.id
    ).filter(
        Route.driver_id == driver.id,
        Booking.status == "COMPLETED"
    ).scalar()

    offset = (review_page - 1) * review_limit

    review_query = db.query(
        Review.rating,
        Review.review_text,
        Review.created_at,
        User.name.label("customer_name")
    ).join(
        User, Review.customer_id == user.id
    ).filter(
        Review.driver_id == driver.id
    ).order_by(
        Review.created_at.desc()
    )

    total_review_records = review_query.count()

    review = review_query.offset(offset).limit(review_limit).all()

    review_list = [
        {
            "rating":r.rating,
            "review_text":r.review_text,
            "customer_name":r.customer_name,
            "created_at":r.created_at
        }
        for r in review
    ]

    return {
        "driver_id": driver.id,
        "name":user.name,
        "vehicle_type": driver.vehicle_type,
        "average_rating":round(float(avg_rating), 2),
        "total_reviews": total_reviews,
        "total_completed_rides": total_completed_rides,
        "reviews": review_list,
        "review_page": review_page,
        "review_total_pages": (total_review_records + review_limit - 1) // review_limit
    }


