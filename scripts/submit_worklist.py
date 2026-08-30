#!/usr/bin/env python3
"""Generate random worklist records, save to output/dicom_data.json,
then login and POST each record to the worklist/request API.

Config via environment variables:
    DICOM_API_KEY   (required) API key for x-api-key header
    DICOM_API_URL   (default http://localhost:8041)
    DICOM_NUM       (default 1000) number of records
"""
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

import _bootstrap

API = os.environ.get("DICOM_API_URL", "http://localhost:8041")
WORKLIST_URL = f"{API}/his/worklist/request"
API_KEY = os.environ.get("DICOM_API_KEY", "")
NUM = int(os.environ.get("DICOM_NUM", "1000"))

FIRST_M = ["BUDI", "AGUS", "RIZKI", "DONI", "HENDRA", "FAISAL", "YOGA", "ILHAM",
           "ANDI", "BAMBANG", "JOKO", "EKO", "WAHYU", "REZA", "DIMAS", "BAYU"]
FIRST_F = ["SARI", "DEWI", "PUTRI", "NISA", "RINA", "INTAN", "MAYA", "LIA",
           "AYU", "INDAH", "SITI", "DEVI", "RANI", "TARI", "WATI", "KARTIKA"]
LAST = ["SANTOSO", "WIBOWO", "PRATAMA", "NUGROHO", "HIDAYAT", "MAHARANI",
        "ANGGRAINI", "PERMATA", "KUSUMA", "SAPUTRA", "WIJAYA", "GUNAWAN",
        "SETIAWAN", "HALIM", "TANJUNG", "NATA"]
INST = ["RS Dummy", "RS Sehat Sentosa", "RS Cahaya Medika", "RS Bersama Kita",
        "RS Harapan", "RS Medika", "RS Permata", "RS Bunda"]
DEPT = ["Radiologi", "UGD", "ICU", "Penyakit Dalam", "Bedah", "Anak"]
LOC = ["RADIOLOGI", "ICU", "UGD", "RUANG CT", "RUANG OK", "POLI UMUM"]
AE = ["CT01", "ct_pro", "CT02", "CTSCANNER", "MR01", "USG01"]
REF = ["DR Josh", "DR DUMMY", "DR Andi", "DR Lestari", "DR Bambang",
       "DR Sari", "DR Eko", "DR Wati"]
DESC = ["CT TEST", "CT ABDOMEN", "CT KEPALA", "CT THORAX", "CT",
        "CT ANGIO", "MRI BRAIN", "USG ABDOMEN"]
GUARANTOR = ["BPJS", "Mandiri", "Prudential", "Self Pay", "Allianz"]


def rand_name(sex):
    first = random.choice(FIRST_M if sex == "M" else FIRST_F)
    last = random.choice(LAST)
    return f"{first} {last}"


def rand_birth():
    return f"{random.randint(1960, 2008)}{random.randint(1, 12):02d}{random.randint(1, 28):02d}"


def rand_time():
    return f"{random.randint(7, 20):02d}{random.randint(0, 59):02d}{random.randint(0, 59):02d}"


def generate_records():
    used_ids = set()
    records = []
    for _ in range(NUM):
        sex = random.choice(["M", "F"])
        pid = str(random.randint(1000000, 9999999))
        while pid in used_ids:
            pid = str(random.randint(1000000, 9999999))
        used_ids.add(pid)
        acc = str(random.randint(10**15, 10**16 - 1))
        records.append({
            "PatientID": pid,
            "PatientName": rand_name(sex),
            "PatientSex": sex,
            "PatientBirthDate": rand_birth(),
            "AccessionNumber": acc,
            "RequestedProcedureID": f"REQ-{random.randint(1000000, 9999999)}",
            "RequestedProcedureDescription": random.choice(DESC),
            "Modality": random.choice(["CT", "MR", "US", "XA"]),
            "ScheduledDate": random.choice(["20260807", "20260806", "20260805"]),
            "ScheduledTime": rand_time(),
            "ScheduledStationAETitle": random.choice(AE),
            "ReferringPhysicianName": random.choice(REF),
            "Location": random.choice(LOC),
            "Department": random.choice(DEPT),
            "Institution": random.choice(INST),
            "Guarantor": random.choice(GUARANTOR)
        })
    return records


def http_json(url, data=None, headers=None, method="GET", retries=3):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            return {"_http_error": e.code, "_body": err}
        except (TimeoutError, OSError) as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return {"_http_error": "timeout", "_body": str(e)}
    return {"_http_error": "timeout", "_body": "max retries"}


def main():
    if not API_KEY:
        print("ERROR: set environment variable DICOM_API_KEY first.")
        print('PowerShell: $env:DICOM_API_KEY = "ak_..."')
        sys.exit(1)

    print(f"Generating {NUM} random records...")
    records = generate_records()
    target = _bootstrap.output_dir() / "dicom_data.json"
    with open(target, "w", encoding="utf8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)
    print(f"Saved {len(records)} records to {target}")

    print(f"\nSubmitting {len(records)} records to {WORKLIST_URL} ...")
    headers = {"x-api-key": API_KEY}
    ok = 0
    fail = 0
    for i, rec in enumerate(records, 1):
        resp = http_json(WORKLIST_URL, rec, headers=headers, method="POST")
        if "_http_error" in resp:
            fail += 1
            if fail <= 5 or i % 100 == 0:
                print(f"[{i}/{len(records)}] FAIL PID={rec['PatientID']} -> {resp['_http_error']}: {resp.get('_body', '')[:200]}")
        else:
            ok += 1
        if i % 100 == 0:
            print(f"[{i}/{len(records)}] ok={ok} fail={fail}")

    print(f"\nDone. Success={ok}, Failed={fail}")


if __name__ == "__main__":
    main()
