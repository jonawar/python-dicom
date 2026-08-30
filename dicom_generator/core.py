"""Low-level DICOM file creation (formerly create-dicom.py)."""
from datetime import datetime

import numpy as np
from PIL import Image
from pydicom.dataset import Dataset as PydDataset
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import (
    ExplicitVRLittleEndian,
    SecondaryCaptureImageStorage,
    generate_uid,
)


def _now_dates():
    dt = datetime.now()
    return dt.strftime("%Y%m%d"), dt.strftime("%H%M%S")


def create_dicom_from_array(filename: str, arr: np.ndarray,
                            patient_name="Anon^Patient", patient_id="0000",
                            modality: str = "CT", series_description="Generated",
                            study_uid=None, series_uid=None, sop_uid=None,
                            metadata: dict = None):
    if arr.ndim == 2:
        rows, cols = arr.shape
        samples_per_pixel = 1
        photometric = "MONOCHROME2"
        planar_configuration = None
    elif arr.ndim == 3 and arr.shape[2] == 3:
        rows, cols = arr.shape[0], arr.shape[1]
        samples_per_pixel = 3
        photometric = "RGB"
        planar_configuration = 0
    else:
        raise ValueError("Unsupported array shape. Use 2D grayscale or HxWx3 RGB.")

    if arr.dtype == np.uint8:
        bits_alloc = 8
        pixel_rep = 0
    elif arr.dtype == np.uint16:
        bits_alloc = 16
        pixel_rep = 0
    elif arr.dtype in (np.float32, np.float64):
        arr = (arr - arr.min()) / (arr.max() - arr.min()) * 255
        arr = arr.astype(np.uint8)
        bits_alloc = 8
        pixel_rep = 0
    else:
        arr = arr.astype(np.uint8)
        bits_alloc = 8
        pixel_rep = 0

    file_meta = FileMetaDataset()
    sop_uid = sop_uid or generate_uid()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)

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

    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr)

    ds.PixelData = arr.tobytes()

    if metadata:
        apply_metadata(ds, metadata)

    ds.save_as(filename, write_like_original=False)
    return ds


def apply_metadata(ds, tags: dict):
    """Apply a dict of tags into the dataset. Supports nested
    ScheduledProcedureStepSequence as a list of dicts."""
    if not tags:
        return
    for key, val in tags.items():
        if key == "ScheduledProcedureStepSequence" and isinstance(val, list):
            items = []
            for item in val:
                item_ds = PydDataset()
                for ik, iv in item.items():
                    setattr(item_ds, ik, iv)
                items.append(item_ds)
            ds.ScheduledProcedureStepSequence = Sequence(items)
        else:
            setattr(ds, key, val)


def load_image_as_array(path: str, as_gray=False, target_bits=8):
    im = Image.open(path)
    if as_gray:
        im = im.convert("L")
    elif im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    arr = np.array(im)
    if target_bits == 16 and arr.dtype == np.uint8:
        arr = arr.astype(np.uint16) << 8
    return arr


def synthetic_array(width: int = 256, height: int = 256,
                    style: str = "gradient", bits: int = 8) -> np.ndarray:
    if style == "noise":
        if bits == 16:
            return np.random.randint(0, 2 ** 16, (height, width), dtype=np.uint16)
        return np.random.randint(0, 256, (height, width), dtype=np.uint8)
    max_val = 2 ** bits - 1
    dtype = np.uint16 if bits == 16 else np.uint8
    x = np.linspace(0, max_val, width, dtype=dtype)
    return np.tile(x, (height, 1))
