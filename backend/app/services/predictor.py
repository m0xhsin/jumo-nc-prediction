import datetime
import os
import re
import pickle
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
import numpy as np

from app.models.sensor import HistoricalOrder, NCPredictionRecord
from app.schemas.prediction import PredictionRequest

# Load the saved regression model and feature schema
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "app" / "services" / "xgb_regressor.pkl"

_model_cache = None

def get_trained_model():
    global _model_cache
    if _model_cache is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model pickle file not found at {MODEL_PATH}. Please run MLOps training first.")
        with open(MODEL_PATH, "rb") as f:
            _model_cache = pickle.load(f)
    return _model_cache


# Precalculated group average lags as robust fallbacks
LAG_DEFAULTS = {
    'lag_mean_tk_n_avg_5': {
        'PCA_1': 3.86427, 'PCA_10': 3.86280, 'PCA_20': 3.87277, 'PCA_5': 3.86382,
        'PCF_10': 3.86000, 'PCF_5': 3.86000, 'PCKL_1': 3.85916, 'PCKL_10': 3.86178,
        'PCS_07': 3.86000, 'PCS_1': 3.86000, 'PCS_10': 3.86000, 'PCS_5': 3.86000
    },
    'lag_mean_r0_shift_5': {
        'PCA_1': 2.68815, 'PCA_10': 1.73404, 'PCA_20': 0.58499, 'PCA_5': 0.19247,
        'PCF_10': 0.0, 'PCF_5': 0.0, 'PCKL_1': 3.03240, 'PCKL_10': 4.31535,
        'PCS_07': 0.0, 'PCS_1': 0.0, 'PCS_10': 0.0, 'PCS_5': 0.0
    }
}


def get_fallback_averages(db: Session):
    """
    Computes averages of past orders for the optional screen printing fields from the database.
    If no historical orders are present, returns standard fallback defaults.
    """
    avg_ds1 = db.query(func.avg(HistoricalOrder.ds1_viscosity)).scalar()
    avg_ds2 = db.query(func.avg(HistoricalOrder.ds2_viscosity)).scalar()
    avg_humidity = db.query(func.avg(HistoricalOrder.air_humidity)).scalar()
    
    return {
        "ds1_viscosity": round(float(avg_ds1), 2) if avg_ds1 is not None else 12.36,
        "ds2_viscosity": round(float(avg_ds2), 2) if avg_ds2 is not None else 14.02,
        "air_humidity": round(float(avg_humidity), 2) if avg_humidity is not None else 44.32
    }


def parse_sensor_group(part_number: str):
    """Parses raw part number to extract sensor group type, resistance and key."""
    parts = str(part_number).strip().split(' ')
    sensor_type = parts[0]
    resistance = "Unknown"
    
    if len(parts) > 1:
        specs = parts[1].split('.')
        if len(specs) > 2:
            raw_res = specs[2]
            match = re.search(r'\d+', raw_res)
            if match:
                resistance = match.group()
                
    key = f"{sensor_type}_{resistance}"
    return sensor_type, resistance, key


