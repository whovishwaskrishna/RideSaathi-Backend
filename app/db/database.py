from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import time

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

for i in range(10):
    try:
        engine = create_engine(DATABASE_URL)
        engine.connect()
        print("Database connected successfully...")
        break
    except Exception as e:
        print("Database not ready, retrying...")
        time.sleep(3)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
