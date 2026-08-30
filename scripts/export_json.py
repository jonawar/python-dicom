#!/usr/bin/env python3
"""Export .dcm files to radiology-table JSON (formerly export_text.py).

Usage:
    python scripts/export_json.py [folder]     # default: output/generated_dicoms
"""
import json
import sys

import _bootstrap

from dicom_generator import exporter


def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else str(
        _bootstrap.output_dir("generated_dicoms"))
    results = exporter.export_all(directory)
    if not results:
        print(f"Tidak ada file .dcm di {directory}")
        return
    for path, record, json_path in results:
        print(f"{path} -> {json_path}")
        print(json.dumps(record, indent=4, ensure_ascii=False))
        print()


if __name__ == "__main__":
    main()
