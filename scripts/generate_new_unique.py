#!/usr/bin/env python3
"""Legacy: 10 DICOMs with unique patient names (5 today + 5 yesterday)."""
import json
import random
from datetime import datetime, timedelta

import _bootstrap
import numpy as np

from dicom_generator.core import create_dicom_from_array

OUTPUT_DIR = _bootstrap.output_dir("generated_dicoms")

TODAY = datetime.now()
YESTERDAY = TODAY - timedelta(days=1)
TODAY_STR = TODAY.strftime("%Y%m%d")
YESTERDAY_STR = YESTERDAY.strftime("%Y%m%d")

FIRST_NAMES = ["RENDI", "PUTRI", "AGUNG", "LINA", "FADLI",
               "KARTIKA", "HENDRO", "SULIS", "WAHYU", "DEVI"]
LAST_NAMES = ["SAPUTRA", "KUSUMA", "RAHARDJO", "WULANDARI", "SETIAWAN",
              "PERMANA", "WIJAYA", "MAULIDA", "NUGRAHA", "INDRASWARI"]
PROCEDURES = ["CT ABDOMEN", "CT THORAX", "CT KEPALA", "CT TEST", "CT"]
STATIONS = ["CT01", "CT02", "CTSCANNER", "ct_pro"]
PHYSICIANS = ["DR Josh", "DR DUMMY", "DR Bambang", "DR Lestari", "DR Andi"]
LOCATIONS = ["UGD", "RUANG CT", "ICU", "RADIOLOGI"]
DEPARTMENTS = ["Radiologi", "UGD", "Penyakit Dalam", "ICU"]
INSTITUTIONS = ["RS Sehat Sentosa", "RS Cahaya Medika", "RS Bersama Kita", "RS Dummy"]


def _max_num(prefix):
    files = [f for f in OUTPUT_DIR.iterdir() if f.name.startswith(prefix) and f.name.endswith(".dcm")]
    nums = []
    for f in files:
        try:
            nums.append(int(f.name.split("_")[-1].replace(".dcm", "")))
        except ValueError:
            pass
    return max(nums) if nums else 0


used_names = set()
used_ids = set()


def unique_patient(idx):
    random.seed(idx * 137 + 42)
    while True:
        first = FIRST_NAMES[idx % len(FIRST_NAMES)]
        last = LAST_NAMES[idx % len(LAST_NAMES)]
        name = f"{first} {last}"
        if name not in used_names:
            used_names.add(name)
            break
        idx += 1
    while True:
        pid = f"{TODAY_STR if idx < 5 else YESTERDAY_STR}{(idx + 1):02d}"
        if pid not in used_ids:
            used_ids.add(pid)
            break
        idx += 1
    return name, pid


def build_json_entry(idx, date_str, time_str, dicom_path):
    name, pid = unique_patient(idx)
    sex = "F" if idx % 2 == 0 else "M"
    birth_year = random.randint(1950, 2005)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    birth_date = f"{birth_year}{birth_month:02d}{birth_day:02d}"
    accession = f"ACC-{pid}"
    req_id = f"REQ-{pid}"
    procedure = PROCEDURES[idx % len(PROCEDURES)]
    station = STATIONS[idx % len(STATIONS)]
    physician = PHYSICIANS[idx % len(PHYSICIANS)]
    location = LOCATIONS[idx % len(LOCATIONS)]
    department = DEPARTMENTS[idx % len(DEPARTMENTS)]
    institution = INSTITUTIONS[idx % len(INSTITUTIONS)]

    entry = {
        "PatientID": pid,
        "PatientName": name,
        "PatientSex": sex,
        "PatientBirthDate": birth_date,
        "AccessionNumber": accession,
        "RequestedProcedureID": req_id,
        "RequestedProcedureDescription": procedure,
        "Modality": "CT",
        "ScheduledDate": date_str,
        "ScheduledTime": time_str,
        "ScheduledStationAETitle": station,
        "ReferringPhysicianName": physician,
        "Location": location,
        "Department": department,
        "Institution": institution,
        "Guarantor": "BPJS"
    }
    if dicom_path:
        entry["DicomFile"] = dicom_path
    return entry


