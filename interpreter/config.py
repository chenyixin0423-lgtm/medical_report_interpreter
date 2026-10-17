import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def data_dir() -> Path:
    return Path(os.environ.get("MRI_DATA_DIR", str(ROOT / ".local_data"))).resolve()


def model_name() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
