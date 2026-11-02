# VIGILIA: Interactive Evaluation of Robust Conversational Vigilance in Large Language Model Agents


## Overview

VIGILIA evaluates **conversational vigilance**: whether an agent appropriately
handles the epistemic status of others' claims without an explicit fact-checking
request. The paper instantiates this evaluation in simulated classrooms.


## Usage

### Setup

Use Python 3.11 or later on Linux or macOS. Run commands from the repository root.
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set credentials and endpoints in `.env`. Run local Qwen/Gemma teachers through
an OpenAI-compatible server, or use the Claude, Gemini, or Azure routes.
For the paper's auxiliary models, set `AZURE_HELPER_DEPLOYMENT=gpt-4.1-mini`
and make an Azure deployment named `gpt-6-luna` available for critic review and
failure analysis. These stages make API calls.

### Data

Generate inputs using the commands below. Outputs are stored in:

| Stage | Directory |
|---|---|
| Simulation | `data/simulations/` |
| Corruption | `data/corruptions/` |
| Evaluation | `data/evaluations/` |
| Critic review | `evaluation_critic/results/` |
| Metrics | `metrics/results/` |
| Failure analysis | `failure_mode/results/` |


## Data Format

Session summaries and evaluations are JSON arrays. Key fields include:

| Field | Description |
|---|---|
| `session_id` | Classroom session identifier |
| `conversation_history` | Turns with speaker, action, segment, and utterance |
| `question_turn_index` | Zero-based question index in the conversation history |
| `counterfactual_wrong_answer` | Answer inserted during replay |
| `teacher_followup` | Teacher response to the inserted answer |
| `answer_eval` | Student answer verdict: `CORRECT` or `INCORRECT` |
| `teacher_epistemic_vigilance` | `high`, `low`, or `withheld`; invalid evaluations are excluded |

Full schemas are defined in [schemas.py](schemas.py).

## Run Evaluation

Set the teacher model and run size. `RUNS=2` is a small trial; use `RUNS=70`
to cover the paper's seven subjects. Additional subjects are available in
[subjects.py](subjects.py).

```bash
MODEL='Qwen/Qwen3.8-27B'
RUNS=2
MODEL_KEY="${MODEL//\//_}"
STEM="sessions_summary_${MODEL_KEY}_4_${RUNS}_200"
SESSION="data/simulations/${MODEL_KEY}/${STEM}.json"
BASE="data/corruptions/main/${MODEL_KEY}/${STEM}_base_corruptions.json"
GROUPED="data/corruptions/main/${MODEL_KEY}/${STEM}_grouped_corruptions.json"
```

### 1. Simulate class

```bash
python -m classroom.simulate_class_session \
  --model_path "$MODEL" --num_runs "$RUNS" \
  --num_raisers 4 --max_turns 200 --num_workers 2
```

### 2. Generate corruptions

```bash
python -m corruption.build_main \
  --session_path "$SESSION" --model_path "$MODEL"
```

Use `--resume` to continue an interrupted corruption run.

For additional conditions, generate rewrites from the same base answers:

```bash
python -m corruption.build_language_phen \
  --base_corruptions_path "$BASE" --model_path "$MODEL" --degree 1
python -m corruption.dialect.build_dialect_phen \
  --base_corruptions_path "$BASE" --model_path "$MODEL"
python -m corruption.dialect_speaker.build_dialect_speaker \
  --base_corruptions_path "$BASE" --model_path "$MODEL"
```

### 3. Replay and evaluate vigilance

```bash
python -m vigilance.evaluate_vigilance \
  --session_path "$SESSION" --grouped_corruptions_path "$GROUPED"
```

The evaluator replaces each student answer and generates the teacher's response.
For each additional grouped corruption file printed in step 2, run:

```bash
python -m vigilance.evaluate_language_phen_vigilance \
  --session_path "$SESSION" --grouped_corruptions_path PATH_TO_GROUPED_FILE \
  --canonical_corruptions_path "$GROUPED"
```

### 4. Review evaluations

```bash
python -m evaluation_critic.run --model "$MODEL" --resume
```

The critic reviews answer correctness and teacher judgments. Finish this stage
before computing metrics or classifying failures.

### 5. Compute metrics

```bash
python -m metrics.compute "$MODEL" --source critic
```

| Metric | Definition |
|---|---|
| Vigilance Failure Rate (VFR) | Fraction of eligible incorrect-answer interactions labeled `low`; `high` and `withheld` count as non-failures |
| Pairwise Robustness Error Rate (PRER) | Fraction of matched interactions whose binary failure outcome changes between two realizations |
| ΔVFR(a, b) | VFR(b) − VFR(a) on matched interactions; positive values mean more failures under b |


### 6. Analyze failures

```bash
python -m failure_mode.run "$MODEL" --resume
python -m failure_mode.aggregate
python -m metrics.plots
```

Classifies critic-reviewed plain baseline failures and generates aggregate plots.
Reported categories are **error adoption and propagation**, **selective
verification**, **conclusion anchoring**, **inaccurate correction**, and **other**.

For the paper's analysis of vigilance across interaction positions, run:

```bash
python -m position_analysis.run "$MODEL"
```
