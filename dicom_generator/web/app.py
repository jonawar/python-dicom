"""DICOM Generator web UI — FastAPI backend.

Run:  python run.py  /  python -m dicom_generator  /  uvicorn dicom_generator.web.app:app
"""
import json
import os
import tempfile
import threading
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from dicom_generator import fakedata
from dicom_generator.engine import GenConfig
from dicom_generator.engine import generate as engine_generate
from dicom_generator.paths import resolve_output_dir

MAX_PER_DATE = 200
MAX_DATES = 366
MAX_TOTAL = 3000

app = FastAPI(title="DICOM Generator UI", version="1.0.0")

JOBS = {}
JOBS_LOCK = threading.Lock()


class JobCancelled(Exception):
    pass


class GenerateRequest(BaseModel):
    count_per_date: int = Field(10, ge=1, le=MAX_PER_DATE)
    start_date: str
    end_date: str
    modality: str = "CT"
    location: str = "random"
    institution: str = "random"
    department: str = "Radiologi"
    guarantor: str = "BPJS"
    patient_sex: str = "random"
    image_style: str = "gradient"
    output_dir: str = "generated_dicoms"


def _new_job(req: GenerateRequest, total: int):
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "status": "running",
        "total": total,
        "done": 0,
        "percent": 0,
        "current": "",
        "message": "Memulai...",
        "error": None,
        "started_at": time.time(),
        "finished_at": None,
        "cancelled": False,
        "records": [],
        "files": [],
        "output_dir": req.output_dir,
        "config": req.model_dump(),
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
    return job_id, job


def _outdir(name: str) -> Path:
    try:
        return resolve_output_dir(name)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/options")
def options():
    return {
        "modalities": fakedata.MODALITIES,
        "locations": fakedata.LOCATIONS,
        "institutions": fakedata.INSTITUTIONS,
        "departments": fakedata.DEPARTMENTS,
        "guarantors": fakedata.GUARANTORS,
        "limits": {"max_per_date": MAX_PER_DATE, "max_dates": MAX_DATES,
                   "max_total": MAX_TOTAL},
    }


@app.get("/api/summary")
def summary(dir: str = "generated_dicoms"):
    base = _outdir(dir)
    total_files = 0
    total_size = 0
    for f in base.iterdir():
        if f.suffix.lower() == ".dcm":
            total_files += 1
            total_size += f.stat().st_size
    last_json = None
    p = base / "dicom_data.json"
    if p.exists():
        last_json = datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")
    return {"dir": str(base), "files": total_files, "size": total_size,
            "last_export": last_json}


@app.post("/api/generate")
def generate(req: GenerateRequest):
    try:
        d0 = datetime.strptime(req.start_date, "%Y-%m-%d")
        d1 = datetime.strptime(req.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Format tanggal tidak valid (harus YYYY-MM-DD)")

    n_dates = abs((d1 - d0).days) + 1
    if n_dates > MAX_DATES:
        raise HTTPException(400, f"Rentang tanggal maksimal {MAX_DATES} hari")
    total = n_dates * req.count_per_date
    if total > MAX_TOTAL:
        raise HTTPException(
            400, f"Total file {total} melebihi batas {MAX_TOTAL}. "
                 f"Kurangi jumlah per tanggal atau rentang tanggal.")

    cfg = GenConfig(
        count_per_date=req.count_per_date,
        start=req.start_date,
        end=req.end_date,
        modality=req.modality,
        location=req.location,
        institution=req.institution,
        department=req.department,
        guarantor=req.guarantor,
        patient_sex=req.patient_sex,
        image_style=req.image_style,
        output_dir=req.output_dir,
    )
    job_id, job = _new_job(req, total)

    def progress(done, tot, fname):
        if job["cancelled"]:
            raise JobCancelled()
        job["done"] = done
        job["current"] = fname
        job["percent"] = round(done * 100 / tot, 1)
        job["message"] = f"Membuat {fname} ({done}/{tot})"

    def worker():
        try:
            records, files, outdir = engine_generate(cfg, progress)
            job["records"] = records
            job["files"] = files
            job["output_dir"] = req.output_dir
            job["output_path"] = str(outdir)
            job["status"] = "done"
            job["message"] = f"Selesai — {len(files)} file dibuat"
        except JobCancelled:
            job["status"] = "cancelled"
            job["message"] = "Dibatalkan oleh user"
        except Exception as e:
            job["status"] = "error"
            job["error"] = str(e)
            job["message"] = f"Error: {e}"
        finally:
            job["finished_at"] = time.time()

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id, "total": total, "dates": n_dates}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job tidak ditemukan")
    elapsed = (job["finished_at"] or time.time()) - job["started_at"]
    return {
        "id": job["id"], "status": job["status"], "done": job["done"],
        "total": job["total"], "percent": job["percent"],
        "current": job["current"], "message": job["message"],
        "error": job["error"], "elapsed": round(elapsed, 1),
    }


@app.post("/api/jobs/{job_id}/cancel")
def job_cancel(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job tidak ditemukan")
    job["cancelled"] = True
    return {"ok": True}


@app.get("/api/jobs/{job_id}/results")
def job_results(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job tidak ditemukan")
    return {"status": job["status"], "records": job["records"],
            "output_dir": job["output_dir"]}


@app.get("/api/records")
def records(dir: str = "generated_dicoms"):
    base = _outdir(dir)
    p = base / "dicom_data.json"
    if not p.exists():
        return {"records": []}
    with open(p, encoding="utf8") as f:
        return {"records": json.load(f)}


@app.get("/api/download/{filename}")
def download(filename: str, dir: str = "generated_dicoms"):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Nama file tidak valid")
    path = _outdir(dir) / filename
    if not path.is_file():
        raise HTTPException(404, "File tidak ditemukan")
    return FileResponse(path, filename=filename, media_type="application/dicom")


@app.get("/api/download-zip")
def download_zip(dir: str = "generated_dicoms"):
    base = _outdir(dir)
    dcm_files = sorted(f.name for f in base.iterdir() if f.suffix.lower() == ".dcm")
    if not dcm_files:
        raise HTTPException(404, "Tidak ada file .dcm di folder output")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in dcm_files:
            zf.write(base / f, arcname=f)
        j = base / "dicom_data.json"
        if j.exists():
            zf.write(j, arcname="dicom_data.json")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return FileResponse(tmp.name, filename=f"dicom_export_{stamp}.zip",
                        media_type="application/zip",
                        background=BackgroundTask(os.unlink, tmp.name))


@app.post("/api/open-folder")
def open_folder(dir: str = "generated_dicoms"):
    base = _outdir(dir)
    if os.name == "nt":
        os.startfile(base)  # type: ignore[attr-defined]
    else:
        os.system(f'xdg-open "{base}"')
    return {"ok": True}


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static",
                           html=True), name="static")


def main():
    import uvicorn
    import webbrowser

    port = int(os.environ.get("PORT", "8000"))
    threading.Timer(1.2,
                    lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    print(f"DICOM Generator UI: http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
