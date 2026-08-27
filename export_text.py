import pydicom
import json
import os
import glob

FILES = sorted(glob.glob("*.dcm"))

def pval(val):
    if val is None:
        return ""
    return str(val)

def get_seq_attr(sps, attr, default=""):
    try:
        return pval(getattr(sps[0], attr, default))
    except (IndexError, AttributeError):
        return default

for fpath in FILES:
    ds = pydicom.dcmread(fpath, force=True)
    sps = getattr(ds, "ScheduledProcedureStepSequence", None) or []

    record = {
        "PatientID": pval(getattr(ds, "PatientID", "")),
        "PatientName": pval(getattr(ds, "PatientName", "")),
        "PatientSex": pval(getattr(ds, "PatientSex", "")),
        "PatientBirthDate": pval(getattr(ds, "PatientBirthDate", "")),
        "AccessionNumber": pval(getattr(ds, "AccessionNumber", "")),
        "RequestedProcedureID": pval(getattr(ds, "RequestedProcedureID", "")),
        "RequestedProcedureDescription": pval(getattr(ds, "RequestedProcedureDescription", "")),
        "Modality": get_seq_attr(sps, "Modality", pval(getattr(ds, "Modality", ""))),
        "ScheduledDate": get_seq_attr(sps, "ScheduledProcedureStepStartDate"),
        "ScheduledTime": get_seq_attr(sps, "ScheduledProcedureStepStartTime"),
        "ScheduledStationAETitle": get_seq_attr(sps, "ScheduledStationAETitle"),
        "ReferringPhysicianName": pval(getattr(ds, "ReferringPhysicianName", "")),
        "Location": get_seq_attr(sps, "ScheduledProcedureStepLocation"),
        "Department": pval(getattr(ds, "InstitutionalDepartmentName", "")),
        "Institution": pval(getattr(ds, "InstitutionName", "RS Dummy")),
        "Guarantor": "BPJS"
    }

    basename = os.path.splitext(fpath)[0]
    outfile = f"{basename}.json"
    with open(outfile, "w", encoding="utf8") as f:
        json.dump(record, f, indent=4, ensure_ascii=False)
    print(f"{fpath} -> {outfile}")
    print(json.dumps(record, indent=4, ensure_ascii=False))
    print()
