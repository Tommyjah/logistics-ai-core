# ------------------------------------------------------------------
# MACHINE LEARNING CORE: PREDICTIVE FUEL FORECASTING ENGINE
# ------------------------------------------------------------------
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime


def prepare_fuel_features(df_fuel):
    """
    Transforms raw Supabase fuel logs into a highly informative feature matrix
    for predictive ML training.
    """
    if df_fuel.empty or len(df_fuel) < 3:
        return pd.DataFrame(), None

    # Ensure robust datetime sorting per vehicle
    df = df_fuel.copy()
    df['fuel_date'] = pd.to_datetime(df['fuel_date'])
    df = df.sort_values(['vehicle_id', 'fuel_date']).reset_index(drop=True)

    # 1. Feature Engineering: Compute deltas between sequential fuel entries
    df['prev_odometer'] = df.groupby('vehicle_id')['odometer_reading'].shift(1)
    df['prev_date'] = df.groupby('vehicle_id')['fuel_date'].shift(1)
    
    # Drop rows without a historical delta anchor
    df = df.dropna(subset=['prev_odometer', 'prev_date']).copy()
    
    # Calculate intervals
    df['km_driven'] = df['odometer_reading'] - df['prev_odometer']
    df['days_between'] = (df['fuel_date'] - df['prev_date']).dt.days
    
    # Prevent zero-division anomalies
    df['days_between'] = df['days_between'].replace(0, 1)
    df['km_per_day'] = df['km_driven'] / df['days_between']
    
    # 2. Extract Time-Based Cyclical Signatures
    df['log_month'] = df['fuel_date'].dt.month
    df['log_day_of_week'] = df['fuel_date'].dt.dayofweek
    
    # 3. Rolling Historical Metrics (Captures engine wear trends over time)
    df['rolling_avg_km_per_day'] = df.groupby('vehicle_id')['km_per_day'].transform(
        lambda x: x.rolling(window=3, min_periods=1).mean()
    )
    
    # Target Variable: The precise daily kilometer utilization to expect next
    X = df[['odometer_reading', 'log_month', 'log_day_of_week', 'rolling_avg_km_per_day']].copy()
    y = df['km_per_day'].copy()
    
    # Fill any edge-case NaN fragments from early windows safely
    X['rolling_avg_km_per_day'] = X['rolling_avg_km_per_day'].fillna(50.0)
    
    return X, y

def train_fuel_predictor(df_fuel):
    """
    Trains a Random Forest Regressor to predict upcoming daily fleet utilization.
    """
    X, y = prepare_fuel_features(df_fuel)
    
    if X.empty or len(X) < 2:
        # Fallback handle if history database size is too small
        return None

    # Instantiate robust ensemble regressor
    model = RandomForestRegressor(
        n_estimators=100, 
        max_depth=6, 
        random_state=42
    )
    model.fit(X, y)
    return model
