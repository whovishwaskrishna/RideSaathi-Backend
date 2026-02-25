from pydantic import BaseModel, Field
from typing import Optional

class ReviewCreate(BaseModel):
    booking_id:int
    rating:int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None