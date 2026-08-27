# Dokumentasi — Pembuatan File DICOM & JSON untuk Radiology

## Daftar Isi

1. [Struktur Folder](#struktur-folder)
2. [Alur Kerja](#alur-kerja)
3. [Langkah 1 — Siapkan Metadata (metadata.json)](#langkah-1--siapkan-metadata)
4. [Langkah 2 — Buat File DICOM](#langkah-2--buat-file-dicom)
5. [Langkah 3 — Ekspor ke JSON untuk Insert Tabel Radiology](#langkah-3--ekspor-ke-json)
6. [Referensi Field JSON Radiology](#referensi-field-json-radiology)
7. [Daftar Location yang Didukung](#daftar-location)
8. [Contoh Hasil Akhir](#contoh-hasil-akhir)

---

## Struktur Folder

```
pythondicom/
├── metadata.json        # Template metadata untuk tag DICOM
├── create-dicom.py      # Core library: buat file .dcm dari array/gambar
├── generate_batch.py    # Script batch: buat DICOM per location
├── export_text.py       # Script: ekspor .dcm → .json (format tabel radiology)
├── readmetadata.py      # Utility: baca metadata dari file .dcm
└── *.dcm / *.json       # Output yang dihasilkan
```

---

## Alur Kerja

```
metadata.json ──► generate_batch.py ──► *.dcm (file DICOM)
                                           │
                                           ▼
                                    export_text.py ──► *.json (siap insert ke tabel radiology)
```

---

## Langkah 1 — Siapkan Metadata

File `metadata.json` mendefinisikan tag DICOM yang akan diterapkan ke file `.dcm`.

### Format

```json
{
    "Tags": {
        "ReferringPhysicianName": "DR Josh",
        "NameOfPhysiciansReadingStudy": "Radiologist 1raazs",
        "OperatorsName": "Technician",
        "InstitutionalDepartmentName": "Radiologi",
        "BodyPartExamined": "CT",
        "PatientID": "20262205002",
        "PatientName": "PATIENT 052202. MR",
        "PatientSex": "M",
        "PatientBirthDate": "19950110",
        "AccessionNumber": "ACC-20262205002",
        "RequestedProcedureID": "REQ-20262205002",
        "RequestedProcedureDescription": "CT",
        "ScheduledProcedureStepSequence": [
            {
                "Modality": "CT",
                "ScheduledProcedureStepStartDate": "20260522",
                "ScheduledProcedureStepStartTime": "100000",
                "ScheduledStationAETitle": "CT01",
                "ScheduledProcedureStepID": "SPS-20262205002",
                "ScheduledProcedureStepDescription": "CT",
                "ScheduledStationName": "RAD-ROOM2",
                "ScheduledProcedureStepLocation": "RADIOLOGI"
            }
        ]
    }
}
```

### Keterangan Tag

| Tag | VR | Format | Contoh | Keterangan |
|-----|-----|--------|--------|------------|
| `ReferringPhysicianName` | PN | `Nama^Belakang` | `DR Josh` | Dokter pengirim |
| `NameOfPhysiciansReadingStudy` | PN | string | `Radiologist 1raazs` | Radiologis yang membaca |
| `OperatorsName` | PN | string | `Technician` | Operator mesin |
| `InstitutionalDepartmentName` | LO | string | `Radiologi` | Departemen |
| `BodyPartExamined` | CS | kode | `CT` / `MR` / `XR` / `US` | Bagian tubuh / tipe pemeriksaan |
| `PatientID` | LO | string | `20262205002` | ID pasien |
| `PatientName` | PN | `Nama^Belakang` | `PATIENT 052202. MR` | Nama pasien |
| `PatientSex` | CS | `M` / `F` / `O` | `M` | Jenis kelamin |
| `PatientBirthDate` | DA | `YYYYMMDD` | `19950110` | Tanggal lahir |
| `AccessionNumber` | SH | string | `ACC-20262205002` | Nomor akses |
| `RequestedProcedureID` | SH | string | `REQ-20262205002` | ID prosedur |
| `RequestedProcedureDescription` | LO | string | `CT` | Deskripsi prosedur |
| `ScheduledProcedureStepSequence` | SQ | array of dict | (lihat bawah) | Jadwal langkah prosedur |

### Sub-tag `ScheduledProcedureStepSequence`

| Tag | VR | Format | Contoh | Keterangan |
|-----|-----|--------|--------|------------|
| `Modality` | CS | kode | `CT` / `MR` / `DX` / `US` | Modalitas pemeriksaan |
| `ScheduledProcedureStepStartDate` | DA | `YYYYMMDD` | `20260522` | Tanggal jadwal |
| `ScheduledProcedureStepStartTime` | TM | `HHMMSS` | `100000` | Waktu jadwal |
| `ScheduledStationAETitle` | AE | string (max 16) | `CT01` | AE Title stasiun |
| `ScheduledProcedureStepID` | SH | string | `SPS-20262205002` | ID langkah prosedur |
| `ScheduledProcedureStepDescription` | LO | string | `CT` | Deskripsi langkah |
| `ScheduledStationName` | SH | string (max 16) | `RAD-ROOM2` | Nama stasiun |
| `ScheduledProcedureStepLocation` | SH | string (max 16) | `RADIOLOGI` | Lokasi pemeriksaan |

---

## Langkah 2 — Buat File DICOM

### Opsi A — Satu file dengan CLI

```bash
python create-dicom.py --out pasien001.dcm --patient "Budi^Santoso" --id 123456 --metadata metadata.json
```

Parameter lengkap:

| Parameter | Wajib | Default | Keterangan |
|-----------|-------|---------|------------|
| `--out` | Ya | - | Nama file output (.dcm) |
| `--from-image` | Tidak | - | Path gambar (png/jpg), jika kosong = gambar sintetis |
| `--width` | Tidak | 256 | Lebar gambar sintetis |
| `--height` | Tidak | 256 | Tinggi gambar sintetis |
| `--bits` | Tidak | 8 | Kedalaman bit (8 atau 16) |
| `--patient` | Tidak | `Anon^Patient` | Nama pasien |
| `--id` | Tidak | `0000` | ID pasien |
| `--metadata` | Tidak | - | Path file JSON atau string JSON |

### Opsi B — Batch per Location

```bash
python generate_batch.py
```

Script ini akan otomatis membuat 4 file DICOM, satu untuk setiap location:

| Location | Nama File Output | AE Title | Station Name |
|----------|-----------------|----------|--------------|
| IGD | `IGD_<PatientID>.dcm` | `IGD01` | `RAD-IGD` |
| ICU | `ICU_<PatientID>.dcm` | `ICU01` | `RAD-ICU` |
| Rawat Inap | `Rawat_Inap_<PatientID>.dcm` | `RAW01` | `RAD-RAWAT_INAP` |
| Umum / Poliklinik | `Umum___Poliklinik_<PatientID>.dcm` | `UMU01` | `RAD-UMUM_/_POLIKLINIK` |

Data pasien, dokter, dan tanggal di-generate secara random. Tanggal default menggunakan variabel `TODAY_DATE` dan `TODAY_TIME` di dalam script.

### Mengubah Tanggal

Edit baris berikut di `generate_batch.py`:

```python
TODAY_DATE = "20260618"   # Format: YYYYMMDD
TODAY_TIME = "100000"     # Format: HHMMSS
```

### Menambah Location Baru

Edit list `LOCATIONS` di `generate_batch.py`:

```python
LOCATIONS = ["IGD", "ICU", "Rawat Inap", "Umum / Poliklinik", "VK", "UGD"]
```

---

## Langkah 3 — Ekspor ke JSON

```bash
python export_text.py
```

Script ini membaca semua file `*.dcm` di folder dan mengkonversi masing-masing ke file `.json` dengan format siap insert ke tabel radiology.

Setiap file `NAMA.dcm` akan menghasilkan `NAMA.json`.

---

## Referensi Field JSON Radiology

Format JSON output yang dihasilkan `export_text.py`:

```json
{
    "PatientID": "423906",
    "PatientName": "Rudi^Hidayat",
    "PatientSex": "M",
    "PatientBirthDate": "20010511",
    "AccessionNumber": "ACC-180024",
    "RequestedProcedureID": "REQ-641396",
    "RequestedProcedureDescription": "ICU",
    "Modality": "US",
    "ScheduledDate": "20260602",
    "ScheduledTime": "100000",
    "ScheduledStationAETitle": "ICU01",
    "ReferringPhysicianName": "dr Rani Siregar",
    "Location": "ICU",
    "Department": "Radiologi",
    "Institution": "RS Dummy",
    "Guarantor": "BPJS"
}
```

### Mapping Field → Sumber DICOM Tag

| Field JSON | Sumber DICOM Tag | Keterangan |
|------------|-----------------|------------|
| `PatientID` | `(0010,0020) PatientID` | ID unik pasien |
| `PatientName` | `(0010,0010) PatientName` | Nama pasien |
| `PatientSex` | `(0010,0040) PatientSex` | M / F / O |
| `PatientBirthDate` | `(0010,0030) PatientBirthDate` | YYYYMMDD |
| `AccessionNumber` | `(0008,0050) AccessionNumber` | Nomor akses |
| `RequestedProcedureID` | `(0040,1001) RequestedProcedureID` | ID prosedur |
| `RequestedProcedureDescription` | `(0032,1060) RequestedProcedureDescription` | Deskripsi prosedur |
| `Modality` | `(0008,0060) Modality` dari ScheduledProcedureStepSequence | CT / MR / DX / US |
| `ScheduledDate` | `(0040,0002) ScheduledProcedureStepStartDate` | YYYYMMDD |
| `ScheduledTime` | `(0040,0003) ScheduledProcedureStepStartTime` | HHMMSS |
| `ScheduledStationAETitle` | `(0040,0001) ScheduledStationAETitle` | AE Title stasiun |
| `ReferringPhysicianName` | `(0008,0090) ReferringPhysicianName` | Dokter pengirim |
| `Location` | `(0040,0011) ScheduledProcedureStepLocation` | Lokasi pemeriksaan |
| `Department` | `(0008,1040) InstitutionalDepartmentName` | Departemen |
| `Institution` | `(0008,0080) InstitutionName` | Nama rumah sakit |
| `Guarantor` | Hardcoded | Penjamin (default: BPJS) |

### SQL Insert Contoh

```sql
INSERT INTO radiology (
    patient_id, patient_name, patient_sex, patient_birth_date,
    accession_number, requested_procedure_id, requested_procedure_description,
    modality, scheduled_date, scheduled_time, scheduled_station_ae_title,
    referring_physician_name, location, department, institution, guarantor
) VALUES (
    '423906', 'Rudi^Hidayat', 'M', '2001-05-11',
    'ACC-180024', 'REQ-641396', 'ICU',
    'US', '2026-06-02', '10:00:00', 'ICU01',
    'dr Rani Siregar', 'ICU', 'Radiologi', 'RS Dummy', 'BPJS'
);
```

---

## Daftar Location

| Location | Keterangan | AE Title | Station Name |
|----------|------------|----------|--------------|
| IGD | Instalasi Gawat Darurat | `IGD01` | `RAD-IGD` |
| ICU | Intensive Care Unit | `ICU01` | `RAD-ICU` |
| Rawat Inap | Pasien rawat inap | `RAW01` | `RAD-RAWAT_INAP` |
| Umum / Poliklinik | Poliklinik umum | `UMU01` | `RAD-UMUM_/_POLIKLINIK` |

---

## Contoh Hasil Akhir

### IGD

**File DICOM:** `IGD_188810.dcm`

**File JSON:** `IGD_188810.json`
```json
{
    "PatientID": "188810",
    "PatientName": "Ahmad^Wulandari",
    "PatientSex": "F",
    "PatientBirthDate": "19591116",
    "AccessionNumber": "ACC-730235",
    "RequestedProcedureID": "REQ-721379",
    "RequestedProcedureDescription": "IGD",
    "Modality": "MR",
    "ScheduledDate": "20260602",
    "ScheduledTime": "100000",
    "ScheduledStationAETitle": "IGD01",
    "ReferringPhysicianName": "dr Ahmad Siregar",
    "Location": "IGD",
    "Department": "Radiologi",
    "Institution": "RS Dummy",
    "Guarantor": "BPJS"
}
```

### ICU

**File DICOM:** `ICU_423906.dcm`

**File JSON:** `ICU_423906.json`
```json
{
    "PatientID": "423906",
    "PatientName": "Rudi^Hidayat",
    "PatientSex": "M",
    "PatientBirthDate": "20010511",
    "AccessionNumber": "ACC-180024",
    "RequestedProcedureID": "REQ-641396",
    "RequestedProcedureDescription": "ICU",
    "Modality": "US",
    "ScheduledDate": "20260602",
    "ScheduledTime": "100000",
    "ScheduledStationAETitle": "ICU01",
    "ReferringPhysicianName": "dr Rani Siregar",
    "Location": "ICU",
    "Department": "Radiologi",
    "Institution": "RS Dummy",
    "Guarantor": "BPJS"
}
```

### Rawat Inap

**File DICOM:** `Rawat_Inap_114879.dcm`

**File JSON:** `Rawat_Inap_114879.json`
```json
{
    "PatientID": "114879",
    "PatientName": "Nita^Wibowo",
    "PatientSex": "M",
    "PatientBirthDate": "19571015",
    "AccessionNumber": "ACC-772223",
    "RequestedProcedureID": "REQ-424977",
    "RequestedProcedureDescription": "Rawat Inap",
    "Modality": "CT",
    "ScheduledDate": "20260602",
    "ScheduledTime": "100000",
    "ScheduledStationAETitle": "RAW01",
    "ReferringPhysicianName": "dr Rani Kusuma",
    "Location": "Rawat Inap",
    "Department": "Radiologi",
    "Institution": "RS Dummy",
    "Guarantor": "BPJS"
}
```

### Umum / Poliklinik

**File DICOM:** `Umum___Poliklinik_238360.dcm`

**File JSON:** `Umum___Poliklinik_238360.json`
```json
{
    "PatientID": "238360",
    "PatientName": "Dewi^Permadi",
    "PatientSex": "M",
    "PatientBirthDate": "20010320",
    "AccessionNumber": "ACC-281467",
    "RequestedProcedureID": "REQ-288302",
    "RequestedProcedureDescription": "Umum / Poliklinik",
    "Modality": "MR",
    "ScheduledDate": "20260602",
    "ScheduledTime": "100000",
    "ScheduledStationAETitle": "UMU01",
    "ReferringPhysicianName": "dr Ahmad Hartono",
    "Location": "Umum / Poliklinik",
    "Department": "Radiologi",
    "Institution": "RS Dummy",
    "Guarantor": "BPJS"
}
```

---

## Quick Start

```bash
# 1. Buat DICOM batch (4 location)
python generate_batch.py

# 2. Ekspor ke JSON untuk insert tabel radiology
python export_text.py

# 3. (Opsional) Buat single DICOM dengan metadata custom
python create-dicom.py --out custom.dcm --patient "Siti^Kusuma" --id 999888 --metadata metadata.json
```

---

## Dependency

```
pydicom
numpy
Pillow
```

Install:
```bash
pip install pydicom numpy Pillow
```
