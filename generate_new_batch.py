#!/usr/bin/env python3
import json
import os
import sys
import numpy as np
import importlib.util as _ilu
from datetime import datetime, timedelta

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(WORKSPACE, "generated_dicoms")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_spec = _ilu.spec_from_file_location("create_dicom_mod",
    os.path.join(WORKSPACE, "create-dicom.py"))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
create_dicom_from_array = _mod.create_dicom_from_array

TODAY = datetime.now()
YESTERDAY = TODAY - timedelta(days=1)

TODAY_STR = TODAY.strftime("%Y%m%d")
YESTERDAY_STR = YESTERDAY.strftime("%Y%m%d")

def _max_num(prefix):
    files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(prefix) and f.endswith(".dcm")]
    nums = []
    for f in files:
        try:
            nums.append(int(f.split("_")[-1].replace(".dcm", "")))
        except ValueError:
            pass
    return max(nums) if nums else 0

NEXT_NUM_TODAY = _max_num(f"dummy_{TODAY_STR}_") + 1
NEXT_NUM_YESTERDAY = _max_num(f"dummy_{YESTERDAY_STR}_") + 1

def build_json_entry(date_str, time_str, dicom_path):
    return {
        "PatientID": "5456403",
        "PatientName": "DUMMY PATIENT FOUR",
        "PatientSex": "F",
        "PatientBirthDate": "19951125",
        "AccessionNumber": "1987654321123433",
        "RequestedProcedureID": "REQ-5555502",
        "RequestedProcedureDescription": "CT TEST",
        "Modality": "CT",
        "ScheduledDate": date_str,
        "ScheduledTime": time_str,
        "ScheduledStationAETitle": "ct_pro",
        "ReferringPhysicianName": "DR DUMMY",
        "Location": "ICU",
        "Department": "UGD",
        "Institution": "RS Dummy",
        "Guarantor": "BPJS",
        "DicomFile": dicom_path
    }

def build_dicom_metadata(date_str, time_str):
    return {
        "Tags": {
            "PatientID": "5456403",
            "PatientName": "DUMMY PATIENT FOUR",
            "PatientSex": "F",
            "PatientBirthDate": "19951125",
            "AccessionNumber": "1987654321123433",
            "RequestedProcedureID": "REQ-5555502",
            "RequestedProcedureDescription": "CT TEST",
            "Modality": "CT",
            "ReferringPhysicianName": "DR DUMMY",
            "InstitutionalDepartmentName": "UGD",
            "InstitutionName": "RS Dummy",
            "ScheduledProcedureStepSequence": [
                {
                    "Modality": "CT",
                    "ScheduledProcedureStepStartDate": date_str,
                    "ScheduledProcedureStepStartTime": time_str,
                    "ScheduledStationAETitle": "ct_pro",
                    "ScheduledProcedureStepID": f"SPS-{date_str}{time_str}",
                    "ScheduledProcedureStepDescription": "CT TEST",
                    "ScheduledStationName": "CT-ROOM1",
                    "ScheduledProcedureStepLocation": "ICU"
                }
            ]
        }
    }

def generate_dicom(date_str, num, time_offset_seconds):
    time_val = datetime.strptime("100000", "%H%M%S")
    from datetime import timedelta as td
    time_val = time_val + td(seconds=time_offset_seconds)
    time_str = time_val.strftime("%H%M%S")
    
    filename = f"dummy_{date_str}_{num:02d}.dcm"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    arr = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
    meta = build_dicom_metadata(date_str, time_str)
    
    ds = create_dicom_from_array(
        filename=filepath,
        arr=arr,
        patient_name="DUMMY^PATIENT FOUR",
        patient_id="5456403",
        modality="CT",
        series_description="CT TEST",
        metadata=meta["Tags"]
    )
    print(f"Created DICOM: {filename}")
    return filename, time_str

def main():
    all_entries = []
    count = 5
    print(f"Generating {count} DICOM files for today ({TODAY_STR})...")
    for i in range(count):
        num = NEXT_NUM_TODAY + i
        filename, time_str = generate_dicom(TODAY_STR, num, i * 60)
        dicom_path = os.path.join(OUTPUT_DIR, filename)
        json_entry = build_json_entry(TODAY_STR, time_str, dicom_path)
        json_filename = filename.replace(".dcm", ".json")
        json_path = os.path.join(OUTPUT_DIR, json_filename)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_entry, f, indent=4, ensure_ascii=False)
        print(f"Created JSON:   {json_filename}")
        all_entries.append(json_entry)

    print(f"\nGenerating {count} DICOM files for yesterday ({YESTERDAY_STR})...")
    for i in range(count):
        num = NEXT_NUM_YESTERDAY + i
        filename, time_str = generate_dicom(YESTERDAY_STR, num, i * 60)
        dicom_path = os.path.join(OUTPUT_DIR, filename)
        json_entry = build_json_entry(YESTERDAY_STR, time_str, dicom_path)
        json_filename = filename.replace(".dcm", ".json")
        json_path = os.path.join(OUTPUT_DIR, json_filename)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_entry, f, indent=4, ensure_ascii=False)
        print(f"Created JSON:   {json_filename}")
        all_entries.append(json_entry)

    all_meta_path = os.path.join(OUTPUT_DIR, "all_metadata.json")
    existing = []
    if os.path.exists(all_meta_path):
        with open(all_meta_path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except:
                existing = []
    
    existing.extend(all_entries)
    with open(all_meta_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)
    print(f"\nUpdated: all_metadata.json ({len(existing)} total entries)")

    dicom_data_path = os.path.join(WORKSPACE, "dicom_data.json")
    with open(dicom_data_path, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, indent=4, ensure_ascii=False)
    print(f"Updated: dicom_data.json ({len(all_entries)} new entries)")

    print(f"\nDone! Generated {count * 2} DICOM files and JSON data.")

if __name__ == "__main__":
    main()
