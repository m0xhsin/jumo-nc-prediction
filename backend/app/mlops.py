import argparse
import json
import os
import sys
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sqlalchemy import create_engine, text

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.preprocessing import Preprocessor
from app.scripts.apply_supabase_init import get_database_urls

try:
    import mlflow
    import mlflow.xgboost
except ImportError:
    mlflow = None


def _sqlalchemy_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def get_supabase_engine():
    """Create a SQLAlchemy engine for the Supabase Postgres database."""
    last_error: Exception | None = None
    for database_url in get_database_urls():
        try:
            engine = create_engine(_sqlalchemy_url(database_url), pool_pre_ping=True)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return engine
        except Exception as exc:
            last_error = exc

    return None


def configure_mlflow(experiment_name: str):
    if mlflow is None:
        return None

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    if tracking_uri.startswith("http"):
        import socket
        from urllib.parse import urlparse
        try:
            parsed = urlparse(tracking_uri)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 5000
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect((host, port))
            s.close()
        except Exception:
            tracking_uri = "sqlite:///mlflow.db"
            
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    return tracking_uri


def build_features_and_targets(df):
    """Prepares feature matrices and targets for JUMO datasets."""
    df = df.copy()
    
    # Fill missing values in essential variables
    for col in ['schichtdicke', 'schichtwiderstand', 'target', 'r20_pt_median', 'r0_pt_median']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(df[col].median())
            
    seasonal_cols = [c for c in df.columns if any(c.endswith(s) for s in ['_is_winter', '_is_spring', '_is_summer', '_is_autumn'])]
    
    base_features = [
        'schichtdicke', 'schichtwiderstand', 'target',
        'r20_pt_median', 'r0_pt_median',
        'lag_mean_tk_n_avg_5', 'lag_mean_r0_shift_5'
    ]
    
    features_to_use = base_features + seasonal_cols
    
    categorical_cols = ['sensor_group_type', 'sensor_group_resistance']
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)
            
    # Calculate improved final clean room target column (NCTr) chronologically
    df['nctr'] = df['n_nominalvaluecorrection'].fillna(df['nt_nominalvaluecorrection']).fillna(df['nominalvaluecorrection'])
            
    df_features = df[features_to_use + categorical_cols + ['sensor_group_key', 'nctr', 'tolp']].copy()
    df_features = pd.get_dummies(df_features, columns=categorical_cols, drop_first=True)
    
    bool_cols = df_features.select_dtypes(include=['bool']).columns
    df_features[bool_cols] = df_features[bool_cols].astype(int)
    
    return df_features


def train_regression_model(df_features, tracking_uri):
    """Trains and logs XGBoost Regressor for final clean room nominal correction (NCTr)."""
    data = df_features.dropna(subset=['nctr']).copy()
    
    target_mean = data['nctr'].mean()
    target_std = data['nctr'].std()
    # Filter outliers
    data = data[(data['nctr'] >= target_mean - 3 * target_std) & 
                (data['nctr'] <= target_mean + 3 * target_std)]
    
    X = data.drop(columns=['nctr', 'tolp', 'sensor_group_key'])
    y = data['nctr']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=data['sensor_group_key']
    )
    
    reg = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.08,
        random_state=42,
        verbosity=1
    )
    
    if mlflow is not None:
        mlflow.xgboost.autolog()
        
    run_name = "xgb_regressor_baseline"
    run_context = mlflow.start_run(run_name=run_name) if mlflow is not None else None
    
    try:
        reg.fit(X_train, y_train)
        y_pred = reg.predict(X_test)
        
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        within_tol = np.mean(np.abs(y_test - y_pred) <= 0.1) * 100
        
        print("\n--- Regression Model (NC) Results ---")
        print(f"RMSE: {rmse:.4f}")
        print(f"MAE:  {mae:.4f}")
        print(f"R2:   {r2:.4f}")
        print(f"Percentage within 0.1 Tol: {within_tol:.2f}%")
        
        if mlflow is not None:
            mlflow.log_metric("rmse", rmse)
            mlflow.log_metric("mae", mae)
            mlflow.log_metric("r2", r2)
            mlflow.log_metric("percent_within_tolerance", within_tol)
            mlflow.xgboost.log_model(reg, "model")
            print("[OK] Regression baseline logged to MLflow.")
            
        # Save model and feature list for inference serving
        services_dir = PROJECT_ROOT / "app" / "services"
        services_dir.mkdir(parents=True, exist_ok=True)
        model_save_path = services_dir / "xgb_regressor.pkl"
        
        # Get active MLflow run ID for compliance traceability
        run_id = mlflow.active_run().info.run_id if mlflow is not None and mlflow.active_run() is not None else "v1.0.0-local"
        
        model_data = {
            "model": reg,
            "feature_names": list(X.columns),
            "model_version": run_id
        }
        with open(model_save_path, "wb") as f:
            pickle.dump(model_data, f)
        print(f"[OK] Model saved successfully to {model_save_path}")
            
    finally:
        if run_context is not None:
            run_context.__exit__(None, None, None)


