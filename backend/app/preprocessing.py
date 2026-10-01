from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Any

import pandas as pd
import numpy as np

DATETIME_NAME_HINTS = (
    "date",
    "time",
    "start",
    "finish",
    "finished",
    "created",
    "updated",
    "process_unit",
)


class Preprocessor:
    """Reusable preprocessing helpers for the manufacturing datasets."""

    def __init__(self, raw_data_dir: str | Path | None = None):
        if raw_data_dir is None:
            self.raw_data_dir = Path(__file__).resolve().parents[1] / "raw_data"
        else:
            self.raw_data_dir = Path(raw_data_dir)

    @staticmethod
    def normalize_column_names(data: pd.DataFrame) -> pd.DataFrame:
        """Return a copy with database-style lowercase snake_case columns."""
        df = data.copy()
        df.columns = [
            re.sub(r"_+", "_", re.sub(r"[^0-9a-zA-Z]+", "_", str(col)).strip("_")).lower()
            for col in df.columns
        ]
        return df

    @staticmethod
    def convert_decimal_columns(
        data: pd.DataFrame,
        columns: Iterable[str] | None = None,
    ) -> pd.DataFrame:
        """Convert comma-decimal text columns to numeric values."""
        df = data.copy()
        target_columns = list(columns) if columns is not None else list(df.columns)

        for column in target_columns:
            if column not in df.columns:
                continue
            if not pd.api.types.is_object_dtype(df[column]) and not pd.api.types.is_string_dtype(
                df[column]
            ):
                continue

            normalized = df[column].astype(str).str.strip().str.replace(",", ".", regex=False)
            numeric = pd.to_numeric(normalized, errors="coerce")
            
            # If it converts at least 50% of the non-null strings to numbers, we can keep it as numeric
            non_null_count = df[column].notna().sum()
            if non_null_count > 0 and (numeric.notna().sum() / non_null_count) > 0.5:
                df[column] = numeric

        return df

    @staticmethod
    def convert_datetime_columns(
        data: pd.DataFrame,
        columns: Iterable[str] | None = None,
        dayfirst: bool = True,
    ) -> pd.DataFrame:
        """Coerce selected or datetime-like object columns to pandas datetimes."""
        df = data.copy()
        target_columns = list(columns) if columns is not None else list(df.columns)

        for column in target_columns:
            if column not in df.columns:
                continue
            if columns is None and not any(hint in column.lower() for hint in DATETIME_NAME_HINTS):
                continue
            if pd.api.types.is_datetime64_any_dtype(df[column]):
                continue
            if pd.api.types.is_numeric_dtype(df[column]):
                continue
            if not pd.api.types.is_object_dtype(df[column]) and not pd.api.types.is_string_dtype(
                df[column]
            ):
                continue

            converted = pd.to_datetime(df[column], errors="coerce", dayfirst=dayfirst)
            if converted.notna().sum() > 0:
                df[column] = converted

        return df

    def convert_data_to_season_encoding(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add seasonal one-hot indicators for datetime columns."""
        df = data.copy()
        datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

        for column in datetime_cols:
            months = df[column].dt.month
            df[f"{column}_is_winter"] = months.isin([12, 1, 2]).fillna(False).astype(int)
            df[f"{column}_is_spring"] = months.isin([3, 4, 5]).fillna(False).astype(int)
            df[f"{column}_is_summer"] = months.isin([6, 7, 8]).fillna(False).astype(int)
            df[f"{column}_is_autumn"] = months.isin([9, 10, 11]).fillna(False).astype(int)

        return df

    def load_and_join_data(self, use_supabase_or_db: bool = False, engine: Any = None) -> pd.DataFrame:
        """Loads and joins all 7 tables in the correct order.
        
        Attempts to read from Supabase/PostgreSQL if use_supabase_or_db=True,
        otherwise falls back to local CSV files.
        """
        if use_supabase_or_db and engine is not None:
            try:
                print("Fetching joined dataset from database...")
                query = """
                    SELECT * FROM substrate 
                    INNER JOIN sputter ON substrate.substrat_id = sputter.substrat_id 
                    INNER JOIN laser ON sputter.substrat_id = laser.substrat_id 
                    INNER JOIN fertigungsauftrag ON substrate.fa_id = fertigungsauftrag.fa_id 
                    INNER JOIN partnumbers ON fertigungsauftrag.fa_teilenummer = partnumbers.teilenummer 
                    INNER JOIN siebdruck ON siebdruck.FA = fertigungsauftrag.FA 
                    INNER JOIN selektion ON selektion.FA = siebdruck.FA
                """
                df = pd.read_sql_query(query, engine)
                df.columns = [c.lower() for c in df.columns]
                return df
            except Exception as e:
                print(f"Database read failed ({e}). Falling back to local CSV files...")

        # Local CSV Ingestion
        def clean_and_load_csv(filename, sep=";", encoding="utf-8"):
            if "Teilenummer" in filename or "Part Number" in filename:
                encoding = "cp850"
            path = self.raw_data_dir / filename
            if not path.exists() and filename == "partnumbers-utf8.csv":
                path = self.raw_data_dir / "Teilenummer-Part Number.csv"
                encoding = "cp850"
            elif not path.exists() and filename == "Teilenummer-Part Number.csv":
                path = self.raw_data_dir / "partnumbers-utf8.csv"
                encoding = "utf-8"

            df_csv = pd.read_csv(path, sep=sep, encoding=encoding, low_memory=False)
            df_csv.columns = [c.lower() for c in df_csv.columns]
            return df_csv

        # Load CSVs
        substrate = clean_and_load_csv("Substrate_trimmed.csv")
        sputter = clean_and_load_csv("Sputtern-Sputtering_trimmed.csv")
        laser = clean_and_load_csv("Laser.csv")
        fertigungsauftrag = clean_and_load_csv("Fertigungsauftrag_trimmed.csv")
        partnumbers = clean_and_load_csv("Teilenummer-Part Number.csv")
        siebdruck = clean_and_load_csv("Siebdruck-Screen Printing_trimmed.csv")
        selektion = clean_and_load_csv("Selektion.csv")

        # Clean keys before join
        def to_numeric_id(series):
            s_str = series.astype(str).str.replace(',', '.', regex=False)
            return pd.to_numeric(s_str, errors='coerce')

        substrate['substrat_id'] = to_numeric_id(substrate['substrat_id'])
        sputter['substrat_id'] = to_numeric_id(sputter['substrat_id'])
        laser['substrat_id'] = to_numeric_id(laser['substrat_id'])

        substrate['fa_id'] = pd.to_numeric(substrate['fa_id'], errors='coerce')
        fertigungsauftrag['fa_id'] = pd.to_numeric(fertigungsauftrag['fa_id'], errors='coerce')

        fertigungsauftrag['fa_teilenummer'] = pd.to_numeric(fertigungsauftrag['fa_teilenummer'], errors='coerce')
        partnumbers['teilenummer'] = pd.to_numeric(partnumbers['teilenummer'], errors='coerce')

        fertigungsauftrag['fa'] = pd.to_numeric(fertigungsauftrag['fa'], errors='coerce')
        siebdruck['fa'] = pd.to_numeric(siebdruck['fa'], errors='coerce')
        selektion['fa'] = pd.to_numeric(selektion['fa'], errors='coerce')

        # Perform Joins
        m1 = pd.merge(substrate, sputter, on='substrat_id', suffixes=('', '_sputter'))
        m2 = pd.merge(m1, fertigungsauftrag, on='fa_id', suffixes=('', '_fa'))
        m3 = pd.merge(m2, laser, on='substrat_id', suffixes=('', '_laser'))
        m4 = pd.merge(m3, partnumbers, left_on='fa_teilenummer', right_on='teilenummer', suffixes=('', '_part'))
        m5 = pd.merge(m4, siebdruck, on='fa', suffixes=('', '_siebdruck'))
        m6 = pd.merge(m5, selektion, on='fa', suffixes=('', '_selektion'))

        # Drop duplicate columns
        cols_to_keep = [c for c in m6.columns if not any(c.endswith(s) for s in ['_sputter', '_fa', '_laser', '_part', '_siebdruck', '_selektion'])]
        return m6[cols_to_keep].copy()

    def add_sensor_group_features(self, df: pd.DataFrame, target_col: str = "sensortyp") -> pd.DataFrame:
        """Parses raw sensortyp names to extract type, resistance, and geometry groups."""
        df = df.copy()
        
        def parse_sensor(val):
            if pd.isna(val):
                return "Unknown", "Unknown", "Unknown"
            
            parts = str(val).strip().split(' ')
            sensor_type = parts[0]
            geometry = "Unknown"
            resistance = "Unknown"
            
            if len(parts) > 1:
                specs = parts[1].split('.')
                if len(specs) > 1:
                    geometry = specs[1]
                if len(specs) > 2:
                    raw_res = specs[2]
                    match = re.search(r'\d+', raw_res)
                    if match:
                        resistance = match.group()
                        
            return sensor_type, resistance, geometry

        parsed = df[target_col].apply(parse_sensor)
        df["sensor_group_type"] = [p[0] for p in parsed]
        df["sensor_group_resistance"] = [p[1] for p in parsed]
        df["sensor_group_geometry"] = [p[2] for p in parsed]
        df["sensor_group_key"] = df["sensor_group_type"] + "_" + df["sensor_group_resistance"]
        
        return df

    def add_paste_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes rolling averages of final selections from past orders to proxy paste lot shifts."""
        df = df.copy()
        
        if 'process_date' in df.columns:
            df['process_date_dt'] = pd.to_datetime(df['process_date'], errors='coerce')
        elif 'created' in df.columns:
            df['process_date_dt'] = pd.to_datetime(df['created'], errors='coerce')
        else:
            df['process_date_dt'] = pd.RangeIndex(len(df))

        df = df.sort_values('process_date_dt')

        # Rolling mean of TCR
        if 'tk_n_avg' in df.columns:
            df['lag_mean_tk_n_avg_5'] = df.groupby('sensor_group_key')['tk_n_avg'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            group_means = df.groupby('sensor_group_key')['tk_n_avg'].transform('mean')
            df['lag_mean_tk_n_avg_5'] = df['lag_mean_tk_n_avg_5'].fillna(group_means).fillna(3.86)

        # Rolling mean of R0 Shift
        if 'r0_n_avg' in df.columns and 'r0_ft_median' in df.columns:
            df['r0_shift'] = df['r0_n_avg'] - df['r0_ft_median']
            df['lag_mean_r0_shift_5'] = df.groupby('sensor_group_key')['r0_shift'].transform(
                lambda x: x.shift(1).rolling(5, min_periods=1).mean()
            )
            group_shift_means = df.groupby('sensor_group_key')['r0_shift'].transform('mean')
            df['lag_mean_r0_shift_5'] = df['lag_mean_r0_shift_5'].fillna(group_shift_means).fillna(0.0)

        if 'process_date_dt' in df.columns:
            df = df.drop(columns=['process_date_dt'])
            
        return df

    def prepare_supabase_frame(
        self,
        data: pd.DataFrame,
        decimal_columns: Iterable[str] | None = None,
        datetime_columns: Iterable[str] | None = None,
        add_season_features: bool = False,
    ) -> pd.DataFrame:
        """Normalize a frame read from Supabase or raw project CSV files."""
        df = self.normalize_column_names(data)
        df = self.convert_decimal_columns(df, decimal_columns)
        df = self.convert_datetime_columns(df, datetime_columns)
        if add_season_features:
            df = self.convert_data_to_season_encoding(df)
        return df

    def run_pipeline(self, use_supabase_or_db: bool = False, engine: Any = None) -> pd.DataFrame:
        """Runs the complete ingestion, cleaning, and engineering pipeline."""
        df = self.load_and_join_data(use_supabase_or_db=use_supabase_or_db, engine=engine)
        df = self.clean_commas_and_cast_wrapper(df)
        df = self.add_sensor_group_features(df)
        df = self.convert_data_to_season_encoding(df)
        df = self.add_paste_lag_features(df)
        return df

    def clean_commas_and_cast_wrapper(self, df: pd.DataFrame) -> pd.DataFrame:
        """Wrapper around convert_decimal_columns and convert_datetime_columns."""
        df = self.normalize_column_names(df)
        df = self.convert_decimal_columns(df)
        df = self.convert_datetime_columns(df)
        return df

    def prepare_model_frame(
        self,
        data: pd.DataFrame,
        feature_columns: Iterable[str],
        target_column: str,
    ) -> pd.DataFrame:
        """Prepare a clean numeric modelling frame for supervised training."""
        df = self.prepare_supabase_frame(data)

        required_columns = [*feature_columns, target_column]
        missing_columns = [column for column in required_columns if column not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required modelling columns: {missing_columns}")

        model_df = df[required_columns].copy()
        for column in required_columns:
            model_df[column] = pd.to_numeric(model_df[column], errors="coerce")

        return model_df.dropna(subset=required_columns).reset_index(drop=True)

    @staticmethod
    def summarize_dataset_changes(
        before: pd.DataFrame,
        after: pd.DataFrame,
    ) -> dict[str, object]:
        """Create a compact audit summary for Confluence/change logs."""
        return {
            "rows_before": int(len(before)),
            "rows_after": int(len(after)),
            "columns_before": int(before.shape[1]),
            "columns_after": int(after.shape[1]),
            "dropped_rows": int(len(before) - len(after)),
            "added_columns": sorted(set(after.columns) - set(before.columns)),
            "removed_columns": sorted(set(before.columns) - set(after.columns)),
        }
