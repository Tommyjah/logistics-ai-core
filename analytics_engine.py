import os
import pandas as pd
import numpy as np
import warnings
from supabase import create_client, Client
from sklearn.linear_model import LinearRegression
from dotenv import load_dotenv

# Suppress warnings for clean output
warnings.filterwarnings("ignore")

# Load environment variables from the .env file


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    raise ValueError("System Error: SUPABASE_KEY not found in the environment setup.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def calculate_fuel_efficiency():
    try:
        # 1. Fetch fuel logs and pull the associated vehicle's plate number via foreign key relation
        response = supabase.table("fleet_fuel_logs").select(
            "liters_fueled, cost_etb, odometer_reading, fleet_vehicles(plate_number)"
        ).execute()
        
        logs = response.data
        if not logs:
            return []

        # 2. Flatten out the nested relational plate_number data for pandas processing
        flattened_logs = []
        for log in logs:
            flattened_logs.append({
                "plate_number": log["fleet_vehicles"]["plate_number"] if log.get("fleet_vehicles") else "Unknown",
                "liters_fueled": float(log["liters_fueled"]),
                "cost_etb": float(log["cost_etb"]),
                "odometer_reading": int(log["odometer_reading"])
            })
            
        df = pd.DataFrame(flattened_logs)
        
        # 3. Aggregate stats grouped by vehicle plate number
        analytics_summary = []
        for plate, group in df.groupby("plate_number"):
            total_liters = group["liters_fueled"].sum()
            total_cost = group["cost_etb"].sum()
            
            # Distance calculated as the gap between their oldest and newest fueling log mileage
            max_odo = group["odometer_reading"].max()
            min_odo = group["odometer_reading"].min()
            distance_driven = max_odo - min_odo
            
            # Prevent Division By Zero error if there is only 1 fuel log or 0 liters
            km_per_liter = round(distance_driven / total_liters, 2) if total_liters > 0 and distance_driven > 0 else 0.0
            
            analytics_summary.append({
                "plate_number": plate,
                "total_liters": round(total_liters, 2),
                "total_cost_etb": round(total_cost, 2),
                "km_per_liter": km_per_liter
            })
            
        # Sort by efficiency descending (Best performing vehicles at the top)
        return sorted(analytics_summary, key=lambda x: x["km_per_liter"], reverse=True)

    except Exception as e:
        print(f"Error computing fuel matrix: {e}")
        return []





def fetch_production_data():
    """Fetches and cleans raw fleet logs."""
    response = supabase.table("fleet_monthly_logs").select(
        "km_driven, fuel_cost_etb, maintenance_cost_etb, days_under_maintenance, "
        "fleet_vehicles(condition_status, project_assignment)"
    ).execute()
    
    raw_df = pd.DataFrame(response.data)
    if raw_df.empty:
        return pd.DataFrame()
        
    raw_df['condition'] = raw_df['fleet_vehicles'].apply(lambda x: x['condition_status'] if isinstance(x, dict) else 'Good')
    raw_df['project'] = raw_df['fleet_vehicles'].apply(lambda x: x['project_assignment'] if isinstance(x, dict) else 'CORE FLEET')
    return raw_df

def get_production_metrics(target_km, days_maint):
    """Calculates predictions based on inputs."""
    df = fetch_production_data()
    if df.empty:
        return {"error": "No data found"}

    # Historical Shop Rate
    # Fix: fillna(0) to make sure math comparisons don't fail silently on empty datasets
    df['maintenance_cost_etb'] = pd.to_numeric(df['maintenance_cost_etb']).fillna(0)
    df['days_under_maintenance'] = pd.to_numeric(df['days_under_maintenance']).fillna(0)
    df['fuel_cost_etb'] = pd.to_numeric(df['fuel_cost_etb']).fillna(0)
    df['km_driven'] = pd.to_numeric(df['km_driven']).fillna(0)

    valid_maint_data = df[(df['maintenance_cost_etb'] > 0) & (df['days_under_maintenance'] > 0)]
    total_days_recorded = valid_maint_data['days_under_maintenance'].sum()
    historical_shop_rate = valid_maint_data['maintenance_cost_etb'].sum() / total_days_recorded if total_days_recorded > 0 else 2500.0
    
    # Prepare Data
    df_encoded = pd.get_dummies(df, columns=['condition', 'project'])
    required_features = [
        'km_driven', 'days_under_maintenance',
        'condition_Excellent', 'condition_Very Good', 'condition_Under Maintenance',
        'project_CM', 'project_LIWAY', 'project_BRIDGE', 'project_HORTI-LIFE'
    ]
    for col in required_features:
        if col not in df_encoded.columns:
            df_encoded[col] = 0

    # Train Models
    fuel_model = LinearRegression().fit(
        df_encoded[['km_driven', 'condition_Excellent', 'condition_Very Good', 'project_CM', 'project_LIWAY']], 
        df_encoded['fuel_cost_etb']
    )
    maint_model = LinearRegression().fit(
        df_encoded[['days_under_maintenance', 'condition_Under Maintenance', 'project_CM', 'project_BRIDGE']], 
        df_encoded['maintenance_cost_etb']
    )

    # Predictions
    pred_fuel_a = max(0.0, fuel_model.predict([[target_km, 1, 0, 1, 0]])[0])
    pred_maint_a = 0.0
    
    pred_fuel_b = 0.0
    raw_maint_b = maint_model.predict([[days_maint, 1, 1, 0]])[0]
    
    # Mathematical protection line to avoid 0 ETB returning from untrained models
    calculated_fallback = days_maint * historical_shop_rate
    pred_maint_b = max(float(raw_maint_b), float(calculated_fallback))

    return {
        "scenario_a": {
            "fuel": round(float(pred_fuel_a), 2),
            "maintenance": round(float(pred_maint_a), 2),
            "total": round(float(pred_fuel_a + pred_maint_a), 2)
        },
        "scenario_b": {
            "fuel": round(float(pred_fuel_b), 2),
            "maintenance": round(float(pred_maint_b), 2),
            "total": round(float(pred_fuel_b + pred_maint_b), 2)
        }
    }

def fetch_fleet_query(query_type):
    """
    SURGERY: Strictly segmented filtering.
    Only shows vehicles that truly match the status requested.
    """
    try:
        response = supabase.table("fleet_vehicles").select("*").execute()
        all_vehicles = response.data if response.data else []
        
        if query_type == "List All Vehicles":
            return all_vehicles
            
        filtered_results = []
        for v in all_vehicles:
            # Clean and normalize status
            status = str(v.get('condition_status', '')).strip().lower()
            
            # STRICT LOGIC:
            # Vehicles in Workshop only show if they contain maintenance keywords
            if query_type == "Vehicles in Workshop":
                if status in ["under maintenance", "maintenance", "workshop", "repair"]:
                    filtered_results.append(v)
            
            # Vehicles Needing Inspection only show if they are poor/bad/fair
            elif query_type == "Vehicles Needing Inspection":
                if status in ["poor", "bad", "fair", "needs inspection"]:
                    filtered_results.append(v)
                    
        return filtered_results
    except Exception as e:
        print(f"Surgery Filter Error: {e}")
        return []


def get_all_vehicle_plates():
    """
    Fetches all unique license plate numbers from the database to populate UI drop-down selectors.
    """
    try:
        response = supabase.table("fleet_vehicles").select("plate_number").order("plate_number").execute()
        return [row["plate_number"] for row in response.data] if response.data else []
    except Exception as e:
        print(f"Error fetching plate matrix: {e}")
        return []

def update_workshop_status(plate_number: str, check_in: bool):
    """
    Updates the operational flag for a targeted vehicle row inside Supabase.
    """
    try:
        response = supabase.table("fleet_vehicles").update(
            {"is_in_workshop": check_in}
        ).eq("plate_number", plate_number).execute()
        return True if response.data else False
    except Exception as e:
        print(f"Error updating workshop vector: {e}")
        return False

def get_available_drivers():
    """Fetches all drivers currently flagged as Available from the database."""
    try:
        response = supabase.table("drivers").select("id, full_name, license_number, work_status").eq("work_status", "Available").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Database error fetching drivers: {e}")
        return []

def assign_driver_to_vehicle(plate_number: str, driver_id: str or None):
    """Links a driver to a vehicle using the vehicle's unique plate number."""
    try:
        # If driver_id is provided as an empty string, we treat it as unassigning the driver (None)
        db_driver_value = driver_id if driver_id and driver_id != "None" else None

        response = supabase.table("fleet_vehicles").update({"current_driver_id": db_driver_value}).eq("plate_number", plate_number).execute()
        
        # Optional: If a driver was assigned, update their status to 'On Trip'
        if db_driver_value:
            supabase.table("drivers").update({"work_status": "On Trip"}).eq("id", db_driver_value).execute()
            
        return len(response.data) > 0
    except Exception as e:
        print(f"Database error assigning driver: {e}")
        return False