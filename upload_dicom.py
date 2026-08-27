#!/usr/bin/env python3
"""Create DICOM files from dicom_data.json and upload to instances_upload API."""
import json
import os
import sys
import time
import uuid
import urllib.request
import urllib.error
import tempfile
import numpy as np

# Import DICOM creator from create-dicom.py
import importlib.util
_spec = importlib.util.spec_from_file_location("create_dicom", os.path.join(os.getcwd(), "create-dicom.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
create_dicom_from_array = _mod.create_dicom_from_array

API = "http://localhost:8041"
LOGIN_URL = f"{API}/login"
UPLOAD_URL = f"{API}/instances_upload"
USERNAME = "superadmin"
PASSWORD = "niatikhla5"
DICOM_DATA_FILE = "dicom_data.json"

def make_metadata(rec):
    """Map flat JSON record to DICOM Tags format."""
    tags = {
        "PatientID": rec["PatientID"],
        "PatientName": rec["PatientName"],
        "PatientSex": rec["PatientSex"],
        "PatientBirthDate": rec["PatientBirthDate"],
        "AccessionNumber": rec["AccessionNumber"],
        "Modality": rec["Modality"],
        "ReferringPhysicianName": rec["ReferringPhysicianName"],
        "InstitutionName": rec.get("Institution", ""),
        "InstitutionalDepartmentName": rec.get("Department", ""),
        "BodyPartExamined": rec.get("Modality", "CT"),
        "ScheduledProcedureStepSequence": [{
            "Modality": rec["Modality"],
            "ScheduledProcedureStepStartDate": rec["ScheduledDate"],
            "ScheduledProcedureStepStartTime": rec["ScheduledTime"],
            "ScheduledStationAETitle": rec["ScheduledStationAETitle"],
            "ScheduledProcedureStepID": rec.get("RequestedProcedureID", ""),
            "ScheduledProcedureStepDescription": rec.get("RequestedProcedureDescription", ""),
            "ScheduledProcedureStepLocation": rec.get("Location", "")
        }]
    }
    return tags

def create_dicom_file(rec, filepath):
    """Create a synthetic DICOM file from a JSON record."""
    # 256x256 gradient synthetic image
    x = np.linspace(0, 255, 256, dtype=np.uint8)
    arr = np.tile(x, (256, 1))
    metadata = make_metadata(rec)
    create_dicom_from_array(filepath, arr, metadata=metadata)
    return filepath

def http_json(url, data=None, headers=None, method="GET"):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        return {"_http_error": e.code, "_body": err}
    except (TimeoutError, OSError) as e:
        return {"_http_error": "timeout", "_body": str(e)}

def upload_file(url, filepath, headers, retries=3):
    """Upload a DICOM file as raw binary with Content-Type: application/dicom."""
    with open(filepath, "rb") as f:
        body = f.read()

    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/dicom")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    if raw.strip():
                        return {"_http_error": 200, "_body": raw[:500]}
                    return {"status": "success", "_raw": ""}
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
    # 1. Load records
    with open(DICOM_DATA_FILE, "r", encoding="utf8") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} records from {DICOM_DATA_FILE}")

    # 2. Login
    print("\nLogging in...")
    login_resp = http_json(LOGIN_URL, {"username": USERNAME, "password": PASSWORD}, method="POST")
    if "_http_error" in login_resp:
        print("Login failed:", login_resp)
        return
    token = login_resp["token"]
    session_id = login_resp["session_id"]
    print(f"Login OK. session_id={session_id}")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Session-ID": session_id
    }

    # 3. Create + upload each DICOM
    print(f"\nCreating and uploading {len(records)} DICOM files to {UPLOAD_URL} ...")
    tmpdir = tempfile.mkdtemp()
    ok = 0
    fail = 0
    for i, rec in enumerate(records, 1):
        dcm_path = os.path.join(tmpdir, f"{rec['PatientID']}.dcm")
        try:
            create_dicom_file(rec, dcm_path)
        except Exception as e:
            fail += 1
            print(f"[{i}/{len(records)}] CREATE FAIL PID={rec['PatientID']}: {e}")
            continue

        resp = upload_file(UPLOAD_URL, dcm_path, headers)
        if "_http_error" in resp:
            fail += 1
            if fail <= 10 or i % 100 == 0:
                print(f"[{i}/{len(records)}] FAIL PID={rec['PatientID']} -> {resp['_http_error']}: {resp.get('_body','')[:200]}")
        else:
            ok += 1

        os.remove(dcm_path)

        if i % 100 == 0:
            print(f"[{i}/{len(records)}] ok={ok} fail={fail}")

    # Cleanup
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass

    print(f"\nDone. Success={ok}, Failed={fail}")

if __name__ == "__main__":
    main()
