import pydicom
ds = pydicom.dcmread('sari.dcm')
print(ds) # Menampilkan semua metadata
print(ds.PatientName) # Menampilkan tag tertentu
