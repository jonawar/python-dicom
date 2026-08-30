#!/usr/bin/env python3
"""Create a single DICOM file from an image, or a synthetic image.

Usage:
    python scripts/create_dicom.py --out pasien001.dcm --patient "Budi^Santoso" --id 123456 --metadata data/metadata.json
"""
import argparse
import json
import os

import _bootstrap  # noqa: F401

from dicom_generator.core import (
    create_dicom_from_array,
    load_image_as_array,
    synthetic_array,
)

DEFAULT_METADATA = _bootstrap.ROOT / "data" / "metadata.json"


def main():
    p = argparse.ArgumentParser(description="Create a simple DICOM file")
    p.add_argument("--out", required=True, help="Output DICOM filename (.dcm)")
    p.add_argument("--from-image", help="Path to image (png/jpg). If not set, a synthetic image is generated")
    p.add_argument("--width", type=int, default=256)
    p.add_argument("--height", type=int, default=256)
    p.add_argument("--bits", type=int, choices=(8, 16), default=8)
    p.add_argument("--style", choices=("gradient", "noise"), default="gradient")
    p.add_argument("--patient", default="Anon^Patient")
    p.add_argument("--id", default="0000")
    p.add_argument("--metadata", help="Path to JSON file or a JSON string containing a top-level 'Tags' object")
    args = p.parse_args()

    if args.from_image:
        arr = load_image_as_array(args.from_image, as_gray=False, target_bits=args.bits)
    else:
        arr = synthetic_array(args.width, args.height, args.style, args.bits)

    metadata = None
    meta_src = args.metadata or str(DEFAULT_METADATA)
    if meta_src:
        try:
            if os.path.exists(meta_src):
                with open(meta_src, "r", encoding="utf8") as f:
                    meta = json.load(f)
            else:
                meta = json.loads(meta_src)
            metadata = meta.get("Tags", meta)
        except Exception as e:
            raise RuntimeError(f"Failed to load metadata: {e}")

    ds = create_dicom_from_array(args.out, arr, patient_name=args.patient,
                                 patient_id=args.id, metadata=metadata)
    print("Wrote DICOM:", args.out)
    print(ds)


if __name__ == "__main__":
    main()
