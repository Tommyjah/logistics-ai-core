-- 1. Add the missing current_odometer column to fleet_vehicles
ALTER TABLE public.fleet_vehicles 
ADD COLUMN current_odometer INT8 DEFAULT 0;

-- 2. (Optional) Seed random mileage between 10,000 and 150,000 km 
-- so your dashboard can render data vectors instantly!
UPDATE public.fleet_vehicles
SET current_odometer = floor(random() * (150000 - 10000 + 1) + 10000)::int8;