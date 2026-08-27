#!/usr/bin/env python3
"""
Simple utility to create a brand-new DICOM file from a NumPy array
or from an input image file.
"""
import argparse
from datetime import datetime
import numpy as np
from PIL import Image
import json
import os
import pydicom # noqa: F401
from pydicom.dataset import FileDataset, FileMetaDataset, Dataset as PydDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid, ExplicitVRLittleEndian, SecondaryCaptureImageStorage

def _now_dates():
    dt = datetime.now()
    return dt.strftime("%Y%m%d"), dt.strftime("%H%M%S")

def create_dicom_from_array(filename: str, arr: np.ndarray,
                            patient_name="Anon^Patient", patient_id="0000",
                            modality: str = "CT", series_description="Generated",
                            study_uid=None, series_uid=None, sop_uid=None,
                            metadata: dict = None):
    # Normalize and validate array
    if arr.ndim == 2:
        rows, cols = arr.shape
        samples_per_pixel = 1
        photometric = "MONOCHROME2"
        planar_configuration = None
    elif arr.ndim == 3 and arr.shape[2] == 3:
        rows, cols = arr.shape[0], arr.shape[1]
        samples_per_pixel = 3
        photometric = "RGB"
        planar_configuration = 0  # RGB by pixel
    else:
        raise ValueError("Unsupported array shape. Use 2D grayscale or HxWx3 RGB.")

    # Choose pixel format
    if arr.dtype == np.uint8:
        bits_alloc = 8
        pixel_rep = 0
    elif arr.dtype == np.uint16:
        bits_alloc = 16
        pixel_rep = 0
    elif arr.dtype == np.float32 or arr.dtype == np.float64:
        # Scale float images to 0-255 and convert to uint8
        arr = (arr - arr.min()) / (arr.max() - arr.min()) * 255
        arr = arr.astype(np.uint8)
        bits_alloc = 8
        pixel_rep = 0
    else:
        # Default to uint8 for other unsupported types
        arr = arr.astype(np.uint8)
        bits_alloc = 8
        pixel_rep = 0

    # Prepare File Meta
    file_meta = FileMetaDataset()
    sop_uid = sop_uid or generate_uid()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    # Build main dataset
    ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Required DICOM tags / basic ident
    study_uid = study_uid or generate_uid()
    series_uid = series_uid or generate_uid()

    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.Modality = metadata.get("Modality", modality) if metadata else modality
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.StudyDate, ds.StudyTime = _now_dates()
    ds.SeriesNumber = "1"
    ds.InstanceNumber = "1"
    ds.SeriesDescription = series_description

    # Image-specific attributes
    ds.SamplesPerPixel = samples_per_pixel
    ds.PhotometricInterpretation = photometric
    ds.Rows = rows
    ds.Columns = cols
    ds.BitsAllocated = bits_alloc
    ds.BitsStored = bits_alloc
    ds.HighBit = bits_alloc - 1
    ds.PixelRepresentation = pixel_rep
    if samples_per_pixel > 1:
        ds.PlanarConfiguration = planar_configuration

    # Ensure contiguous bytes
    if not arr.flags['C_CONTIGUOUS']:
        arr = np.ascontiguousarray(arr)

    ds.PixelData = arr.tobytes()

    # Apply optional metadata (JSON tags -> DICOM attributes)
    if metadata:
        apply_metadata(ds, metadata)

    # Save
    ds.save_as(filename, write_like_original=False)
    return ds

def apply_metadata(ds, tags: dict):
    """Apply a dict of Tags into the pydicom Dataset. Supports nested
    ScheduledProcedureStepSequence as a list of dicts."""
    if not tags:
        return
    for key, val in tags.items():
        if key == "ScheduledProcedureStepSequence" and isinstance(val, list):
            items = []
            for item in val:
                it_ds = PydDataset()
                for ik, iv in item.items():
                    setattr(it_ds, ik, iv)
                items.append(it_ds)
            ds.ScheduledProcedureStepSequence = Sequence(items)
        else:
            # simple mapping; pydicom will handle VRs for known tags
            setattr(ds, key, val)

def load_image_as_array(path: str, as_gray=False, target_bits=8):
    im = Image.open(path)
    if as_gray:
        im = im.convert("L")
    else:
        # convert color images to RGB if they contain alpha or different mode
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
    arr = np.array(im)
    # if target bits 16 convert scale
    if target_bits == 16 and arr.dtype == np.uint8:
        arr = (arr.astype(np.uint16) << 8)  # simple upscale
    return arr

def main():
    p = argparse.ArgumentParser(description="Create a simple DICOM file")
    p.add_argument("--out", required=True, help="Output DICOM filename (.dcm)")
    p.add_argument("--from-image", help="Path to image (png/jpg). If not set, a synthetic image is generated")
    p.add_argument("--width", type=int, default=256)
    p.add_argument("--height", type=int, default=256)
    p.add_argument("--bits", type=int, choices=(8,16), default=8)
    p.add_argument("--patient", default="Anon^Patient")
    p.add_argument("--id", default="0000")
    p.add_argument("--metadata", help="Path to JSON file or a JSON string containing a top-level 'Tags' object")
    args = p.parse_args()

    if args.from_image:
        arr = load_image_as_array(args.from_image, as_gray=False, target_bits=args.bits)
    else:
        # Create a gradient synthetic image
        max_val = 2**args.bits - 1
        x = np.linspace(0, max_val, args.width, dtype=np.uint16 if args.bits == 16 else np.uint8)
        arr = np.tile(x, (args.height, 1))
        # The dtype is already set by np.linspace, so explicit casting here is redundant
        # if args.bits == 16:
        #     arr = arr.astype(np.uint16)
        # else:
        #     arr = arr.astype(np.uint8)

    metadata = None
    if args.metadata:
        try:
            if os.path.exists(args.metadata):
                with open(args.metadata, "r", encoding="utf8") as f:
                    meta = json.load(f)
            else:
                meta = json.loads(args.metadata)
            metadata = meta.get("Tags", meta)
        except Exception as e:
            raise RuntimeError(f"Failed to load metadata: {e}")

    ds = create_dicom_from_array(args.out, arr, patient_name=args.patient, patient_id=args.id, metadata=metadata)
    print("Wrote DICOM:", args.out)
    print(ds)

if __name__ == "__main__":
    main()