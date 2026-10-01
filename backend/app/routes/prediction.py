from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.models.sensor import NCPredictionRecord
from app.services.predictor import calculate_nc_recommendation

router = APIRouter(
    prefix="/api/prediction",
    tags=["Predictions"]
)

@router.post("/calculate", response_model=PredictionResponse)
def calculate_prediction(payload: PredictionRequest, db: Session = Depends(get_db)):
    """
    Calculate the NC Recommendation.
    If optional screen printing values are omitted, they will be filled using the averages
    of past orders from the database. The calculation is logged in history.
    """
    try:
        record = calculate_nc_recommendation(payload, db)
        return record
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction calculation failed: {str(e)}")

@router.get("/history", response_model=List[PredictionResponse])
def get_prediction_history(db: Session = Depends(get_db)):
    """
    Get all past prediction records ordered by latest timestamp.
    """
    records = db.query(NCPredictionRecord).order_by(NCPredictionRecord.timestamp.desc()).all()
    return records

@router.delete("/history")
def clear_prediction_history(db: Session = Depends(get_db)):
    """
    Clear all past prediction history records from the database.
    """
    try:
        deleted_count = db.query(NCPredictionRecord).delete()
        db.commit()
        return {"status": "ok", "message": f"Cleared {deleted_count} prediction history records."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")

