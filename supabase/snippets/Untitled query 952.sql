-- Add a dedicated operational toggle flag to your existing master vehicle table
ALTER TABLE public.fleet_vehicles 
ADD COLUMN is_in_workshop BOOLEAN DEFAULT FALSE;