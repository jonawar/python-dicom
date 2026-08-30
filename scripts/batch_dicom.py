#!/usr/bin/env python3
"""Generate N DICOM files per date and dump a flattened JSON summary.

Usage:
    python scripts/batch_dicom.py 10            # 10 files for today
    python scripts/batch_dicom.py 10 1          # 10 files each for today and yesterday
    python scripts/batch_dicom.py 5 3           # 5 files each for today and 3 days back

Output goes to output/generated_dicoms/. Prefer the web UI (python run.py)
for interactive use.
"""
import json
import random
import sys
from datetime import datetime, timedelta

import _bootstrap  # noqa: F401
from pydicom import dcmread

from dicom_generator.core import create_dicom_from_array, synthetic_array
from dicom_generator.paths import resolve_output_dir

NUM = int(sys.argv[1]) if len(sys.argv) > 1 else 10
DAYS_BACK = int(sys.argv[2]) if len(sys.argv) > 2 else 0
TODAY = datetime.now()
OUT_DIR = resolve_output_dir("generated_dicoms")

FIRST_M = ["BUDI", "AGUS", "RIZKI", "DONI", "HENDRA", "FAISAL", "YOGA", "ILHAM"]
FIRST_F = ["SARI", "DEWI", "PUTRI", "NISA", "RINA", "INTAN", "MAYA", "LIA"]
LAST = ["SANTOSO", "WIBOWO", "PRATAMA", "NUGROHO", "HIDAYAT", "MAHARANI", "ANGGRAINI", "PERMATA"]
INST = ["RS Dummy", "RS Sehat Sentosa", "RS Cahaya Medika", "RS Bersama Kita"]
DEPT = ["Radiologi", "UGD", "ICU", "Penyakit Dalam"]
LOC = ["RADIOLOGI", "ICU", "UGD", "RUANG CT"]
AE = ["CT01", "ct_pro", "CT02", "CTSCANNER"]
REF = ["DR Josh", "DR DUMMY", "DR Andi", "DR Lestari", "DR Bambang"]
DESC = ["CT TEST", "CT ABDOMEN", "CT KEPALA", "CT THORAX", "CT"]


def rand_name(sex):
    first = random.choice(FIRST_M if sex == "M" else FIRST_F)
    last = random.choice(LAST)
    return f"{last}^{first}", f"{first} {last}"


def rand_birth():
    return (f"{random.randint(1970, 2005)}"
            f"{random.randint(1, 12):02d}{random.randint(1, 28):02d}")


def rand_time():
    return (f"{random.randint(7, 18):02d}"
            f"{random.randint(0, 59):02d}{random.randint(0, 59):02d}")


def make(i, date_str, suffix):
    sex = random.choice(["M", "F"])
    pid = f"{date_str}{i:02d}"
    dicom_name, plain_name = rand_name(sex)
    dept = random.choice(DEPT)
    loc = random.choice(LOC)
    inst = random.choice(INST)
    ae_title = random.choice(AE)
    ref = random.choice(REF)
    desc = random.choice(DESC)
    tags = {
        "PatientID": pid,
        "PatientName": plain_name,
        "PatientSex": sex,
        "PatientBirthDate": rand_birth(),
        "AccessionNumber": f"ACC-{pid}",
        "RequestedProcedureID": f"REQ-{pid}",
        "RequestedProcedureDescription": desc,
        "Modality": "CT",
        "ReferringPhysicianName": ref,
        "InstitutionName": inst,
        "InstitutionalDepartmentName": dept,
        "BodyPartExamined": "CT",
        "StudyDate": date_str,
        "ScheduledProcedureStepSequence": [{
            "Modality": "CT",
            "ScheduledProcedureStepStartDate": date_str,
            "ScheduledProcedureStepStartTime": rand_time(),
            "ScheduledStationAETitle": ae_title,
            "ScheduledProcedureStepID": f"SPS-{pid}",
            "ScheduledProcedureStepDescription": desc,
            "ScheduledStationName": f"RAD-ROOM{random.randint(1, 4)}",
            "ScheduledProcedureStepLocation": loc,
        }],
    }
    out = OUT_DIR / f"dicom_{pid}{suffix}.dcm"
    create_dicom_from_array(
        filename=str(out),
        arr=synthetic_array(256, 256, "gradient", 8),
        patient_name=plain_name,
        patient_id=pid,
        modality="CT",
        series_description=desc,
        metadata=tags,
    )
    return out.name


def dump_json(files):
    out = []
    for f in files:
        ds = dcmread(str(OUT_DIR / f))
        sps = ds.ScheduledProcedureStepSequence[0] if "ScheduledProcedureStepSequence" in ds else None
        out.append({
            "PatientID": getattr(ds, "PatientID", ""),
            "PatientName": str(getattr(ds, "PatientName", "")),
            "PatientSex": getattr(ds, "PatientSex", ""),
            "PatientBirthDate": getattr(ds, "PatientBirthDate", ""),
            "AccessionNumber": getattr(ds, "AccessionNumber", ""),
            "RequestedProcedureID": getattr(ds, "RequestedProcedureID", ""),
            "RequestedProcedureDescription": getattr(ds, "RequestedProcedureDescription", ""),
            "Modality": getattr(ds, "Modality", ""),
            "ScheduledDate": getattr(sps, "ScheduledProcedureStepStartDate", "") if sps else "",
            "ScheduledTime": getattr(sps, "ScheduledProcedureStepStartTime", "") if sps else "",
            "ScheduledStationAETitle": getattr(sps, "ScheduledStationAETitle", "") if sps else "",
            "ReferringPhysicianName": str(getattr(ds, "ReferringPhysicianName", "")),
            "Location": getattr(sps, "ScheduledProcedureStepLocation", "") if sps else "",
            "Department": getattr(ds, "InstitutionalDepartmentName", ""),
            "Institution": getattr(ds, "InstitutionName", ""),
            "Guarantor": "BPJS",
        })
    return out


def main():
    dates = []
    for d in range(DAYS_BACK, -1, -1):
        dates.append((TODAY - timedelta(days=d)).strftime("%Y%m%d"))
    files = []
    for date_str in dates:
        for i in range(1, NUM + 1):
            suffix = f"_{date_str}" if len(dates) > 1 else ""
            files.append(make(i, date_str, suffix))
        print(f"Created {NUM} files for {date_str}")
    data = dump_json(files)
    target = OUT_DIR / "dicom_data.json"
    with open(target, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"\nWrote {len(data)} entries to {target}\n")
    print(json.dumps(data, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
