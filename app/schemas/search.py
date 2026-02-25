from pydantic import BaseModel

class RouteSearch(BaseModel):
    start_city_id:int
    end_city_id:int