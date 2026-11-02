"""Discover original or full-run Luna-reviewed evaluation files without mixing sources."""


def discover_inputs(model, source, data_root, critic_root, session_stem=None):
    inputs = []
    if source == "original":
        for family in ("main", "language_phen", "dialect_phen", "dialect_speaker"):
            for path in sorted(
                (data_root / family / model).glob("*_vigilance_eval.json")
            ):
                if "_replayed_" not in path.name:
                    inputs.append((family, path, path.stem))
    else:
        # Direct children select full-run Luna outputs, excluding pilot and other critics.
        for path in sorted((critic_root / model).glob("*/reviewed_evaluations.json")):
            stem = path.parent.name
            if not stem.endswith("_vigilance_eval") or "_replayed_" in stem:
                continue
            family = "main"
            for candidate in ("language_phen", "dialect_phen", "dialect_speaker"):
                if stem.endswith("_" + candidate + "_vigilance_eval"):
                    family = candidate
                    break
            inputs.append((family, path, stem))
    return [
        item
        for item in inputs
        if not session_stem or item[2].startswith(session_stem + "_")
    ]
