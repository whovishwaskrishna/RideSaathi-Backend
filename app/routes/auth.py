from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from sqlalchemy import func
from datetime import datetime

from app.db.database import get_db
from app.models.user import User
from app.models.user_otp import UserOTP
from app.schemas.user import UserCreate,OTPVerify, UserResponse
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token
from app.core.email_service import send_email
from app.core.dependencies import get_current_user, require_role
from app.core.otp import generate_otp, get_otp_expiry

router = APIRouter(prefix="/auth", tags=["Auth"])

ADMIN_EMAIL = "admin.ridesaathi@yopmail.com"

@router.post("/register", response_model=UserResponse)
def register(
    user:UserCreate, 
    backend_tasks:BackgroundTasks, 
    db: Session = Depends(get_db)
):

    # check duplicate email
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already register")
    
    # Hash Password
    hashed_password = hash_password(user.password)

    # create user
    new_user = User(
        name=user.name,
        email=user.email,
        phone=user.phone,
        password=hashed_password,
        role=user.role,
        is_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate OTP
    otp = generate_otp()
    otp_record = UserOTP(
        user_id=new_user.id,
        otp_hash=hash_password(otp),
        expires_at=get_otp_expiry()
    )

    db.add(otp_record)
    db.commit()

    backend_tasks.add_task(
        send_email,
        new_user.email,
        "Verify Your Email - RideSaathi OTP",
        f"Your OTP is: {otp}\nValid for 10 minutes."
    )

    if new_user.role == "DRIVER":

        #Email to Driver
        backend_tasks.add_task(
            send_email,
            new_user.email,
            "Driver Registration Received",
            f"Hi {new_user.name},\n\nYour driver registration is under review.\nWe will notify you once approved."
        )

        # Email to Admin
        backend_tasks.add_task(
            send_email,
            ADMIN_EMAIL,
            "New Driver Registration",
            f"New driver registerd:\n\nName: {new_user.name}\nEmail: {new_user.email}"
        )

    elif new_user.role == "CUSTOMER":
        backend_tasks.add_task(
            send_email,
            new_user.email,
            "New Driver Registration",
            f"Hi {new_user.name},\n\nYour account has been created successfully."
        )

    return new_user


@router.post("/verify-otp")
def verify_otp(
    data:OTPVerify,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    otp_record = db.query(UserOTP).filter(
        UserOTP.user_id == user.id
    ).order_by(UserOTP.id.desc()).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP not found")
    
    if datetime.utcnow() > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP expired")
    
    if not verify_password(data.otp, otp_record.otp_hash):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    user.is_verified = True
    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/resend-otp")
def resend_otp(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_verified:
        raise HTTPException(status_code=400, detail="User already verified")
    
    db.query(UserOTP).filter(UserOTP.user_id == user.id).delete()

    otp = generate_otp()

    otp_record = UserOTP(
        user_id=user.id,
        otp_hash=hash_password(otp),
        expires_at=get_otp_expiry()
    )

    db.add(otp_record)
    db.commit()

    background_tasks.add_task(
        send_email,
        user.email,
        "Resend OTP - RideSaathi",
        f"Your OYP s: {otp}\nValid for 10 minutes."
    )

    return {"message": "OTP resent successfully."}


@router.post("/forget-password")
def forget_password(
    email:str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.query(UserOTP).filter(UserOTP.user_id == user.id).delete()

    otp= generate_otp()

    otp_record = UserOTP(
        user_id=user.id,
        otp_hash=hash_password(otp),
        expires_at=get_otp_expiry()
    )

    db.add(otp_record)
    db.commit()

    background_tasks.add_task(
        send_email,
        user.email,
        "Password Reset OTP",
        f"Your OTP is: {otp}\nValid for 10 minutes."
    )

    return {"message": "Password reset OTP sent"}


@router.post("/reset-password")
def reset_password(
    email:str,
    otp:str,
    new_password:str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    otp_record = db.query(UserOTP).filter(
        UserOTP.user_id == user.id
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP not found")
    
    if datetime.utcnow() > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP Expired")
    
    if not verify_password(otp, otp_record.otp_hash):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    user.password = hash_password(new_password)

    db.delete(otp_record)
    db.commit()

    return {"message": "Password rest successfully."}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")
    
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    
    access_token = create_access_token({"sub": str(user.id), "role": user.role})

    return {
        "access_token":access_token, "token_type": "Bearer"
    }


@router.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role
    }


@router.get("/admin")
def admin_only(current_user: User = Depends(require_role("ADMIN"))):
    return {"message": "Welcome Admin"}


@router.get("/users", response_model=List[UserResponse])
def get_users(db: Session= Depends(get_db)):
    return db.query(User).filter(func.lower(User.role) != "admin").all()

