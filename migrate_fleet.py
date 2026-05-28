import pandas as pd
import re
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def extract_project(plate_str: str) -> str:
    """Extracts NGO project frameworks from bracketed or appended plate notation"""
    match = re.search(r'\((.*?)\)|,\s*([A-Za-z0-9\s\-]+)', plate_str)
    if match:
        project = match.group(1) if match.group(1) else match.group(2)
        return project.strip().upper()
    # Secondary cleanup fallback
    for keyword in ['CM', 'RAYEE', 'LIWAY', 'BRIDGE', 'HORTI-LIFE', 'L4R', 'NBPE', 'W0RK SHOP']:
        if keyword.lower() in plate_str.lower():
            return keyword
    return "CORE FLEET"

def clean_float(val) -> float:
    if pd.isna(val): return 0.0
    try: return float(val)
    except (ValueError, TypeError): return 0.0

def clean_int(val, default_val=0) -> int:
    if pd.isna(val): return default_val
    try: return int(float(val))
    except (ValueError, TypeError): return default_val

def migrate_excel_data(file_path: str, target_month: str):
    print(f"📖 Ingesting Spreadsheet: {file_path}")
    df = pd.read_excel(file_path, header=4)
    logs_inserted = 0
    
    for index, row in df.iterrows():
        raw_plate = row.get('Plate number/ Project')
        if pd.isna(raw_plate) or str(raw_plate).strip() == '' or 'total' in str(raw_plate).lower():
            continue
            
        plate = str(raw_plate).strip()
        project = extract_project(plate)
        raw_condition = str(row.get('Vehicle condition', 'Good')).strip()
        
        condition_status = "Good"
        if "maintenance" in raw_condition.lower() or "shop" in raw_condition.lower():
            condition_status = "Under Maintenance"
        elif "excellent" in raw_condition.lower():
            condition_status = "Excellent"
        elif "very good" in raw_condition.lower():
            condition_status = "Very Good"

        try:
            v_check = supabase.table("fleet_vehicles").select("id").eq("plate_number", plate).execute()
            if v_check.data:
                vehicle_id = v_check.data[0]['id']
                # Keep condition and project status synchronized
                supabase.table("fleet_vehicles").update({
                    "condition_status": condition_status,
                    "project_assignment": project
                }).eq("id", vehicle_id).execute()
            else:
                v_insert = supabase.table("fleet_vehicles").insert({
                    "plate_number": plate,
                    "vehicle_model": "NGO Operational Vehicle",
                    "condition_status": condition_status,
                    "project_assignment": project
                }).execute()
                vehicle_id = v_insert.data[0]['id']

            starting_km = clean_float(row.get('Starting KM at the beginning of the month'))
            ending_km = clean_float(row.get('Ending Km at the end of the month'))
            km_driven = clean_float(row.get('Km driven during the month'))
            fuel_liters = clean_float(row.get('Monthely fule consumption in liter'))
            fuel_cost = clean_float(row.get('Monthely fuel cost'))
            maint_cost = clean_float(row.get('Total Maintenance cost of the month'))
            
            working_days = clean_int(row.get('#working days of the month'), 26)
            days_avail = clean_int(row.get('vehicle avalible per month'), 26)
            days_maint = clean_int(row.get('# days vehicle under maintenance'), 0)
            idle_days = clean_int(row.get('# of Idle days of the month'), 0)

            fuel_efficiency = km_driven / fuel_liters if fuel_liters > 0 else 0

            supabase.table("fleet_monthly_logs").insert({
                "vehicle_id": vehicle_id,
                "log_month_year": target_month,
                "starting_km": starting_km,
                "ending_km": ending_km,
                "km_driven": km_driven,
                "fuel_consumption_liters": fuel_liters,
                "fuel_cost_etb": fuel_cost,
                "maintenance_cost_etb": maint_cost,
                "fuel_efficiency": fuel_efficiency,
                "working_days": working_days,
                "days_available": days_avail,
                "days_under_maintenance": days_maint,
                "idle_days": idle_days
            }).execute()
            logs_inserted += 1
            
        except Exception as e:
            print(f"⚠️ Row Ingestion Error {index}: {str(e)}")

    print(f"🏁 System Ready: Linked {logs_inserted} records with complete Project Trackers.")

if __name__ == "__main__":
    migrate_excel_data("November Fleet Summery.xlsx", "2023-11-01")