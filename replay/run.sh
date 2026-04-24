#!/bin/bash

#SBATCH --mail-user=cokite@umich.edu
#SBATCH --mail-type=ALL
#SBATCH --partition=standard     
#SBATCH --time=48:10:00
#SBATCH --mem=8G
# SBATCH --account=mihalcea_owned1 # cse692w25_class # mihalcea_owned1 # mihalcea98 # chaijy2  # mihalcea98 # mihalcea_owned1

model_path="Qwen/Qwen3.5-27B-FP8"
session_path="sessions_summary_Qwen_Qwen3.5-27B-FP8_plain_fairness_4_20_200.json"
target_profile_type="gender"
target_group="male_coded"

num_raisers=4
num_workers=2


module load python/3.11.5
source .venv/bin/activate 


python -m replay.replay_sessions \
  --session_path ${session_path} \
  --target_profile_type ${target_profile_type} \
  --model_path ${model_path} \
  --num_raisers ${num_raisers} \
  --num_workers ${num_workers} \
  --target_group ${target_group}
  