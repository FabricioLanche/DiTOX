#!/usr/bin/env bash
# Submit from the project root: sbatch khipu/text_sentiment.slurm
# Config: configs/run/{complete|partial}/config_text_sentiment_explore.json
#         configs/run/config_text_sentiment_isolate.json
# Parameters (environment variables):
#   COMPLETE=true|false    complete/ (full) or partial/ (small) explore config
#   EXPLORE=true|false     explore or isolate config
#   MODEL_WORKERS=N        override runtime.tvm.model_workers
#   THREADS_PER_WORKER=N   override runtime.tvm.threads_per_worker (0 = auto)
#   PROJECT_DIR, CONDA_ENV, CONDA_ENV_PREFIX, CONDA_INSTALL_DIR
#
# Examples:
#   sbatch khipu/text_sentiment.slurm
#   COMPLETE=false MODEL_WORKERS=4 THREADS_PER_WORKER=8 sbatch khipu/text_sentiment.slurm
#   sbatch --export=ALL,EXPLORE=false khipu/text_sentiment.slurm

#SBATCH --job-name=ditox-text-sentiment
#SBATCH --partition=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=text-sentiment-%j.out
#SBATCH --error=text-sentiment-%j.err

set -Eeuo pipefail

COMPLETE="${COMPLETE:-true}"
EXPLORE="${EXPLORE:-true}"
MODEL_WORKERS="${MODEL_WORKERS:-4}"
THREADS_PER_WORKER="${THREADS_PER_WORKER:-8}"
FAMILY="text"
CONFIG_FAMILY="text_sentiment"
EXPECTED_BACKEND="tvmr"

submit_dir="${SLURM_SUBMIT_DIR:-$PWD}"
if [[ -n "${PROJECT_DIR:-}" ]]; then
    project_dir="$PROJECT_DIR"
elif [[ -f "$submit_dir/main.py" ]]; then
    project_dir="$submit_dir"
elif [[ -f "$submit_dir/../main.py" ]]; then
    project_dir="$submit_dir/.."
else
    printf 'Error: no se pudo localizar la raíz del proyecto desde %s. Define PROJECT_DIR.\n' \
        "$submit_dir" >&2
    exit 1
fi
project_dir="$(cd -- "$project_dir" && pwd)"
cd "$project_dir"

mkdir -p "$project_dir/results/slurm"
log_file="$project_dir/results/slurm/text_sentiment-${SLURM_JOB_ID:-manual}.log"
exec > >(tee -a "$log_file") 2>&1

# shellcheck source=khipu/common.sh
source "$project_dir/khipu/common.sh"

config_file="$(khipu_select_config "$CONFIG_FAMILY" "$COMPLETE" "$EXPLORE")"
printf 'Project: %s\nConfig: %s\nCOMPLETE=%s EXPLORE=%s\n' \
    "$project_dir" "$config_file" "$COMPLETE" "$EXPLORE"

khipu_activate_env
khipu_export_overrides "$MODEL_WORKERS" "$THREADS_PER_WORKER"
khipu_validate_config "$FAMILY" "$config_file" "$EXPECTED_BACKEND"
khipu_run_pipeline "$FAMILY" "$config_file"

printf 'Text sentiment run completed successfully.\n'
