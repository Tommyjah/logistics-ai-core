-- 1. Create the Drivers Registry Table
CREATE TABLE IF NOT EXISTS public.drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    license_number TEXT UNIQUE NOT NULL,
    phone_number TEXT,
    work_status TEXT NOT NULL DEFAULT 'Available' CHECK (work_status IN ('Available', 'On Trip', 'On Leave', 'Suspended')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 2. Add Driver Assignment Linkage to Your Existing Fleet Table
ALTER TABLE public.fleet_vehicles 
ADD COLUMN IF NOT EXISTS current_driver_id UUID REFERENCES public.drivers(id) ON DELETE SET NULL;

-- 3. Create the Telematics Tracking Stream Table (High-frequency tracking metrics)
CREATE TABLE IF NOT EXISTS public.telematics_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id UUID NOT NULL REFERENCES public.fleet_vehicles(id) ON DELETE CASCADE,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    current_speed_kmh NUMERIC(5, 2) DEFAULT 0.0,
    fuel_level_percent NUMERIC(5, 2),
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 4. Create Performance Indexes for Telemetry Lookup Optimization
-- This ensures that when the map looks up a vehicle's path, queries return in milliseconds
CREATE INDEX IF NOT EXISTS idx_telematics_vehicle_time 
ON public.telematics_logs (vehicle_id, logged_at DESC);