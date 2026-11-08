#!/usr/bin/env bash
# Submit from the project root: sbatch slurm/vision.slurm
# Or from slurm/: sbatch vision.slurm
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
#SBATCH --output=vision-%j.out
#SBATCH --error=vision-%j.err

set -Eeuo pipefail
conda_env="${CONDA_ENV:-ditox-cuda}"
conda_env_prefix="${CONDA_ENV_PREFIX:-}"
conda_install_dir="${CONDA_INSTALL_DIR:-$HOME/.local/miniforge3}"

submit_dir="${SLURM_SUBMIT_DIR:-$PWD}"
if [[ -n "${PROJECT_DIR:-}" ]]; then
    project_dir="$PROJECT_DIR"
elif [[ -f "$submit_dir/main.py" ]]; then
    project_dir="$submit_dir"
elif [[ -f "$submit_dir/../main.py" ]]; then
    project_dir="$submit_dir/.."
else
    printf 'Error: could not locate the DiTOX project root from %s. Set PROJECT_DIR explicitly.\n' \
        "$submit_dir" >&2
    exit 1
fi
project_dir="$(cd -- "$project_dir" && pwd)"
config_file="${CONFIG_FILE:-config_tvm_vision.json}"

if [[ "$config_file" != /* ]]; then
    config_file="$project_dir/$config_file"
fi

cd "$project_dir"
if [[ ! -s "$project_dir/main.py" ]]; then
    printf 'Error: main.py was not found in project root %s.\n' "$project_dir" >&2
    exit 1
fi
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
    if ! module load miniconda/3.0; then
        printf 'Warning: miniconda/3.0 module is unavailable; checking local Conda.\n' >&2
    fi
fi

if ! command -v conda >/dev/null 2>&1; then
    if [[ -x "$conda_install_dir/bin/conda" ]]; then
        export PATH="$conda_install_dir/bin:$PATH"
        hash -r
    fi
fi

if ! command -v conda >/dev/null 2>&1; then
    printf 'Error: Conda is unavailable. Run setup.sh first or set CONDA_INSTALL_DIR.\n' >&2
    exit 1
fi

find_prefix_from_conda() {
    local conda_command="$1"
    local candidate

    candidate="$("$conda_command" env list 2>/dev/null \
        | awk -v env="$conda_env" '$1 == env { print $NF; exit }' || true)"
    if [[ -n "$candidate" && -x "$candidate/bin/python" ]]; then
        printf '%s\n' "$candidate"
        return 0
    fi
    return 1
}

if [[ -n "$conda_env_prefix" ]]; then
    if [[ ! -x "$conda_env_prefix/bin/python" ]]; then
        printf 'Error: CONDA_ENV_PREFIX does not contain an environment Python: %s\n' \
            "$conda_env_prefix" >&2
        exit 1
    fi
else
    conda_env_prefix="$(find_prefix_from_conda conda || true)"

    default_env_prefix="$HOME/.conda/envs/$conda_env"
    if [[ -z "$conda_env_prefix" && -x "$default_env_prefix/bin/python" ]]; then
        conda_env_prefix="$default_env_prefix"
    fi

    if [[ -z "$conda_env_prefix" && -f "$HOME/.conda/environments.txt" ]]; then
        while IFS= read -r candidate; do
            if [[ "${candidate##*/}" == "$conda_env" \
                && -x "$candidate/bin/python" ]]; then
                conda_env_prefix="$candidate"
                break
            fi
        done < "$HOME/.conda/environments.txt"
    fi

    local_conda="$conda_install_dir/bin/conda"
    if [[ -z "$conda_env_prefix" && -x "$local_conda" ]]; then
        conda_env_prefix="$(find_prefix_from_conda "$local_conda" || true)"
    fi

    if [[ -z "$conda_env_prefix" ]]; then
        printf 'Error: Conda environment "%s" was not found.\n' "$conda_env" >&2
        printf 'Checked default environment prefix: %s\n' "$default_env_prefix" >&2
        printf 'Conda selected from PATH: %s\n' "$(command -v conda)" >&2
        printf 'Environments visible to that Conda installation:\n' >&2
        conda env list >&2 || true
        if [[ -f "$HOME/.conda/environments.txt" ]]; then
            printf 'Registered Conda environment prefixes:\n' >&2
            cat "$HOME/.conda/environments.txt" >&2
        fi
        if [[ -x "$local_conda" ]]; then
            printf 'Environments visible to local Conda at %s:\n' "$conda_install_dir" >&2
            "$local_conda" env list >&2 || true
        fi
        printf 'Run bash setup.sh with the same account, or set CONDA_ENV_PREFIX to the existing environment prefix.\n' >&2
        exit 1
    fi
fi

printf 'Using Conda environment %s at %s.\n' "$conda_env" "$conda_env_prefix"

eval "$(conda shell.bash hook)"
conda activate "$conda_env_prefix"
printf 'Conda environment: %s\nConda executable: %s\n' \
    "$CONDA_PREFIX" "$(command -v conda)"

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
