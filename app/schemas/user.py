from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    name:str
    email:str
    password:str
    role:Optional[str] = "CUSTOMER"

class UserResponse(BaseModel):
    id:int
    name:str
    email:EmailStr
    role:str

    class Config:
        from_attributes = True