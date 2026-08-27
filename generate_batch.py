#!/usr/bin/env python3
import json
import random
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("create_dicom_mod",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "create-dicom.py"))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
create_dicom_from_array = _mod.create_dicom_from_array

TODAY_DATE = "20260602"
TODAY_TIME = "100000"

LOCATIONS = ["IGD", "ICU", "Rawat Inap", "Umum / Poliklinik"]

FIRST_NAMES = ["Budi", "Siti", "Ahmad", "Dewi", "Rudi", "Fitri", "Hendra", "Maya",
               "Agus", "Rina", "Doni", "Sri", "Eko", "Wati", "Bayu", "Nita",
               "Adi", "Rani", "Tono", "Dian"]
LAST_NAMES = ["Santoso", "Wijaya", "Kusuma", "Pratama", "Saputra", "Hidayat",
              "Nugroho", "Utami", "Wulandari", "Siregar", "Nasution", "Gunawan",
              "Wibowo", "Handayani", "Permadi", "Hartono"]

def random_patient_name():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first}^{last}"

def random_patient_id():
    return f"{random.randint(100000, 999999)}"

def random_physician():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"dr {first} {last}"

def random_accession():
    return f"ACC-{random.randint(100000, 999999)}"

def random_requested_id():
    return f"REQ-{random.randint(100000, 999999)}"

def random_sps_id():
    return f"SPS-{random.randint(100000, 999999)}"

def build_metadata(location):
    patient_name = random_patient_name()
    patient_id = random_patient_id()
    physician = random_physician()

    return {
        "Tags": {
            "ReferringPhysicianName": physician,
            "NameOfPhysiciansReadingStudy": f"Radiologist {random_patient_name().replace('^', ' ')}",
            "OperatorsName": "Technician",
            "InstitutionalDepartmentName": "Radiologi",
            "BodyPartExamined": random.choice(["CT", "MR", "XR", "US"]),
            "PatientID": patient_id,
            "PatientName": patient_name,
            "PatientSex": random.choice(["M", "F"]),
            "PatientBirthDate": f"{random.randint(1950, 2005)}{random.randint(1,12):02d}{random.randint(1,28):02d}",
            "AccessionNumber": random_accession(),
            "RequestedProcedureID": random_requested_id(),
            "RequestedProcedureDescription": location,
            "ScheduledProcedureStepSequence": [
                {
                    "Modality": random.choice(["CT", "MR", "DX", "US"]),
                    "ScheduledProcedureStepStartDate": TODAY_DATE,
                    "ScheduledProcedureStepStartTime": TODAY_TIME,
                    "ScheduledStationAETitle": f"{location[:3].upper()}01",
                    "ScheduledProcedureStepID": random_sps_id(),
                    "ScheduledProcedureStepDescription": location,
                    "ScheduledStationName": f"RAD-{location.replace(' ', '_').upper()}",
                    "ScheduledProcedureStepLocation": location
                }
            ]
        }
    }

def main():
    np.random.seed()
    random.seed()

    for loc in LOCATIONS:
        meta = build_metadata(loc)
        patient_name = meta["Tags"]["PatientName"]
        patient_id = meta["Tags"]["PatientID"]
        safe_loc = loc.replace(" ", "_").replace("/", "_")
        filename = f"{safe_loc}_{patient_id}.dcm"

        arr = np.random.randint(0, 256, (256, 256), dtype=np.uint8)

        ds = create_dicom_from_array(
            filename=filename,
            arr=arr,
            patient_name=patient_name,
            patient_id=patient_id,
            modality=meta["Tags"]["ScheduledProcedureStepSequence"][0]["Modality"],
            series_description=loc,
            metadata=meta["Tags"]
        )
        print(f"Created: {filename}  |  Patient: {patient_name}  |  Location: {loc}")

    print("\nAll DICOM files generated successfully.")

if __name__ == "__main__":
    main()
