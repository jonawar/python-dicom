"""Batch DICOM generation engine used by the web UI and CLI."""
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from dicom_generator import fakedata
from dicom_generator.core import create_dicom_from_array, synthetic_array
from dicom_generator.paths import resolve_output_dir


@dataclass
class GenConfig:
    count_per_date: int = 10
    start: str = ""                 # YYYY-MM-DD
    end: str = ""                   # YYYY-MM-DD
    modality: str = "CT"            # CT/MR/US/DX or "random"
    location: str = "random"
    institution: str = "random"
    department: str = "Radiologi"
    guarantor: str = "BPJS"
    patient_sex: str = "random"     # random/M/F
    image_style: str = "gradient"   # gradient/noise
    output_dir: str = "generated_dicoms"
    width: int = 256
    height: int = 256


def date_list(start: str, end: str):
    d0 = datetime.strptime(start, "%Y-%m-%d").date()
    d1 = datetime.strptime(end, "%Y-%m-%d").date()
    if d1 < d0:
        d0, d1 = d1, d0
    return [(d0 + timedelta(days=i)).strftime("%Y%m%d")
            for i in range((d1 - d0).days + 1)]


def build_record(cfg: GenConfig, pid: str, date_str: str, time_str: str):
    sex = fakedata.pick(cfg.patient_sex, ["M", "F"])
    _, plain_name = fakedata.random_name(sex)
    modality = fakedata.pick(cfg.modality, fakedata.MODALITIES)
    location = fakedata.pick(cfg.location, fakedata.LOCATIONS)
    institution = fakedata.pick(cfg.institution, fakedata.INSTITUTIONS)
    department = cfg.department or "Radiologi"
    guarantor = fakedata.pick(cfg.guarantor, fakedata.GUARANTORS)
    desc = random.choice(
        fakedata.DESCRIPTIONS_BY_MOD.get(modality, fakedata.DESCRIPTIONS_BY_MOD["CT"]))
    ae = random.choice(fakedata.AE_BY_MOD.get(modality, ["GEN01"]))
    physician = random.choice(fakedata.PHYSICIANS)
    birth = fakedata.random_birth_date()

    tags = {
        "PatientID": pid,
        "PatientName": plain_name,
        "PatientSex": sex,
        "PatientBirthDate": birth,
        "AccessionNumber": f"ACC-{pid}",
        "RequestedProcedureID": f"REQ-{pid}",
        "RequestedProcedureDescription": desc,
        "Modality": modality,
        "ReferringPhysicianName": physician,
        "InstitutionName": institution,
        "InstitutionalDepartmentName": department,
        "BodyPartExamined": modality,
        "StudyDate": date_str,
        "StudyTime": time_str,
        "ScheduledProcedureStepSequence": [{
            "Modality": modality,
            "ScheduledProcedureStepStartDate": date_str,
            "ScheduledProcedureStepStartTime": time_str,
            "ScheduledStationAETitle": ae,
            "ScheduledProcedureStepID": f"SPS-{pid}",
            "ScheduledProcedureStepDescription": desc,
            "ScheduledStationName": f"{modality}-ROOM{random.randint(1, 4)}",
            "ScheduledProcedureStepLocation": location,
        }],
    }
    record = {
        "PatientID": pid,
        "PatientName": plain_name,
        "PatientSex": sex,
        "PatientBirthDate": birth,
        "AccessionNumber": tags["AccessionNumber"],
        "RequestedProcedureID": tags["RequestedProcedureID"],
        "RequestedProcedureDescription": desc,
        "Modality": modality,
        "ScheduledDate": date_str,
        "ScheduledTime": time_str,
        "ScheduledStationAETitle": ae,
        "ReferringPhysicianName": physician,
        "Location": location,
        "Department": department,
        "Institution": institution,
        "Guarantor": guarantor,
    }
    return tags, record


def generate(cfg: GenConfig, progress=None):
    """Generate all DICOM files for cfg. Returns (records, filenames, outdir)."""
    dates = date_list(cfg.start, cfg.end)
    total = len(dates) * cfg.count_per_date
    outdir = resolve_output_dir(cfg.output_dir)

    records, files = [], []
    done = 0
    for date_str in dates:
        for i in range(1, cfg.count_per_date + 1):
            pid = f"{date_str}{i:02d}"
            time_str = fakedata.random_schedule_time()
            tags, record = build_record(cfg, pid, date_str, time_str)

            filename = f"dicom_{pid}.dcm"
            filepath = outdir / filename
            arr = synthetic_array(cfg.width, cfg.height, cfg.image_style)
            create_dicom_from_array(
                filename=str(filepath),
                arr=arr,
                patient_name=tags["PatientName"],
                patient_id=pid,
                modality=tags["Modality"],
                series_description=tags["RequestedProcedureDescription"],
                metadata=tags,
            )
            record["File"] = filename
            records.append(record)
            files.append(filename)
            done += 1
            if progress:
                progress(done, total, filename)

    with open(outdir / "dicom_data.json", "w", encoding="utf8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)

    return records, files, outdir
