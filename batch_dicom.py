#!/usr/bin/env python3
"""Generate N DICOM files per date and dump a flattened JSON summary.

Usage:
    python batch_dicom.py 10            # 10 files for today
    python batch_dicom.py 10 1          # 10 files each for today and yesterday
    python batch_dicom.py 5 3           # 5 files each for today and 3 days back
"""
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta

from pydicom import dcmread

NUM = int(sys.argv[1]) if len(sys.argv) > 1 else 10
DAYS_BACK = int(sys.argv[2]) if len(sys.argv) > 2 else 0
TODAY = datetime.now()

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
    y = random.randint(1970, 2005)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y}{m:02d}{d:02d}"

def rand_time():
    h = random.randint(7, 18)
    m = random.randint(0, 59)
    s = random.randint(0, 59)
    return f"{h:02d}{m:02d}{s:02d}"

def make(i, date_str, suffix):
    sex = random.choice(["M", "F"])
    pid = f"{date_str}{i:02d}"
    dicom_name, plain_name = rand_name(sex)
    birth = rand_birth()
    sched_time = rand_time()
    dept = random.choice(DEPT)
    loc = random.choice(LOC)
    inst = random.choice(INST)
    ae_title = random.choice(AE)
    ref = random.choice(REF)
    desc = random.choice(DESC)
    m = {"Tags": {
        "PatientID": pid,
        "PatientName": plain_name,
        "PatientSex": sex,
        "PatientBirthDate": birth,
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
            "ScheduledProcedureStepStartTime": sched_time,
            "ScheduledStationAETitle": ae_title,
            "ScheduledProcedureStepID": f"SPS-{pid}",
            "ScheduledProcedureStepDescription": desc,
            "ScheduledStationName": f"RAD-ROOM{random.randint(1,4)}",
            "ScheduledProcedureStepLocation": loc
        }]
    }}
    tmp = f"_meta_{pid}.json"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(m, f, indent=2)
    out = f"dicom_{pid}{suffix}.dcm"
    subprocess.run(["python", "create-dicom.py", "--out", out, "--metadata", tmp],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    os.remove(tmp)
    return out

def dump_json(files):
    out = []
    for f in files:
        ds = dcmread(f)
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
            "Guarantor": "BPJS"
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
    with open("dicom_data.json", "w", encoding="utf8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"\nWrote {len(data)} entries to dicom_data.json\n")
    print(json.dumps(data, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
