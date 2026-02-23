from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.city import City
from app.schemas.city import CityCreate, CityResponse
from typing import List

router = APIRouter(prefix="/cities", tags=["Cities"])

@router.post("/", response_model=CityResponse)
def create_city(city: CityCreate, db: Session = Depends(get_db)):
    new_city = City(name=city.name, state=city.state)
    db.add(new_city)
    db.commit()
    db.refresh(new_city)
    return new_city

@router.get("/", response_model=List[CityResponse])
def get_cities(db:Session=Depends(get_db)):
    return db.query(City).all()