def calculate_nc_recommendation(payload: PredictionRequest, db: Session) -> NCPredictionRecord:
    """
    Orchestrates the calculation logic:
    1. Resolves optional screen printing parameters (using database averages if left blank).
    2. Constructs the feature vector and runs the XGBoost Regressor model.
    3. Saves the input parameters along with the recommendation to the database history.
    """
    # 1. Resolve optional screen printing values
    averages = get_fallback_averages(db)
    
    effective_ds1_viscosity = (
        payload.ds1_viscosity if payload.ds1_viscosity is not None else averages["ds1_viscosity"]
    )
    effective_ds2_viscosity = (
        payload.ds2_viscosity if payload.ds2_viscosity is not None else averages["ds2_viscosity"]
    )
    effective_air_humidity = (
        payload.air_humidity if payload.air_humidity is not None else averages["air_humidity"]
    )
    
    # 2. Extract sensor grouping and lag fallback values
    sensor_type, resistance_str, group_key = parse_sensor_group(payload.part_number)
    
    lag_tcr = LAG_DEFAULTS['lag_mean_tk_n_avg_5'].get(group_key, 3.84)
    lag_shift = LAG_DEFAULTS['lag_mean_r0_shift_5'].get(group_key, 0.0)
    
    # Calculate R0 pre-test median using physics heuristic: R0 = R20 / (1 + 20 * alpha)
    tcr_alpha = payload.tcr_sputter * 1e-3
    r0_pt_median = payload.pt_r20_value / (1.0 + 20.0 * tcr_alpha)
    
    # Fetch trained model and feature list
    model_data = get_trained_model()
    reg_model = model_data["model"]
    feature_names = model_data["feature_names"]
    
    # Construct seasonal variables dynamically based on current date
    now = datetime.datetime.utcnow()
    current_month = now.month
    is_winter = int(current_month in [12, 1, 2])
    is_spring = int(current_month in [3, 4, 5])
    is_summer = int(current_month in [6, 7, 8])
    is_autumn = int(current_month in [9, 10, 11])
    
    # Map input values to feature names
    input_features = {
        "schichtdicke": float(payload.film_thickness),
        "schichtwiderstand": float(payload.sheet_resistance),
        "target": float(payload.tcr_sputter),
        "r20_pt_median": float(payload.pt_r20_value),
        "r0_pt_median": float(r0_pt_median),
        "lag_mean_tk_n_avg_5": float(lag_tcr),
        "lag_mean_r0_shift_5": float(lag_shift),
    }
    
    # Construct complete feature row
    feature_row = {}
    for feat in feature_names:
        if feat in input_features:
            feature_row[feat] = input_features[feat]
        elif feat.endswith("_is_winter"):
            feature_row[feat] = is_winter
        elif feat.endswith("_is_spring"):
            feature_row[feat] = is_spring
        elif feat.endswith("_is_summer"):
            feature_row[feat] = is_summer
        elif feat.endswith("_is_autumn"):
            feature_row[feat] = is_autumn
        elif feat.startswith("sensor_group_type_"):
            group_type = feat.replace("sensor_group_type_", "")
            feature_row[feat] = 1 if sensor_type == group_type else 0
        elif feat.startswith("sensor_group_resistance_"):
            group_res = feat.replace("sensor_group_resistance_", "")
            feature_row[feat] = 1 if resistance_str == group_res else 0
        else:
            feature_row[feat] = 0.0  # Safe fallback for any other column
            
    # Perform inference
    df_sample = pd.DataFrame([feature_row])[feature_names]
    recommended_nc_value = reg_model.predict(df_sample)[0]
    
    # Ensure it's rounded
    recommended_nc_value = round(float(recommended_nc_value), 3)
    
    # 3. Log/Save to Database
    record = NCPredictionRecord(
        timestamp=now,
        part_number=payload.part_number,
        resistance=payload.resistance,
        sensor_type=payload.sensor_type,
        has_nt_step=payload.has_nt_step,
        sputter_machine=payload.sputter_machine,
        film_thickness=payload.film_thickness,
        sheet_resistance=payload.sheet_resistance,
        tcr_sputter=payload.tcr_sputter,
        substrate_batch=payload.substrate_batch,
        pt_r20_value=payload.pt_r20_value,
        paste_lot_ds1=payload.paste_lot_ds1,
        paste_lot_ds2=payload.paste_lot_ds2,
        ds1_viscosity_input=payload.ds1_viscosity,
        ds2_viscosity_input=payload.ds2_viscosity,
        air_humidity_input=payload.air_humidity,
        effective_ds1_viscosity=effective_ds1_viscosity,
        effective_ds2_viscosity=effective_ds2_viscosity,
        effective_air_humidity=effective_air_humidity,
        recommended_nc_value=recommended_nc_value,
        model_version=model_data.get("model_version", "v1.0.0-local")
    )
    
    db.add(record)
    db.commit()
    db.refresh(record)
    
    return record
