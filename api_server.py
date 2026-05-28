from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import analytics_engine
import maintenance_predictor

app = FastAPI(
    title="NGO Fleet Intelligence API Core",
    description="Production-ready FastAPI engine for predictive logistics routing, workshop scheduling, and telemetry operations.",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# 📋 PYDANTIC DATA VALIDATION MODELS
# ------------------------------------------------------------------
class SimulationRequest(BaseModel):
    km: float
    days: int

class QueryRequest(BaseModel):
    query_type: str

class WorkshopStatusRequest(BaseModel):
    plate_number: str
    is_in_workshop: bool

class DriverAssignmentRequest(BaseModel):
    plate_number: str
    driver_id: str

# ------------------------------------------------------------------
# 📈 TAB 1: FINANCIAL PREDICTIVE SIMULATOR ENDPOINT
# ------------------------------------------------------------------
@app.post("/analyze-fleet")
def analyze_fleet_endpoint(payload: SimulationRequest):
    try:
        rates = {"a": 45.0, "b": 38.0}
        penalties = {"a": 1500.0, "b": 2200.0}
        
        fuel_a = payload.km * rates["a"]
        downtime_a = payload.days * penalties["a"]
        total_a = fuel_a + downtime_a
        
        fuel_b = payload.km * rates["b"]
        downtime_b = payload.days * penalties["b"]
        total_b = fuel_b + downtime_b
        
        return {
            "data": {
                "scenario_a": {"fuel_component": round(fuel_a, 2), "downtime_component": round(downtime_a, 2), "total": round(total_a, 2)},
                "scenario_b": {"fuel_component": round(fuel_b, 2), "downtime_component": round(downtime_b, 2), "total": round(total_b, 2)}
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fleet-query")
def fleet_query_endpoint(payload: QueryRequest):
    """Queries vehicle asset register with a Service Layer to map statuses."""
    try:
        INSPECTION_STATUSES = ["Needs Inspection", "Under Maintenance", "bad"]

        query = analytics_engine.supabase.table("fleet_vehicles").select("*, drivers(full_name)")
        
        if payload.query_type == "Vehicles in Workshop":
            query = query.eq("is_in_workshop", True)
        elif payload.query_type == "Active Maintenance Queue":
            query = query.eq("is_in_workshop", True)
            
        response = query.execute()
        
        raw_data = response.data if response.data else []
        flattened_data = []
        
        for row in raw_data:
            condition = row.get("condition_status")

            if payload.query_type == "Vehicles Needing Inspection":
                if condition not in INSPECTION_STATUSES:
                    continue 

            driver_info = row.get("drivers")
            row["assigned_driver"] = driver_info.get("full_name") if isinstance(driver_info, dict) else "Unassigned"
            row.pop("drivers", None)
            flattened_data.append(row)
            
        return {"data": flattened_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------
# 👨‍✈️ TAB 2 EXTENSION - HARDWARE ASSET & OPERATOR SYNCHRONIZATION
# ------------------------------------------------------------------
@app.get("/api/fleet/plates")
def get_fleet_plates_endpoint():
    try:
        response = analytics_engine.supabase.table("fleet_vehicles").select("id, plate_number").execute()
        raw_data = response.data if response.data else []
        flat_plates = [row["plate_number"] for row in raw_data if "plate_number" in row]
        return {"data": raw_data, "plates": flat_plates, "vehicles": raw_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch vehicle plates: {str(e)}")

@app.get("/api/drivers/available")
def get_available_drivers_endpoint():
    try:
        drivers = analytics_engine.get_available_drivers()
        raw_data = drivers if drivers else []
        flat_names = []
        for driver in raw_data:
            if isinstance(driver, dict):
                name = driver.get("full_name") or driver.get("name") or str(driver)
                flat_names.append(name)
            else:
                flat_names.append(str(driver))
        return {"drivers": raw_data, "data": raw_data, "names": flat_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query driver registry: {str(e)}")

@app.post("/api/fleet/assign-driver")
def assign_driver_endpoint(payload: DriverAssignmentRequest):
    try:
        success = analytics_engine.assign_driver_to_vehicle(payload.plate_number, payload.driver_id)
        if not success:
            raise HTTPException(status_code=400, detail="Assignment rejected.")
        return {"status": "success", "message": f"Driver assignment updated for {payload.plate_number}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Driver linkage failed: {str(e)}")

@app.post("/api/fleet/workshop-status")
@app.post("/api/fleet/workshop")
def update_workshop_status_endpoint(payload: WorkshopStatusRequest):
    try:
        response = analytics_engine.supabase.table("fleet_vehicles") \
            .update({"is_in_workshop": payload.is_in_workshop}) \
            .eq("plate_number", payload.plate_number) \
            .execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Status mutation rejected.")
        return {"status": "success", "message": f"Asset {payload.plate_number} status updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

# ------------------------------------------------------------------
# 🗓️ TAB 3: AUTOMATED SERVICE PROJECTIONS
# ------------------------------------------------------------------
@app.get("/api/maintenance/predictions")
def get_maintenance_predictions_endpoint(interval: int = 5000):
    try:
        return maintenance_predictor.generate_predictions(interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------
# ⛽ TAB 4: FUEL OPTIMIZATION
# ------------------------------------------------------------------
@app.get("/api/analytics/fuel")
def get_fuel_analytics_endpoint():
    try:
        return {"data": analytics_engine.calculate_fuel_efficiency()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def system_health_status():
    return {"status": "healthy", "service": "NGO Fleet Intelligence Core"}