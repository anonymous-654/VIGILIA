"""Validate corruption checkpoints against their inputs and generation settings."""

import hashlib
import json
import os
from pathlib import Path

from core.json_io import save_json

ROOT = Path(__file__).resolve().parents[1]


def prepare_checkpoint(manifest, input_path, parameters, artifacts, resume):
    code = [ROOT / "config.py", ROOT / "schemas.py", ROOT / "enums.py"]
    for package in ("core", "llm", "corruption"):
        code.extend((ROOT / package).rglob("*.py"))
    provenance = dict(
        input_sha256=hashlib.sha256(Path(input_path).read_bytes()).hexdigest(),
        parameters=parameters,
        code={
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(code)
        },
        environment={
            name: os.getenv(name)
            for name in (
                "AZUREOPENAI_ENDPOINT",
                "AZURE_API_VERSION",
                "AZURE_OPENAI_DEPLOYMENT",
                "AZURE_HELPER_DEPLOYMENT",
            )
        },
    )
    if any(path.exists() for path in artifacts):
        if not resume:
            raise ValueError(
                "Corruption outputs already exist; use --resume or a new input filename"
            )
        if not manifest.exists() or json.loads(manifest.read_text()) != provenance:
            raise ValueError(
                "Checkpoint inputs, parameters, code or helper settings differ; use a new input filename"
            )
    save_json(manifest, provenance)