def build_dicom_metadata(entry, date_str, time_str):
    return {
        "PatientID": entry["PatientID"],
        "PatientName": entry["PatientName"].replace(" ", "^"),
        "PatientSex": entry["PatientSex"],
        "PatientBirthDate": entry["PatientBirthDate"],
        "AccessionNumber": entry["AccessionNumber"],
        "RequestedProcedureID": entry["RequestedProcedureID"],
        "RequestedProcedureDescription": entry["RequestedProcedureDescription"],
        "Modality": "CT",
        "ReferringPhysicianName": entry["ReferringPhysicianName"],
        "InstitutionalDepartmentName": entry["Department"],
        "InstitutionName": entry["Institution"],
        "ScheduledProcedureStepSequence": [
            {
                "Modality": "CT",
                "ScheduledProcedureStepStartDate": date_str,
                "ScheduledProcedureStepStartTime": time_str,
                "ScheduledStationAETitle": entry["ScheduledStationAETitle"],
                "ScheduledProcedureStepID": f"SPS-{date_str}{time_str}",
                "ScheduledProcedureStepDescription": entry["RequestedProcedureDescription"],
                "ScheduledStationName": "CT-ROOM1",
                "ScheduledProcedureStepLocation": entry["Location"]
            }
        ]
    }


def generate_dicom(entry, date_str, time_str, num):
    filename = f"dummy_{date_str}_{num:02d}.dcm"
    filepath = OUTPUT_DIR / filename

    arr = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
    meta = build_dicom_metadata(entry, date_str, time_str)

    create_dicom_from_array(
        filename=str(filepath),
        arr=arr,
        patient_name=entry["PatientName"].replace(" ", "^"),
        patient_id=entry["PatientID"],
        modality="CT",
        series_description=entry["RequestedProcedureDescription"],
        metadata=meta
    )
    print(f"Created DICOM: {filename}")
    return str(filepath)


def main():
    random.seed(2026)
    np.random.seed(2026)

    all_entries = []
    time_offsets = [0, 3600, 7200, 10800, 14400]

    next_today = _max_num(f"dummy_{TODAY_STR}_") + 1
    print(f"Generating 5 DICOM files for today ({TODAY_STR})...")
    for i in range(5):
        idx = i
        base_time = datetime.strptime("080000", "%H%M%S")
        time_val = base_time + timedelta(seconds=time_offsets[i])
        time_str = time_val.strftime("%H%M%S")
        num = next_today + i
        entry = build_json_entry(idx, TODAY_STR, time_str, None)
        dicom_path = generate_dicom(entry, TODAY_STR, time_str, num)
        entry["DicomFile"] = dicom_path
        all_entries.append(entry)

    next_yesterday = _max_num(f"dummy_{YESTERDAY_STR}_") + 1
    print(f"\nGenerating 5 DICOM files for yesterday ({YESTERDAY_STR})...")
    for i in range(5):
        idx = i + 5
        base_time = datetime.strptime("080000", "%H%M%S")
        time_val = base_time + timedelta(seconds=time_offsets[i])
        time_str = time_val.strftime("%H%M%S")
        num = next_yesterday + i
        entry = build_json_entry(idx, YESTERDAY_STR, time_str, None)
        dicom_path = generate_dicom(entry, YESTERDAY_STR, time_str, num)
        entry["DicomFile"] = dicom_path
        all_entries.append(entry)

    all_meta_path = OUTPUT_DIR / "all_metadata.json"
    existing = []
    if all_meta_path.exists():
        try:
            existing = json.loads(all_meta_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.extend(all_entries)
    all_meta_path.write_text(json.dumps(existing, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"\nUpdated: all_metadata.json ({len(existing)} total entries)")

    dicom_data_new_path = _bootstrap.OUTPUT_ROOT / "dicom_data_new.json"
    dicom_data_new_path.write_text(json.dumps(all_entries, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"Created: {dicom_data_new_path} ({len(all_entries)} entries)")

    print("\nDone! Generated 10 DICOM files and JSON data.")


if __name__ == "__main__":
    main()
