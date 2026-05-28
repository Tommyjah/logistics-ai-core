-- 1. Create the fuel logs tracking table
CREATE TABLE public.fleet_fuel_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vehicle_id UUID REFERENCES public.fleet_vehicles(id) ON DELETE CASCADE,
    fuel_date DATE DEFAULT CURRENT_DATE,
    liters_fueled NUMERIC(10, 2) NOT NULL,
    cost_etb NUMERIC(10, 2) NOT NULL,
    odometer_reading INT8 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Seed realistic historical fuel logs for your existing 41 vehicles
-- This inserts 3 mock fueling entries per vehicle over the last month
INSERT INTO public.fleet_fuel_logs (vehicle_id, fuel_date, liters_fueled, cost_etb, odometer_reading)
SELECT 
    id,
    current_date - (val || ' days')::INTERVAL as fuel_date,
    round((45 + random() * 35)::numeric, 2) as liters_fueled, -- 45 to 80 Liters per fill
    0 as cost_etb, -- Will calculate dynamically below
    (current_odometer - (val * 120) - floor(random() * 50))::int8 as odometer_reading
FROM public.fleet_vehicles
CROSS JOIN (VALUES (5), (15), (25)) AS days(val);

-- 3. Set realistic ETB cost based on ~105 ETB per liter 
UPDATE public.fleet_fuel_logs
SET cost_etb = liters_fueled * 105.25;