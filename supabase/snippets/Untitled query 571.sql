-- Seed sample drivers
INSERT INTO public.drivers (full_name, license_number, phone_number, work_status)
VALUES 
('Abebe Bikila', 'DL-ETH-99211-A', '+251 911 223344', 'Available'),
('Aster Aweke', 'DL-ETH-88432-B', '+251 912 556677', 'Available')
ON CONFLICT (license_number) DO NOTHING;