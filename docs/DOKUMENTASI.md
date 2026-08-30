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
9. [UI Web — DICOM Generator](#ui-web--dicom-generator)

---

## Struktur Folder

```
pythondicom/
├── run.py                       # Entry point web UI (python run.py)
├── dicom_generator/             # Package utama
│   ├── core.py                  #   buat file .dcm dari array/gambar
│   ├── engine.py                #   engine batch generate (jumlah × rentang tanggal)
│   ├── exporter.py              #   ekspor .dcm → .json (format tabel radiology)
│   ├── fakedata.py              #   pool data dummy (nama, RS, lokasi, dll.)
│   ├── paths.py                 #   resolusi path project
│   └── web/                     #   web UI (FastAPI + frontend statis)
├── scripts/                     # Skrip CLI / utility
├── data/metadata.json           # Template metadata untuk tag DICOM
└── output/                      # Semua file .dcm / .json hasil generate
```

---

## Alur Kerja

```
data/metadata.json ──► scripts/create_dicom.py / web UI ──► output/*.dcm
                                                                │
                                                                ▼
                                              scripts/export_json.py ──► *.json
                                              (siap insert ke tabel radiology)
```

> Cara termudah: jalankan web UI (`python run.py`) — jumlah file, rentang
> tanggal, dan ekspor JSON bisa diatur langsung dari browser.

---

## Langkah 1 — Siapkan Metadata

File `data/metadata.json` mendefinisikan tag DICOM yang akan diterapkan ke file `.dcm`.

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
python scripts/create_dicom.py --out pasien001.dcm --patient "Budi^Santoso" --id 123456 --metadata data/metadata.json
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
| `--metadata` | Tidak | `data/metadata.json` | Path file JSON atau string JSON |

### Opsi B — Batch per Location

```bash
python scripts/generate_batch.py
```

Script ini akan otomatis membuat 4 file DICOM, satu untuk setiap location:

| Location | Nama File Output | AE Title | Station Name |
|----------|-----------------|----------|--------------|
| IGD | `IGD_<PatientID>.dcm` | `IGD01` | `RAD-IGD` |
| ICU | `ICU_<PatientID>.dcm` | `ICU01` | `RAD-ICU` |
| Rawat Inap | `Rawat_Inap_<PatientID>.dcm` | `RAW01` | `RAD-RAWAT_INAP` |
| Umum / Poliklinik | `Umum___Poliklinik_<PatientID>.dcm` | `UMU01` | `RAD-UMUM_/_POLIKLINIK` |

Data pasien, dokter, dan tanggal di-generate secara random. Tanggal default menggunakan variabel `TODAY_DATE` dan `TODAY_TIME` di dalam `scripts/generate_batch.py`. File hasil ditulis ke `output/generated_dicoms/`.

### Mengubah Tanggal

Edit baris berikut di `scripts/generate_batch.py`:

```python
TODAY_DATE = "20260618"   # Format: YYYYMMDD
TODAY_TIME = "100000"     # Format: HHMMSS
```

### Menambah Location Baru

Edit list `LOCATIONS` di `scripts/generate_batch.py`:

```python
LOCATIONS = ["IGD", "ICU", "Rawat Inap", "Umum / Poliklinik", "VK", "UGD"]
```

---

## Langkah 3 — Ekspor ke JSON

```bash
python scripts/export_json.py [folder]     # default: output/generated_dicoms
```

Script ini membaca semua file `*.dcm` di folder dan mengkonversi masing-masing ke file `.json` dengan format siap insert ke tabel radiology.

Setiap file `NAMA.dcm` akan menghasilkan `NAMA.json`.

---

## Referensi Field JSON Radiology

Format JSON output yang dihasilkan `scripts/export_json.py` (modul `dicom_generator.exporter`):

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
# 0. Install dependencies
pip install -r requirements.txt

# 1. Jalankan web UI (cara termudah) — browser terbuka di http://127.0.0.1:8000
python run.py

# 2. Alternatif CLI: buat DICOM batch (4 location)
python scripts/generate_batch.py

# 3. Ekspor ke JSON untuk insert tabel radiology
python scripts/export_json.py

# 4. (Opsional) Buat single DICOM dengan metadata custom
python scripts/create_dicom.py --out custom.dcm --patient "Siti^Kusuma" --id 999888 --metadata data/metadata.json
```

---

## UI Web — DICOM Generator

Web UI untuk membuat file DICOM tanpa command line. Menyediakan kontrol
**jumlah DICOM per tanggal** dan **rentang tanggal** file DICOM.

### Menjalankan

```bash
python run.py
```

Browser otomatis membuka `http://127.0.0.1:8000`. Alternatif:

```bash
python -m dicom_generator
uvicorn dicom_generator.web.app:app --host 127.0.0.1 --port 8000
```

Port bisa diubah lewat environment variable `PORT` (default 8000).

### Fitur utama

- **Jumlah per tanggal** — berapa file DICOM yang dibuat untuk setiap tanggal (1–200).
- **Rentang tanggal** — tanggal mulai & selesai. File dibuat untuk setiap tanggal
  di rentang tersebut. Ada tombol cepat: Hari ini, 7 hari terakhir, 30 hari terakhir.
- **Preview total** — ringkasan real-time (tanggal × jumlah = total file).
- **Detail data (opsional)** — modality (CT/MR/US/DX/acak), location, institution,
  department, guarantor, jenis kelamin pasien, dan gaya gambar (gradient/noise).
- **Progress bar live** — pantau proses generate per file, bisa dibatalkan.
- **Hasil & download** — tabel hasil, search + filter tanggal, download per file,
  download semua sebagai `.zip`, ekspor `dicom_data.json`, dan tombol buka folder.

### Konfigurasi Generate (API)

| Field | Wajib | Default | Keterangan |
|-------|-------|---------|------------|
| `count_per_date` | Ya | 10 | Jumlah DICOM per tanggal (1–200) |
| `start_date` | Ya | — | Tanggal mulai (`YYYY-MM-DD`) |
| `end_date` | Ya | — | Tanggal selesai (`YYYY-MM-DD`) |
| `modality` | Tidak | `CT` | `CT`/`MR`/`US`/`DX`/`random` |
| `location` | Tidak | `random` | Lokasi atau `random` |
| `institution` | Tidak | `random` | Nama RS atau `random` |
| `guarantor` | Tidak | `BPJS` | Penjamin atau `random` |
| `patient_sex` | Tidak | `random` | `M`/`F`/`random` |
| `image_style` | Tidak | `gradient` | `gradient`/`noise` |
| `output_dir` | Tidak | `generated_dicoms` | Folder output (di bawah `output/`) |

### API endpoints

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/options` | Opsi dropdown + limit |
| GET | `/api/summary?dir=` | Statistik folder output |
| POST | `/api/generate` | Mulai generate (body JSON config), mengembalikan `job_id` |
| GET | `/api/jobs/{job_id}` | Status/progress job |
| POST | `/api/jobs/{job_id}/cancel` | Batalkan job |
| GET | `/api/jobs/{job_id}/results` | Data hasil (tabel) |
| GET | `/api/records?dir=` | Baca `dicom_data.json` dari folder output |
| GET | `/api/download/{filename}?dir=` | Download satu file `.dcm` |
| GET | `/api/download-zip?dir=` | Download semua `.dcm` sebagai zip |
| POST | `/api/open-folder?dir=` | Buka folder output di file manager |

---

## Dependency

```
pydicom
numpy
Pillow
fastapi
uvicorn
```

Install:
```bash
pip install -r requirements.txt
```
