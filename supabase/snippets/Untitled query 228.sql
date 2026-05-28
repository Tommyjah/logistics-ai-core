INSERT INTO public.drivers (full_name, license_number, phone_number, work_status)
VALUES 
('Tadesse Alemu', 'DL-ETH-11223-T', '+251 911 112233', 'Available'),
('Selamawit Daniel', 'DL-ETH-44556-S', '+251 911 445566', 'Available'),
('Yohannes Tekle', 'DL-ETH-77889-Y', '+251 911 778899', 'Available'),
('Almaz Yosef', 'DL-ETH-33445-A', '+251 911 334455', 'Available'),
('Bekele Kebede', 'DL-ETH-55667-B', '+251 911 556677', 'Available'),
('Eleni Gebru', 'DL-ETH-88990-E', '+251 911 889900', 'Available')
ON CONFLICT (license_number) DO NOTHING;