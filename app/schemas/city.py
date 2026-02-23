from pydantic import BaseModel

class CityCreate(BaseModel):
    name:str
    state:str

class CityResponse(BaseModel):
    id:int
    name:str
    state:str

    class Config:
        from_attributes = True
