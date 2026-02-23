from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.driver import Driver
from app.models.user import User
from app.models.driver_document import DriverDocument
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/driver", tags=["Driver"])

@router.post("/register")
def create_driver_profile(phone:str, vehicle_type:str,vehicle_number:str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "DRIVER":
        raise HTTPException(status_code=403, detail="Only driver can create profile")
    
    existing = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Driver profile already exists")
    
    driver= Driver(
        user_id=current_user.id,
        phone=phone,
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
def approve_driver(driver_id:int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin can approve drivers")
    
    driver = db.query(Driver).filter(Driver.id == driver_id).first()

    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
        
    driver.is_approved = True
    db.commit()

    return {"message": "Driver approved successfully"}