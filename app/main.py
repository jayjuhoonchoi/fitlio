from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from fastapi import FastAPI
from app.database import engine
from app import models
from app.routers import router as auth_router
from app.bookings import router as booking_router
from app.payments import router as payment_router
from app.attendance import router as attendance_router
from app.admin import router as admin_router

models.Base.metadata.create_all(bind=engine)

from app.seed import seed_database
seed_database()

app = FastAPI(
    title="Fitlio",
    description="Sports facility management platform",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(booking_router)
app.include_router(payment_router)
app.include_router(attendance_router)
app.include_router(admin_router)

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("app/templates/index.html", "r") as f:
        return f.read()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "fitlio"}
    