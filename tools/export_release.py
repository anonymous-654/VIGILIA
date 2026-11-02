"""Export the reproducible paper pipeline without local experiments or outputs."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (
    "classroom",
    "core",
    "llm",
    "corruption",
    "vigilance",
    "evaluation_critic",
    "metrics",
    "failure_mode",
    "position_analysis",
)
EXCLUDED = {
    "streamlit_app.py",
    "prompts_old.py",
    "recover_main.py",
    "stats.py",
    "review_vigilance.py",
    "review_pipeline.py",
    "rejudge_pipeline.py",
    "critic.py",
    "run_stats.sh",
    "run_critic.sh",
    "CRITIC.md",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists():
        parser.error("Destination must not exist; exports never overwrite files")
    if destination == ROOT or ROOT in destination.parents:
        parser.error("Choose a destination outside the working repository")
    files = [
        ROOT / name
        for name in (
            "README.md",
            "requirements.txt",
            ".gitignore",
            ".env.example",
            "config.py",
            "schemas.py",
            "enums.py",
            "subjects.py",
        )
    ]
    for package in PACKAGES:
        for path in (ROOT / package).rglob("*"):
            if (
                path.is_file()
                and path.suffix in {".py", ".sh", ".md"}
                and len(path.relative_to(ROOT / package).parts) <= 2
                and not any(
                    part
                    in {
                        "results",
                        "pilot",
                        "pilot_inputs",
                        "audits",
                        "aggregation",
                        "__pycache__",
                    }
                    for part in path.parts
                )
                and path.name not in EXCLUDED
            ):
                files.append(path)
    files.extend((ROOT / "tests").glob("test_*.py"))
    files.append(ROOT / "tests/__init__.py")
    files.extend((ROOT / "docs").glob("*.md"))
    files.append(ROOT / "core/liwc_categories_exclusive.json")
    files.append(Path(__file__).resolve())
    for source in files:
        target = destination / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(f"Exported {len(files)} source files to {destination}")


if __name__ == "__main__":
    main()
