from fastapi import FastAPI
from app.database import engine
from app import models
from app.routers import router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Fitlio",
    description="Sports facility management platform",
    version="1.0.0"
)

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "fitlio"}

@app.get("/")
def root():
    return {"message": "Welcome to Fitlio API"}