# Append this to ml_engine.py
from sklearn.ensemble import IsolationForest
def detect_fuel_anomalies(df_fuel):
    """
    Uses an unsupervised Isolation Forest model to flag high-risk 
    anomalies and potential fuel fraud across fleet logs.
    """
    if df_fuel.empty or len(df_fuel) < 5:
        df_out = df_fuel.copy()
        df_out['is_anomaly'] = False
        df_out['anomaly_score'] = 0.0
        return df_out

    # Sort sequentially by vehicle and date to accurately calculate distances
    df = df_fuel.copy()
    df['fuel_date'] = pd.to_datetime(df['fuel_date'])
    df = df.sort_values(['vehicle_id', 'fuel_date']).reset_index(drop=True)

    # 1. Internal Feature Engineering: Calculate sequential distance driven
    df['prev_odometer'] = df.groupby('vehicle_id')['odometer_reading'].shift(1)
    df['distance_driven_internal'] = df['odometer_reading'] - df['prev_odometer']
    
    # Fill the first log entry shortfall with 0 or a reasonable historical gap floor
    df['distance_driven_internal'] = df['distance_driven_internal'].fillna(0)

    # Calculate engineering targets explicitly to catch anomalies cleanly
    df['km_per_liter_log'] = df['distance_driven_internal'] / df['liters_fueled'].replace(0, 1)
    df['cost_per_liter_log'] = df['cost_etb'] / df['liters_fueled'].replace(0, 1)
    
    # Handle infinite or invalid edge cases safely (like first entries where distance is 0)
    df['km_per_liter_log'] = df['km_per_liter_log'].fillna(10.0).replace([np.inf, -np.inf], 10.0)
    df['cost_per_liter_log'] = df['cost_per_liter_log'].fillna(85.0).replace([np.inf, -np.inf], 85.0)

    # Extract target array for Isolation Forest tracking
    X_anomaly = df[['km_per_liter_log', 'cost_per_liter_log']].values

    # 2. Train Isolation Forest
    iso_forest = IsolationForest(contamination=0.07, random_state=42)
    
    # Predict: -1 for outlier/anomaly, 1 for normal data point
    predictions = iso_forest.fit_predict(X_anomaly)
    raw_scores = iso_forest.score_samples(X_anomaly)

    # 3. Map outcomes back to output frame
    df['is_anomaly'] = predictions == -1
    
    min_s, max_s = raw_scores.min(), raw_scores.max()
    if max_s - min_s > 0:
        df['anomaly_score'] = ((max_s - raw_scores) / (max_s - min_s) * 100).astype(int)
    else:
        df['anomaly_score'] = 0

    return df
def evaluate_maintenance_risk(df_vehicles, df_maintenance):
    """
    Computes a predictive breakdown risk profile for every vehicle 
    using historical maintenance intervals and operational mileage stress metrics.
    """
    if df_vehicles.empty:
        return df_vehicles

    v_df = df_vehicles.copy()
    
    # Dynamic key lookups to accommodate varied database schema footprints
    odo_key = None
    for key in ['current_odometer', 'odometer', 'odometer_reading']:
        if key in v_df.columns:
            odo_key = key
            break

    # Robust fallback anchor
    if not odo_key:
        v_df['breakdown_risk_score'] = 12
        v_df['risk_status'] = "Healthy Status"
        return v_df

    risk_scores = []
    risk_labels = []

    for _, vehicle in v_df.iterrows():
        v_id = vehicle.get('id')
        current_odo = vehicle.get(odo_key, 0)
        
        # Pull specific service logs for this truck
        v_logs = df_maintenance[df_maintenance['vehicle_id'] == v_id] if not df_maintenance.empty else pd.DataFrame()
        
        # IMPROVED LOGIC: 
        # Only calculate 'km_since_service' if logs actually exist and have data.
        # Otherwise, set to 0 to prevent "Unknown" trucks from being marked as Critical.
        if not v_logs.empty and 'odometer_reading' in v_logs.columns and v_logs['odometer_reading'].max() > 0:
            last_service_odo = v_logs['odometer_reading'].max()
            km_since_service = max(0, current_odo - last_service_odo)
        else:
            # Baseline: Assume healthy until maintenance logs prove otherwise
            km_since_service = 0 

        # Standard heavy truck preventive maintenance threshold floor is 10,000 KM
        interval_pct = km_since_service / 10000.0

        # Compute Exponential Maintenance Risk Matrix
        base_risk = 10.0  # Safe resting operational baseline
        if interval_pct > 1.0:
            base_risk += min(55.0, (interval_pct - 1.0) * 40.0)  # Overdue scaling
        else:
            base_risk += (interval_pct * 20.0)

        # Model Year Age Vector Weighting
        vehicle_year = vehicle.get('year')
        if not vehicle_year or pd.isna(vehicle_year) or vehicle_year == 0:
            vehicle_year = 2018
            
        age_penalty = max(0, (2026 - int(vehicle_year)) * 2.5) 
        
        # Final score calculation
        final_score = min(99, max(5, int(base_risk + age_penalty)))
        
        # Categorize
        if final_score >= 70:
            status = "Critical Risk"
        elif final_score >= 40:
            status = "Elevated Risk"
        else:
            status = "Healthy Status"
            
        risk_scores.append(final_score)
        risk_labels.append(status)

    v_df['breakdown_risk_score'] = risk_scores
    v_df['risk_status'] = risk_labels
    return v_df