def train_classification_model(df_features):
    """Trains and logs XGBoost Classifier to predict tolerance class achieved."""
    data = df_features.copy()
    data['tolp'] = data['tolp'].astype(str).str.replace(',', '.', regex=False)
    
    valid_classes = ['F 0.1', 'F 0.15', 'F 0.3']
    data = data[data['tolp'].isin(valid_classes)].copy()
    
    class_mapping = {'F 0.1': 0, 'F 0.15': 1, 'F 0.3': 2}
    data['target_class'] = data['tolp'].map(class_mapping)
    
    X = data.drop(columns=['nctr', 'tolp', 'sensor_group_key', 'target_class'])
    y = data['target_class']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=data['sensor_group_key']
    )
    
    clf = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.08,
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        verbosity=1
    )
    
    run_name = "xgb_classifier_baseline"
    run_context = mlflow.start_run(run_name=run_name) if mlflow is not None else None
    
    try:
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        rec = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        
        print("\n--- Classification Model (Class) Results ---")
        print(f"Accuracy:  {acc:.4f}")
        print(f"Precision: {prec:.4f}")
        print(f"Recall:    {rec:.4f}")
        print(f"F1-Score:  {f1:.4f}")
        
        if mlflow is not None:
            mlflow.log_metric("accuracy", acc)
            mlflow.log_metric("precision", prec)
            mlflow.log_metric("recall", rec)
            mlflow.log_metric("f1_weighted", f1)
            mlflow.xgboost.log_model(clf, "model")
            print("[OK] Classification baseline logged to MLflow.")
    finally:
        if run_context is not None:
            run_context.__exit__(None, None, None)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the XGBoost regressor and classifier baseline models."
    )
    parser.add_argument("--experiment-name", default="jumo_laser_trimming_baselines")
    parser.add_argument("--skip-mlflow", action="store_true")
    args = parser.parse_args()

    # Check connection to Supabase
    engine = None
    use_supabase = False
    try:
        engine = get_supabase_engine()
        if engine is not None:
            use_supabase = True
            print("Successfully connected to Supabase database engine.")
    except Exception as e:
        print(f"Could not connect to Supabase: {e}. Running local pipeline...")

    print("Running data preprocessing pipeline...")
    preprocessor = Preprocessor()
    df_raw = preprocessor.run_pipeline(use_supabase_or_db=use_supabase, engine=engine)
    print(f"Raw joined shape: {df_raw.shape}")
    
    print("Building features...")
    df_features = build_features_and_targets(df_raw)
    print(f"Feature matrix shape: {df_features.shape}")

    tracking_uri = None
    if not args.skip_mlflow:
        tracking_uri = configure_mlflow(args.experiment_name)
        if tracking_uri:
            print(f"MLflow configured with tracking URI: {tracking_uri}")

    # Train models
    train_regression_model(df_features, tracking_uri)
    train_classification_model(df_features)
    
    print("\n[OK] Model training successfully completed!")


if __name__ == "__main__":
    main()
