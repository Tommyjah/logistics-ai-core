import os
import pandas as pd
from datetime import datetime, timedelta
# Reusing the authenticated client instance from analytics_engine to fix the 401 API key error
from analytics_engine import supabase

def generate_predictions(service_interval_km=5000):
    """
    Calculates the predicted next maintenance date for all vehicles 
    based on historical monthly driving utilization patterns.
    Matches the naming expected by the FastAPI api_server layer.
    """
    try:
        # 1. Fetch historical monthly logs to find driving velocity patterns
        logs_resp = supabase.table("fleet_monthly_logs").select("vehicle_id, km_driven").execute()
        logs_data = logs_resp.data if logs_resp.data else []
        logs_df = pd.DataFrame(logs_data)
        
        # 2. Fetch current real-time state of the vehicle assets
        vehicles_resp = supabase.table("fleet_vehicles").select("id, plate_number, current_odometer").execute()
        vehicles_data = vehicles_resp.data if vehicles_resp.data else []
        vehicles_df = pd.DataFrame(vehicles_data)
        
        # Fallback guard: If no vehicles exist, return an empty array safely without raising errors
        if vehicles_df.empty:
            return []
            
        # Calculate daily usage matrix. If no logs exist yet, daily_usage series remains empty
        daily_usage = pd.Series(dtype=float)
        if not logs_df.empty and 'km_driven' in logs_df.columns:
            logs_df['km_driven'] = pd.to_numeric(logs_df['km_driven']).fillna(0)
            daily_usage = logs_df.groupby('vehicle_id')['km_driven'].mean() / 30.0
        
        predictions = []
        current_date = datetime.now()
        
        for _, vehicle in vehicles_df.iterrows():
            v_id = vehicle['id']
            current_km = float(vehicle.get('current_odometer', 0) or 0)
            
            # Determine next target service ceiling (e.g., if at 12,300km and interval is 5000, target is 15,000km)
            next_service_target = ((current_km // service_interval_km) + 1) * service_interval_km
            km_remaining = max(0.0, next_service_target - current_km)
            
            # Extract driving velocity, fallback to standard 50km/day if logs are missing
            km_per_day = daily_usage.get(v_id, 50.0)
            if pd.isna(km_per_day) or km_per_day <= 0: 
                km_per_day = 50.0 
                
            days_remaining = int(km_remaining / km_per_day)
            predicted_date = current_date + timedelta(days=days_remaining)
            
            predictions.append({
                "plate_number": vehicle['plate_number'],
                "current_odometer": current_km,
                "next_service_ceil": next_service_target,
                "km_remaining": km_remaining,
                "predicted_maintenance_date": predicted_date.strftime("%Y-%m-%d"),
                "days_countdown": days_remaining
            })
            
        return predictions
    except Exception as e:
        print(f"Prediction Engine Internal Error: {e}")
        return []