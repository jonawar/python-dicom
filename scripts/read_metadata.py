#!/usr/bin/env python3
"""Print all DICOM tags of a file (formerly readmetadata.py).

Usage:
    python scripts/read_metadata.py output/generated_dicoms/dicom_xxx.dcm
"""
import sys

import _bootstrap  # noqa: F401
import pydicom

if len(sys.argv) < 2:
    print("Usage: python scripts/read_metadata.py <file.dcm>")
    raise SystemExit(1)

ds = pydicom.dcmread(sys.argv[1])
print(ds)
