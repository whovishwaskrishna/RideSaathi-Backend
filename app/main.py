from fastapi import FastAPI
from app.db.database import engine
from app.db.base import Base
import app.models
from app.routes import auth, driver, city, route, booking, review, notification_ws, admin_analytics, analytics

app=FastAPI(title="RideSaathi API")

@app.on_event("startup")
def create_tables():
    print("Creating tables...")
    # Base.metadata.create_all(bind=engine)
    print("Tables created:", Base.metadata.tables)

app.include_router(auth.router)
app.include_router(driver.router)
app.include_router(city.router)
app.include_router(route.router)
app.include_router(booking.router)
app.include_router(review.router)
app.include_router(notification_ws.router)
app.include_router(admin_analytics.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"message":"RideSaathi Backend Running"}
