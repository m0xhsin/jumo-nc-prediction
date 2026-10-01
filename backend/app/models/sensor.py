import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from app.database import Base

class SensorConfig(Base):
    __tablename__ = "sensor_configs"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String, unique=True, index=True, nullable=False)
    resistance = Column(Integer, nullable=False)  # 100, 500, 1000
    sensor_type = Column(String, nullable=False)  # T-type, E-type, H-type
    has_nt_step = Column(Boolean, nullable=False)  # True (Yes) or False (No)


class HistoricalOrder(Base):
    __tablename__ = "historical_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, nullable=True)
    paste_lot_ds1 = Column(String, nullable=True)
    paste_lot_ds2 = Column(String, nullable=True)
    ds1_viscosity = Column(Float, nullable=True)
    ds2_viscosity = Column(Float, nullable=True)
    air_humidity = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class NCPredictionRecord(Base):
    __tablename__ = "nc_prediction_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # Section 1: Sensor Type
    part_number = Column(String, nullable=False)
    resistance = Column(Integer, nullable=False)
    sensor_type = Column(String, nullable=False)
    has_nt_step = Column(Boolean, nullable=False)

    # Section 2: Sputter / Pre-Laser Data
    sputter_machine = Column(String, nullable=False)
    film_thickness = Column(Float, nullable=False)
    sheet_resistance = Column(Float, nullable=False)
    tcr_sputter = Column(Float, nullable=False)
    substrate_batch = Column(String, nullable=False)
    pt_r20_value = Column(Float, nullable=False)

    # Section 3: Screen Printing Input (Provided)
    paste_lot_ds1 = Column(String, nullable=True)
    paste_lot_ds2 = Column(String, nullable=True)
    ds1_viscosity_input = Column(Float, nullable=True)
    ds2_viscosity_input = Column(Float, nullable=True)
    air_humidity_input = Column(Float, nullable=True)

    # Effective Screen Printing Parameters Used in Calculation (Either input or computed average)
    effective_ds1_viscosity = Column(Float, nullable=False)
    effective_ds2_viscosity = Column(Float, nullable=False)
    effective_air_humidity = Column(Float, nullable=False)

    # Result
    recommended_nc_value = Column(Float, nullable=False)
    model_version = Column(String, nullable=True)
