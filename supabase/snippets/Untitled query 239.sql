-- 1. Create a clean enum for vehicle health metrics
CREATE TYPE vehicle_condition_status AS ENUM ('Good', 'Very Good', 'Excellent', 'Under Maintenance');

-- 2. Master Fleet Table (Tracks vehicle models like Vitz, Hyundai, Suzuki, etc.)
CREATE TABLE fleet_vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plate_number VARCHAR(50) UNIQUE NOT NULL,
    vehicle_model VARCHAR(100) NOT NULL,
    condition_status vehicle_condition_status DEFAULT 'Good',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Monthly Log Tracking Table (Stores the metrics from your spreadsheets)
CREATE TABLE fleet_monthly_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID REFERENCES fleet_vehicles(id) ON DELETE CASCADE,
    log_month_year DATE NOT NULL, -- Format: YYYY-MM-01 (e.g., '2023-11-01')
    starting_km NUMERIC(12,2) DEFAULT 0.0,
    ending_km NUMERIC(12,2) DEFAULT 0.0,
    km_driven NUMERIC(12,2) DEFAULT 0.0,
    fuel_consumption_liters NUMERIC(10,4) DEFAULT 0.0000,
    fuel_cost_etb NUMERIC(12,2) DEFAULT 0.00,
    maintenance_cost_etb NUMERIC(12,2) DEFAULT 0.00,
    fuel_efficiency NUMERIC(10,4), -- Km driven per liter
    working_days INT DEFAULT 26,
    days_available INT DEFAULT 26,
    days_under_maintenance INT DEFAULT 0,
    idle_days INT DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexing for instant data retrieval when parsing reports
CREATE INDEX idx_fleet_logs_vehicle ON fleet_monthly_logs(vehicle_id);
CREATE INDEX idx_fleet_logs_date ON fleet_monthly_logs(log_month_year);