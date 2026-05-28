SELECT 
    v.plate_number,
    v.condition_status as vehicle_status,
    l.km_driven,
    l.fuel_consumption_liters,
    ROUND(l.fuel_efficiency, 2) as km_per_liter,
    l.fuel_cost_etb,
    l.maintenance_cost_etb,
    (l.fuel_cost_etb + l.maintenance_cost_etb) as total_operating_cost_etb,
    l.days_under_maintenance,
    l.idle_days
FROM fleet_monthly_logs l
JOIN fleet_vehicles v ON l.vehicle_id = v.id
ORDER BY total_operating_cost_etb DESC;