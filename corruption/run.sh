#!/bin/bash

#SBATCH --mail-user=cokite@umich.edu
#SBATCH --mail-type=ALL
#SBATCH --partition=standard     
#SBATCH --time=48:10:00
#SBATCH --mem=8G
# SBATCH --account=mihalcea_owned1 # cse692w25_class # mihalcea_owned1 # mihalcea98 # chaijy2  # mihalcea98 # mihalcea_owned1

model_path="Qwen/Qwen3.5-27B-FP8"
session_path="sessions_summary_Qwen_Qwen3.5-27B-FP8_plain_fairness_4_20_200.json"



#  "anecdote" "emotion", 'none'
# Load modules
module load python/3.11.5
source .venv/bin/activate 


python -m corruption.build_main \
    --model_path ${model_path} \
    --session_path ${session_path}