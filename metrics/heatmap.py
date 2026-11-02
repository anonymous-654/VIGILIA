"""Regenerate the across-model baseline-versus-realization PRER comparison."""

import argparse
import csv
import html
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUDE_PHENOMENA = ["emotion", "tentative", "negative_concord"]


def normalize(value):
    return re.sub(r"[\s_/-]+", "_", value.strip().lower())


def model_label(model):
    model = model.split("/")[-1]
    model = re.sub(r"^(google|qwen|anthropic|openai)_", "", model, flags=re.I)
    return re.sub(r"(claude-haiku-4-5)-\d+$", r"\1", model)


def add_filter_args(parser):
    parser.add_argument(
        "--exclude-models",
        nargs="*",
        default=None,
        help="Model IDs or short names to omit from heatmap",
    )
    parser.add_argument(
        "--exclude-phenomena",
        nargs="*",
        default=DEFAULT_EXCLUDE_PHENOMENA,
        help="Realizations to omit; pass without values to include all",
    )


GROUPS = [
    ("main", "Rhetorical Framing"),
    ("language_phen", "Linguistic phenomena"),
    ("dialect_phen", "Dialect Phenomena"),
    ("dialect_speaker", "Dialect rewrite"),
]


def collect(results_root, exclude_models=None, exclude_phenomena=None):
    excluded_models = {normalize(m) for m in (exclude_models or [])}
    excluded_phenomena = {
        normalize(p)
        for p in (
            DEFAULT_EXCLUDE_PHENOMENA
            if exclude_phenomena is None
            else exclude_phenomena
        )
    }
    models, sources = [], {}
    cells = defaultdict(lambda: [0, 0])
    for path in sorted(results_root.glob("*/pairwise.csv")):
        model = path.parent.name
        if (
            normalize(model) in excluded_models
            or normalize(model_label(model)) in excluded_models
        ):
            continue
        models.append(model)
        manifest = path.parent / "manifest.json"
        sources[model] = (
            json.loads(manifest.read_text()).get("input_source", "unknown")
            if manifest.exists()
            else "unknown"
        )
        with path.open() as handle:
            for row in csv.DictReader(handle):
                family = row["family"]
                if family not in dict(GROUPS):
                    continue
                a, b = row["label_a"], row["label_b"]
                baseline = "plain" if family == "main" else "baseline"
                if baseline not in (a, b):
                    continue
                other = b if a == baseline else a
                if normalize(other) in excluded_phenomena:
                    continue
                degree = re.search(
                    r"_(degree\d+)_language_phen_vigilance_eval$", row["evaluation"]
                )
                variant = degree.group(1) if degree else ""
                if family == "language_phen" and variant != "degree1":
                    continue
                key = (family, variant, other, model)
                cells[key][0] += int(row["n_changed_outcomes"])
                cells[key][1] += int(row["n_pairs"])
    keys = sorted(
        {key[:3] for key in cells},
        key=lambda k: ([x[0] for x in GROUPS].index(k[0]), k[1], k[2]),
    )
    return models, sources, cells, keys


def label(key):
    return key[2].replace("_", " ").capitalize()


