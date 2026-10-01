from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.config import router as config_router
from app.routes.prediction import router as prediction_router

app = FastAPI(
    title="NC Prediction API",
    description="Backend API for Sensor Manufacturing NC Recommendation",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router)
app.include_router(prediction_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "NC Prediction API is running"}
