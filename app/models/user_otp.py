from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from app.db.base import Base

class UserOTP(Base):
    __tablename__ = "user_otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    otp_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    