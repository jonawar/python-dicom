"""Central path resolution for the project."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_ROOT = PROJECT_ROOT / "output"
DEFAULT_OUTPUT_NAME = "generated_dicoms"


def resolve_output_dir(name: str = DEFAULT_OUTPUT_NAME) -> Path:
    """Resolve an output folder name to an absolute path.

    Relative names live under OUTPUT_ROOT. Absolute paths must stay inside
    the project root. Creates the folder on success.
    """
    raw = (name or "").strip() or DEFAULT_OUTPUT_NAME
    candidate = Path(raw)
    base = candidate if candidate.is_absolute() else OUTPUT_ROOT / candidate
    base = base.resolve()
    root = PROJECT_ROOT.resolve()
    if base != root and root not in base.parents:
        raise ValueError("Output folder harus berada di dalam folder project")
    base.mkdir(parents=True, exist_ok=True)
    return base
