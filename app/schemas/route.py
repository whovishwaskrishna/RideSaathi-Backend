from pydantic import BaseModel
from datetime import datetime
from typing import List

class RouteCreate(BaseModel):
    start_city_id:int
    end_city_id:int
    departure_time:datetime
    estimated_duration_minutes: int
    available_seats:int
    price_per_seat:float
    stops: List[int]