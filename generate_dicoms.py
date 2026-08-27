import os
import sys
import datetime
import json
try:
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.uid import generate_uid, ExplicitVRLittleEndian, PYDICOM_IMPLEMENTATION_UID
    from pydicom.tag import Tag
except Exception:
    # Install pydicom if missing
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pydicom'])
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.uid import generate_uid, ExplicitVRLittleEndian, PYDICOM_IMPLEMENTATION_UID
    from pydicom.tag import Tag

outdir = r"C:\Users\mantr\Documents\pythondicom\generated_dicoms"
os.makedirs(outdir, exist_ok=True)

today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)

template = {
    "PatientID": "5456403",
    "PatientName": "DUMMY PATIENT FOUR",
    "PatientSex": "F",
    "PatientBirthDate": "19951125",
    "AccessionNumber": "0987654321123433",
    "RequestedProcedureID": "REQ-5555502",
    "RequestedProcedureDescription": "CT TEST",
    "Modality": "CT",
    "ScheduledStationAETitle": "ct_pro",
    "ReferringPhysicianName": "DR DUMMY",
    "Location": "ICU",
    "Department": "UGD",
    "Institution": "RS Dummy",
    "Guarantor": "BPJS"
}

all_entries = []

for i in range(10):
    # First 5 -> today, next 5 -> yesterday
    if i < 5:
        sched_date = today
    else:
        sched_date = yesterday
    filename = f"dummy_{sched_date.strftime('%Y%m%d')}_{i+1:02d}.dcm"
    path = os.path.join(outdir, filename)

    # File meta
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = generate_uid()
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID

    ds = FileDataset(path, {}, file_meta=file_meta, preamble=b"\0"*128)

    # Set metadata based on template, but ScheduledDate/Time vary
    ds.PatientID = template["PatientID"]
    ds.PatientName = template["PatientName"]
    ds.PatientSex = template["PatientSex"]
    ds.PatientBirthDate = template["PatientBirthDate"]
    ds.AccessionNumber = template["AccessionNumber"]
    ds.RequestedProcedureID = template["RequestedProcedureID"]
    ds.RequestedProcedureDescription = template["RequestedProcedureDescription"]
    ds.Modality = template["Modality"]
    ds.ScheduledDate = sched_date.strftime("%Y%m%d")
    # Use a stable scheduled time per file (HHMMSS)
    ds.ScheduledTime = (datetime.datetime.now() - datetime.timedelta(seconds=i*60)).strftime('%H%M%S')
    ds.ScheduledStationAETitle = template["ScheduledStationAETitle"]
    ds.ReferringPhysicianName = template["ReferringPhysicianName"]
    # Standard tag for Institution
    ds.InstitutionName = template["Institution"]
    # Put other non-standard fields into private tags to preserve them in the file
    # Use private creator and private element
    priv_creator_tag = Tag(0x0043, 0x0010)  # private creator
    try:
        ds.add_new(priv_creator_tag, 'LO', 'GENERATOR')
        ds.add_new(Tag(0x0043, 0x1010), 'LO', template['Location'])
        ds.add_new(Tag(0x0043, 0x1011), 'LO', template['Department'])
        ds.add_new(Tag(0x0043, 0x1012), 'LO', template['Guarantor'])
    except Exception:
        # If adding private tags fails, ignore - we'll still write JSON from the template
        pass

    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Save DICOM
    ds.save_as(path, write_like_original=False)

    # Build JSON entry (derived from what we set)
    entry = {
        "PatientID": str(ds.PatientID),
        "PatientName": str(ds.PatientName),
        "PatientSex": str(ds.PatientSex),
        "PatientBirthDate": str(ds.PatientBirthDate),
        "AccessionNumber": str(ds.AccessionNumber),
        "RequestedProcedureID": str(ds.RequestedProcedureID),
        "RequestedProcedureDescription": str(ds.RequestedProcedureDescription),
        "Modality": str(ds.Modality),
        "ScheduledDate": str(ds.ScheduledDate),
        "ScheduledTime": str(ds.ScheduledTime),
        "ScheduledStationAETitle": str(ds.ScheduledStationAETitle),
        "ReferringPhysicianName": str(ds.ReferringPhysicianName),
        "Location": template['Location'],
        "Department": template['Department'],
        "Institution": template['Institution'],
        "Guarantor": template['Guarantor'],
        "DicomFile": path
    }

    # write per-file json
    json_path = os.path.splitext(path)[0] + '.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(entry, f, ensure_ascii=False, indent=4)

    all_entries.append(entry)

# write combined JSON
combined_path = os.path.join(outdir, 'all_metadata.json')
with open(combined_path, 'w', encoding='utf-8') as f:
    json.dump(all_entries, f, ensure_ascii=False, indent=4)

print(f"Created {len(all_entries)} DICOM files in: {outdir}")
print(f"Per-file JSON created alongside each DICOM and combined JSON at: {combined_path}")
