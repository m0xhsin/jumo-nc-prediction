from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.sensor import SensorConfig
from app.schemas.config import SensorConfigResponse

router = APIRouter(
    prefix="/api/config",
    tags=["Configurations"]
)

@router.get("/parts", response_model=List[str])
def get_part_numbers(db: Session = Depends(get_db)):
    """
    Get a list of all registered Part Numbers.
    """
    configs = db.query(SensorConfig).all()
    # Return list of distinct part numbers
    return list(set([c.part_number for c in configs]))

@router.get("/details/{part_number}", response_model=SensorConfigResponse)
def get_part_details(part_number: str, db: Session = Depends(get_db)):
    """
    Get default configuration parameters (resistance, sensor_type, has_nt_step) for a given part number.
    """
    config = db.query(SensorConfig).filter(SensorConfig.part_number == part_number).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Part number '{part_number}' not found.")
    return config
