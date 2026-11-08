#!/usr/bin/env bash
# Submit from the project root: sbatch slurm/vision.slurm
# Resources can be overridden with sbatch, for example:
#   sbatch --partition=debug --cpus-per-task=4 --mem=16G --time=01:00:00 slurm/vision.slurm
# Environment overrides:
#   PROJECT_DIR=/path/to/DiTOX CONFIG_FILE=config_tvm_vision.json CONDA_ENV=ditox-cuda sbatch slurm/vision.slurm

#SBATCH --job-name=ditox-vision
#SBATCH --partition=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=slurm/vision-%j.out
#SBATCH --error=slurm/vision-%j.err

set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="${PROJECT_DIR:-$(dirname "$script_dir")}"
project_dir="$(cd -- "$project_dir" && pwd)"
config_file="${CONFIG_FILE:-config_tvm_vision.json}"
conda_env="${CONDA_ENV:-ditox-cuda}"

if [[ "$config_file" != /* ]]; then
    config_file="$project_dir/$config_file"
fi

cd "$project_dir"
mkdir -p "$project_dir/result_tvm/slurm"
log_file="$project_dir/result_tvm/slurm/vision-${SLURM_JOB_ID:-manual}.log"
exec > >(tee -a "$log_file") 2>&1

printf 'Project: %s\nConfig: %s\n' "$project_dir" "$config_file"
printf 'Job: %s | CPUs: %s | Memory: %s | Time limit: %s\n' \
    "${SLURM_JOB_ID:-manual}" \
    "${SLURM_CPUS_PER_TASK:-32}" \
    "${SLURM_MEM_PER_NODE:-96000} MB" \
    "${SLURM_JOB_TIME_LIMIT:-08:00:00}"

# Lmod may reference LD_PRELOAD during initialization when nounset is enabled.
export LD_PRELOAD="${LD_PRELOAD-}"
if command -v module >/dev/null 2>&1; then
    module purge
    module load miniconda/3.0
fi

if ! command -v conda >/dev/null 2>&1; then
    export PATH="${CONDA_INSTALL_DIR:-$HOME/.local/miniforge3}/bin:$PATH"
fi
if ! command -v conda >/dev/null 2>&1; then
    printf 'Error: Conda is unavailable. Initialize Conda or load miniconda/3.0.\n' >&2
    exit 1
fi

eval "$(conda shell.bash hook)"
conda activate "$conda_env"

if [[ ! -s "$config_file" ]]; then
    printf 'Error: config file is missing or empty: %s\n' "$config_file" >&2
    exit 1
fi
if [[ ! -s "$project_dir/models_manifest.json" ]]; then
    printf 'Error: model manifest is missing: %s\n' "$project_dir/models_manifest.json" >&2
    exit 1
fi

python - "$config_file" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as config_file:
    config = json.load(config_file)

if config.get("general", {}).get("backend") != "tvmr":
    raise SystemExit("Error: the vision Slurm job requires the TVM backend (tvmr).")
images = config.get("images", {})
if images.get("images_chunk", 0) <= 0 or images.get("limit", 0) <= 0:
    raise SystemExit("Error: images.images_chunk and images.limit must be positive.")
print(
    "TVM vision config validated: "
    f"{images['limit']} images in chunks of {images['images_chunk']}."
)
PY

shopt -s nullglob
coco_images=("$project_dir"/images/COCO/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].jpg)
if (( ${#coco_images[@]} != 5000 )); then
    printf 'Error: expected 5,000 COCO val2017 images in %s/images/COCO; found %s.\n' \
        "$project_dir" "${#coco_images[@]}" >&2
    exit 1
fi

threads="${SLURM_CPUS_PER_TASK:-32}"
export TVM_NUM_THREADS="${TVM_NUM_THREADS:-$threads}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-$threads}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-$threads}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-$threads}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-$threads}"
export TF_NUM_INTRAOP_THREADS="${TF_NUM_INTRAOP_THREADS:-$threads}"
export TF_NUM_INTEROP_THREADS="${TF_NUM_INTEROP_THREADS:-$threads}"

printf 'Running on %s with TVM_NUM_THREADS=%s\n' "$(hostname)" "$TVM_NUM_THREADS"
srun --ntasks=1 --cpus-per-task="$threads" \
    python -u "$project_dir/main.py" "$config_file"

printf 'Vision run completed successfully.\n'
