from fastapi import FastAPI
from app.routes import health

app = FastAPI(title="CodeBot API", version="1.0")

app.include_router(health.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "🚀 CodeBot API is running successfully!"}