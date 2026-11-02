"""Shared pipeline paths; output directories are created when a stage writes them."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
DATA_DIR = Path(os.getenv("AGENTS_WILD_DATA_DIR", "data")).expanduser()
if not DATA_DIR.is_absolute():
    DATA_DIR = ROOT / DATA_DIR
SIMULATION_DIR = DATA_DIR / "simulations"
CORRUPTION_DIR = DATA_DIR / "corruptions"
EVAL_DIR = DATA_DIR / "evaluations"
DEFAULT_STYLE_TYPES = ["plain", "credibility", "anecdote"]


def safe_model_name(model_path: str) -> str:
    name = model_path.replace("/", "_")
    if not name or name in {".", ".."} or "\\" in name:
        raise ValueError("Model name must identify a model, not a directory")
    return name


def model_data_dir(root: Path, model_path: str) -> Path:
    path = root / safe_model_name(model_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def simulation_model_dir(model_path: str) -> Path:
    return model_data_dir(SIMULATION_DIR, model_path)


def corruption_model_dir(corruption_type: str, model_path: str) -> Path:
    return model_data_dir(CORRUPTION_DIR / corruption_type, model_path)


def evaluation_model_dir(family: str, model_path: str) -> Path:
    return model_data_dir(EVAL_DIR / family, model_path)
