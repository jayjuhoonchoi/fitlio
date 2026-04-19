from fastapi import FastAPI

app = FastAPI(
    title="Fitlio",
    description="Sports facility management platform",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "fitlio"}

@app.get("/")
def root():
    return {"message": "Welcome to Fitlio API"}
