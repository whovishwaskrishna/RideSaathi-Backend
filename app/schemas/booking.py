from pydantic import BaseModel
from typing import Optional

class BookingCreate(BaseModel):
    route_id:int
    from_city_id:int
    to_city_id:int
    seats_booked:int