def generate_heatmap(
    results_root=ROOT / "metrics/results", exclude_models=None, exclude_phenomena=None
):
    models, sources, cells, keys = collect(
        results_root, exclude_models, exclude_phenomena
    )
    if not models:
        return None
    target = results_root / "comparison"
    target.mkdir(parents=True, exist_ok=True)
    note = "Baseline-versus-realization PRER (%). Lower indicates greater robustness; darker red indicates more changed failure outcomes. Missing/no matched pairs are shown as —. Only degree-1 linguistic phenomena are included. Multiple evaluation runs for the same row are pooled by matched-pair counts."

    def esc(value):
        return html.escape(str(value))

    parts = [
        '<!doctype html><html><head><meta charset="utf-8"><title>Baseline PRER across models</title><style>body{font:15px system-ui;margin:32px;color:#18212b}table{border-collapse:collapse}th,td{padding:12px;border:1px solid #ddd;text-align:center}thead th{position:sticky;top:0;background:white}tbody th{text-align:left;min-width:250px}.group th{background:#e9eef5;font-size:18px}td{min-width:130px}small{display:block;font-weight:normal;color:#555}p{max-width:1000px}</style></head><body><h1>Baseline PRER across models</h1>',
        f"<p>{esc(note)}</p><table><thead><tr><th>Realization</th>",
    ]
    parts.extend(
        f"<th>{esc(model_label(m))}<small>Source: {esc(sources[m])}</small></th>"
        for m in models
    )
    parts.append("</tr></thead><tbody>")
    flat = []
    for family, title in GROUPS:
        parts.append(
            f'<tr class="group"><th colspan="{len(models)+1}">{title}</th></tr>'
        )
        for key in [k for k in keys if k[0] == family]:
            parts.append(f"<tr><th>{esc(label(key))}</th>")
            for model in models:
                changed, n = cells.get((*key, model), (0, 0))
                rate = changed / n if n else None
                flat.append(
                    dict(
                        group=title,
                        degree=key[1],
                        realization=key[2],
                        model=model,
                        input_source=sources[model],
                        n_changed=changed,
                        n_pairs=n,
                        prer=rate,
                    )
                )
                if rate is None:
                    parts.append('<td style="background:#eee">—</td>')
                else:
                    color = f"rgb(255,{round(255-190*rate)},{round(255-210*rate)})"
                    parts.append(
                        f'<td style="background:{color}" title="{changed} changed / {n} matched pairs">{100*rate:.1f}<small>n={n}</small></td>'
                    )
            parts.append("</tr>")
    parts.append("</tbody></table></body></html>")
    (target / "baseline_prer_heatmap.html").write_text("".join(parts))
    with (target / "baseline_prer.csv").open("w", newline="") as handle:
        fields = [
            "group",
            "degree",
            "realization",
            "model",
            "input_source",
            "n_changed",
            "n_pairs",
            "prer",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(flat)
    # Standalone figure for Markdown reports and export.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    display = []
    for family, title in GROUPS:
        display.append((None, title))
        display.extend((k, label(k)) for k in keys if k[0] == family)
    data = np.full((len(display), len(models)), np.nan)
    for i, (key, _) in enumerate(display):
        if key is not None:
            for j, m in enumerate(models):
                changed, n = cells.get((*key, m), (0, 0))
                if n:
                    data[i, j] = 100 * changed / n
    fig, ax = plt.subplots(
        figsize=(max(12, len(models) * 2.6), len(display) * 0.43 + 3)
    )
    cmap = plt.get_cmap("Reds").copy()
    cmap.set_bad("#ededed")
    im = ax.imshow(
        np.ma.masked_invalid(data), cmap=cmap, vmin=0, vmax=100, aspect="auto"
    )
    ax.set_xticks(
        range(len(models)), [model_label(m) for m in models], rotation=20, ha="left"
    )
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(display)), [name for _, name in display])
    for i, (key, title) in enumerate(display):
        if key is None:
            ax.axhspan(i - 0.5, i + 0.5, color="#dce5f0")
            ax.get_yticklabels()[i].set_weight("bold")
        else:
            for j in range(len(models)):
                value = data[i, j]
                ax.text(
                    j,
                    i,
                    "—" if np.isnan(value) else f"{value:.1f}",
                    ha="center",
                    va="center",
                    color="white" if value > 60 else "#222",
                    fontsize=10,
                )
    fig.colorbar(im, ax=ax, label="PRER (%)", fraction=0.025, pad=0.02)
    fig.tight_layout()
    fig.savefig(target / "baseline_prer_heatmap.png", dpi=180)
    fig.savefig(target / "baseline_prer_heatmap.svg")
    fig.savefig(target / "baseline_prer_heatmap.pdf", bbox_inches="tight")
    plt.close(fig)
    lines = [
        "# Baseline PRER across models",
        "",
        note,
        "",
        "![Baseline PRER heatmap](baseline_prer_heatmap.png)",
        "",
        "[Paper PDF](baseline_prer_heatmap.pdf)",
        "",
        "[Interactive table with matched-pair counts](baseline_prer_heatmap.html)",
        "",
        "Evaluation sources:",
        "",
    ]
    lines.extend(f"- {m}: `{sources[m]}`" for m in models)
    (target / "report.md").write_text("\n".join(lines) + "\n")
    from metrics.directional import generate_directional

    generate_directional(results_root, exclude_models, exclude_phenomena)
    with (target / "report.md").open("a") as handle:
        handle.write(
            "\n[Directional ΔVFR table](directional_contrasts.md) · [LaTeX](directional_contrasts.tex) · [CSV](directional_contrasts.csv)\n"
        )
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=ROOT / "metrics/results")
    add_filter_args(parser)
    args = parser.parse_args()
    print(
        generate_heatmap(args.results_root, args.exclude_models, args.exclude_phenomena)
    )
