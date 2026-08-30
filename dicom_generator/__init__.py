"""DICOM generator toolkit: engine, export, and web UI."""

__version__ = "1.0.0"

from dicom_generator.core import (
    apply_metadata,
    create_dicom_from_array,
    load_image_as_array,
)
from dicom_generator.engine import GenConfig, generate

__all__ = [
    "GenConfig",
    "generate",
    "create_dicom_from_array",
    "apply_metadata",
    "load_image_as_array",
    "__version__",
]
