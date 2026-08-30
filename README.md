# DICOM Generator

Generator file **DICOM dummy** & data **radiology worklist** untuk kebutuhan
testing, dilengkapi **web UI** untuk menentukan jumlah file dan rentang tanggal
tanpa command line.

## Fitur

- **Web UI** — atur jumlah DICOM per tanggal + rentang tanggal, pantau progress
  secara real-time, lihat hasil dalam tabel, download per file / semua (`.zip`) / JSON.
- **Engine batch** — generate N file untuk setiap tanggal dalam rentang tertentu.
- **Data dummy realistis** — nama pasien, accession number, AE title, lokasi,
  rumah sakit, dan jadwal acak (modality CT/MR/US/DX).
- **Ekspor JSON** — format siap insert ke tabel radiology (`dicom_data.json`).
- **Skrip CLI** — tetap tersedia di `scripts/` untuk otomasi.

## Struktur Folder

```
pythondicom/
├── run.py                       # Entry point web UI (python run.py)
├── dicom_generator/             # Package utama
│   ├── core.py                  #   Pembuatan file .dcm level rendah
│   ├── engine.py                #   Engine batch generate
│   ├── exporter.py              #   Ekspor .dcm → JSON radiology
│   ├── fakedata.py              #   Pool data dummy (nama, RS, lokasi, dll.)
│   ├── paths.py                 #   Resolusi path project
│   └── web/                     #   Web UI (FastAPI + frontend statis)
│       ├── app.py
│       └── static/
├── scripts/                     # Skrip CLI / legacy
├── data/                        # Template metadata (metadata.json)
├── docs/                        # Dokumentasi detail (DOKUMENTASI.md)
└── output/                      # Semua file hasil generate (tidak disimpan di git)
```

## Persyaratan

- Python **3.10+**
- Dependencies: `pydicom`, `numpy`, `Pillow`, `fastapi`, `uvicorn`

## Cara Menjalankan Aplikasi

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

atau install sebagai package (menyediakan perintah `dicomgen-web`):

```bash
pip install -e .
```

### 2. Jalankan web UI

```bash
python run.py
```

Browser otomatis membuka **http://127.0.0.1:8000**.

Alternatif lain:

```bash
python -m dicom_generator          # sama dengan run.py
uvicorn dicom_generator.web.app:app --host 127.0.0.1 --port 8000   # manual
dicomgen-web                       # jika install via pip install -e .
```

Port bisa diubah lewat environment variable:

```bash
# PowerShell
$env:PORT = "9000"; python run.py
```

### 3. Gunakan UI

1. Isi **Jumlah DICOM per tanggal** (contoh: 10 file/tanggal).
2. Pilih **rentang tanggal jadwal** (dari–sampai). Total file ditampilkan
   langsung: `tanggal × jumlah per tanggal`.
3. (Opsional) buka **Detail data** untuk mengatur modality, lokasi, rumah sakit,
   penjamin, jenis kelamin, dan folder output.
4. Klik **Generate DICOM** — progress bar menunjukkan proses per file dan bisa
   dibatalkan.
5. Setelah selesai: lihat hasil di tabel (search + filter tanggal), download
   per file, **Unduh semua (.zip)**, atau ekspor **JSON**.

File hasil disimpan di `output/generated_dicoms/` beserta `dicom_data.json`.

## Skrip CLI

| Skrip | Fungsi |
|-------|--------|
| `python scripts/create_dicom.py --out file.dcm --patient "Nama^Pasien" --id 123` | Buat satu file DICOM (metadata dari `data/metadata.json`) |
| `python scripts/batch_dicom.py 10 3` | 10 file/hari untuk hari ini + 3 hari ke belakang |
| `python scripts/export_json.py [folder]` | Ekspor semua `.dcm` di folder ke JSON radiology |
| `python scripts/read_metadata.py file.dcm` | Tampilkan semua tag DICOM |
| `python scripts/submit_worklist.py` | POST record worklist ke API (butuh `DICOM_API_KEY`) |
| `python scripts/generate_batch.py` | Satu DICOM per location (legacy) |
| `python scripts/generate_new_batch.py` / `generate_new_unique.py` / `generate_dicoms.py` | Generator dummy legacy |

## REST API Web UI

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/api/options` | Opsi form + limit |
| GET | `/api/summary?dir=` | Statistik folder output |
| POST | `/api/generate` | Mulai generate → `job_id` |
| GET | `/api/jobs/{job_id}` | Progress job |
| POST | `/api/jobs/{job_id}/cancel` | Batalkan job |
| GET | `/api/records?dir=` | Isi `dicom_data.json` |
| GET | `/api/download/{filename}?dir=` | Download satu `.dcm` |
| GET | `/api/download-zip?dir=` | Download semua `.dcm` (zip) |
| POST | `/api/open-folder?dir=` | Buka folder output |

## Dokumentasi

Detail tag DICOM, format JSON radiology, dan contoh hasil ada di
[docs/DOKUMENTASI.md](docs/DOKUMENTASI.md).
