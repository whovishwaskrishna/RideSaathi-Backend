from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import Review, Booking, Driver, Route, User
from app.core.dependencies import require_role
from app.schemas.review import ReviewCreate

router = APIRouter(prefix="/reviews", tags=["Reviews"])

# Customer use for Review
@router.post("/")
def create_review(
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("CUSTOMER"))                          
):
    
    booking = db.query(Booking).filter(Booking.id == data.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    if booking.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Can review only completed rides")
    
    existing_review = db.query(Review).filter(
        Review.booking_id == booking.id
    ).first()
    if existing_review:
        raise HTTPException(status_code=400, detail="Review already submitted")
    
    route = db.query(Route).filter(Route.id == booking.route_id).first()
    driver = db.query(Driver).filter(Driver.id == route.driver_id).first()

    review = Review(
        booking_id=booking.id,
        driver_id=driver.id,
        customer_id=current_user.id,
        rating=data.rating,
        review_text=data.review_text
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    return {
        "message": "Review submitted successfully",
        "review_id": review.id
    }
    
# Driver use for get Review
@router.get("/ratings")
def driver_rating_Summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("DRIVER"))
):
    driver = db.query(Driver).filter(
        Driver.user_id == current_user.id
    ).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    # Average rating
    avg_rating = db.query(
        func.coalesce(func.avg(Review.rating), 0)
    ).filter(
        Review.driver_id == driver.id
    ).scalar()

    # Total reviews
    total_review = db.query(
        func.count(Review.id)
    ).filter(
        Review.driver_id == driver.id
    ).scalar()

    # Rating breakdown
    breakdown = db.query(
        Review.rating,
        func.count(Review.id)
    ).filter(
        Review.driver_id == driver.id
    ).group_by(Review.rating).all()

    rating_breakdown = {i:0 for i in range(1,6)}
    for rating, count in breakdown:
        rating_breakdown[rating] = count

    return {
        "average_rating": round(float(avg_rating), 2),
        "total_reviews": total_review,
        "rating_breakdown": rating_breakdown
    }
