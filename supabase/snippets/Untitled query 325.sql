-- Ensure the fleet vehicles table tracks project assignments dynamically
ALTER TABLE public.fleet_vehicles 
ADD COLUMN IF NOT EXISTS project_assignment VARCHAR DEFAULT 'General Operations';

-- Create an index to maximize query speeds when the NGO data grows to thousands of rows
CREATE INDEX IF NOT EXISTS idx_vehicles_plate ON public.fleet_vehicles(plate_number);
CREATE INDEX IF NOT EXISTS idx_logs_vehicle_month ON public.fleet_monthly_logs(vehicle_id, log_month_year);