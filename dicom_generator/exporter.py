"""Export .dcm files to radiology-table JSON records (formerly export_text.py)."""
import glob
import json
import os

import pydicom


def pval(val):
    if val is None:
        return ""
    return str(val)


def seq_attr(sps, attr, default=""):
    try:
        return pval(getattr(sps[0], attr, default))
    except (IndexError, AttributeError):
        return default


def record_from_dataset(ds):
    """Map a pydicom dataset to the radiology JSON record format."""
    sps = getattr(ds, "ScheduledProcedureStepSequence", None) or []
    return {
        "PatientID": pval(getattr(ds, "PatientID", "")),
        "PatientName": pval(getattr(ds, "PatientName", "")),
        "PatientSex": pval(getattr(ds, "PatientSex", "")),
        "PatientBirthDate": pval(getattr(ds, "PatientBirthDate", "")),
        "AccessionNumber": pval(getattr(ds, "AccessionNumber", "")),
        "RequestedProcedureID": pval(getattr(ds, "RequestedProcedureID", "")),
        "RequestedProcedureDescription": pval(
            getattr(ds, "RequestedProcedureDescription", "")),
        "Modality": seq_attr(sps, "Modality", pval(getattr(ds, "Modality", ""))),
        "ScheduledDate": seq_attr(sps, "ScheduledProcedureStepStartDate"),
        "ScheduledTime": seq_attr(sps, "ScheduledProcedureStepStartTime"),
        "ScheduledStationAETitle": seq_attr(sps, "ScheduledStationAETitle"),
        "ReferringPhysicianName": pval(getattr(ds, "ReferringPhysicianName", "")),
        "Location": seq_attr(sps, "ScheduledProcedureStepLocation"),
        "Department": pval(getattr(ds, "InstitutionalDepartmentName", "")),
        "Institution": pval(getattr(ds, "InstitutionName", "RS Dummy")),
        "Guarantor": "BPJS",
    }


def export_file(path: str):
    """Read one .dcm file and return (record, json_path). Writes the JSON next
    to the file."""
    ds = pydicom.dcmread(path, force=True)
    record = record_from_dataset(ds)
    json_path = os.path.splitext(path)[0] + ".json"
    with open(json_path, "w", encoding="utf8") as f:
        json.dump(record, f, indent=4, ensure_ascii=False)
    return record, json_path


def export_all(directory: str = "."):
    """Export every *.dcm in `directory`. Returns list of (path, record, json_path)."""
    results = []
    for path in sorted(glob.glob(os.path.join(directory, "*.dcm"))):
        record, json_path = export_file(path)
        results.append((path, record, json_path))
    return results
