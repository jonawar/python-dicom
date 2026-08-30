#!/usr/bin/env python3
"""Legacy: 5 dummy DICOMs today + 5 yesterday with fixed patient template."""
import json
from datetime import datetime, timedelta

import _bootstrap
import numpy as np

from dicom_generator.core import create_dicom_from_array

OUTPUT_DIR = _bootstrap.output_dir("generated_dicoms")

TODAY = datetime.now()
YESTERDAY = TODAY - timedelta(days=1)

TODAY_STR = TODAY.strftime("%Y%m%d")
YESTERDAY_STR = YESTERDAY.strftime("%Y%m%d")


def _max_num(prefix):
    files = [f for f in OUTPUT_DIR.iterdir() if f.name.startswith(prefix) and f.name.endswith(".dcm")]
    nums = []
    for f in files:
        try:
            nums.append(int(f.name.split("_")[-1].replace(".dcm", "")))
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
    base_time = datetime.strptime("100000", "%H%M%S")
    time_val = base_time + timedelta(seconds=time_offset_seconds)
    time_str = time_val.strftime("%H%M%S")

    filename = f"dummy_{date_str}_{num:02d}.dcm"
    filepath = OUTPUT_DIR / filename

    arr = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
    meta = build_dicom_metadata(date_str, time_str)

    create_dicom_from_array(
        filename=str(filepath),
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
        dicom_path = str(OUTPUT_DIR / filename)
        json_entry = build_json_entry(TODAY_STR, time_str, dicom_path)
        with open(OUTPUT_DIR / filename.replace(".dcm", ".json"), "w", encoding="utf-8") as f:
            json.dump(json_entry, f, indent=4, ensure_ascii=False)
        all_entries.append(json_entry)

    print(f"\nGenerating {count} DICOM files for yesterday ({YESTERDAY_STR})...")
    for i in range(count):
        num = NEXT_NUM_YESTERDAY + i
        filename, time_str = generate_dicom(YESTERDAY_STR, num, i * 60)
        dicom_path = str(OUTPUT_DIR / filename)
        json_entry = build_json_entry(YESTERDAY_STR, time_str, dicom_path)
        with open(OUTPUT_DIR / filename.replace(".dcm", ".json"), "w", encoding="utf-8") as f:
            json.dump(json_entry, f, indent=4, ensure_ascii=False)
        all_entries.append(json_entry)

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

    dicom_data_path = _bootstrap.OUTPUT_ROOT / "dicom_data.json"
    dicom_data_path.write_text(json.dumps(all_entries, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"Updated: {dicom_data_path} ({len(all_entries)} new entries)")

    print(f"\nDone! Generated {count * 2} DICOM files and JSON data.")


if __name__ == "__main__":
    main()
