"""Make the project root importable when running scripts directly:

    python scripts/<name>.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_ROOT = ROOT / "output"


def output_dir(sub: str = "") -> Path:
    d = OUTPUT_ROOT / sub if sub else OUTPUT_ROOT
    d.mkdir(parents=True, exist_ok=True)
    return d
