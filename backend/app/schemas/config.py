from pydantic import BaseModel

class SensorConfigBase(BaseModel):
    part_number: str
    resistance: int
    sensor_type: str
    has_nt_step: bool

class SensorConfigCreate(SensorConfigBase):
    pass

class SensorConfigResponse(SensorConfigBase):
    id: int

    class Config:
        from_attributes = True
