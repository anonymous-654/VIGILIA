#!/bin/bash

#SBATCH --mail-user=cokite@umich.edu
#SBATCH --mail-type=ALL
#SBATCH --partition=standard     
#SBATCH --time=120:10:00
#SBATCH --mem=8G
# SBATCH --account=mihalcea_owned1 # cse692w25_class # mihalcea_owned1 # mihalcea98 # chaijy2  # mihalcea98 # mihalcea_owned1

# model="gpt-4o-mini", # "gpt-4-32k", # model = "deployment_name".
# model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
# model="gpt-4.1-mini",

# model_path="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
# model_path="Qwen/Qwen3-32B"
model_path="Qwen/Qwen3.5-27B-FP8"
num_runs=20
profile_type="plain"
# profile_type="position"
max_turns=200
eval_type="fairness"
num_raisers=4

#  "anecdote" "emotion", 'none'
# Load modules
module load python/3.11.5
source .venv/bin/activate 


python -m classroom.main2 \
    --model_path ${model_path} \
    --num_runs ${num_runs} \
    --profile_type ${profile_type} \
    --max_turns ${max_turns} \
    --eval_type ${eval_type} \
    --num_raisers ${num_raisers}