#!/usr/bin/env bash
# Shared helpers for the khipu/*.slurm launchers.
# The sourcing script must set project_dir and call these functions.

khipu_fail() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

khipu_bool_value=""

khipu_normalize_bool() {
    case "${1,,}" in
        true|1|yes|y) khipu_bool_value="true" ;;
        false|0|no|n) khipu_bool_value="false" ;;
        *) khipu_fail "$2 debe ser true o false (recibido: '$1')." ;;
    esac
}

# EXPLORE=true resolves configs/run/{complete|partial}/config_<family>_explore.json.
# EXPLORE=false resolves the shared configs/run/config_<family>_isolate.json
# (falling back to the complete/partial directory when present).
khipu_select_config() {
    local family="$1"
    local config_dir config_mode config_file complete_value explore_value
    local -a candidates=()

    khipu_normalize_bool "$2" COMPLETE
    complete_value="$khipu_bool_value"
    if [[ "$complete_value" == "true" ]]; then
        config_dir="complete"
    else
        config_dir="partial"
    fi

    khipu_normalize_bool "$3" EXPLORE
    explore_value="$khipu_bool_value"
    if [[ "$explore_value" == "true" ]]; then
        config_mode="explore"
    else
        config_mode="isolate"
    fi

    candidates+=("configs/run/$config_dir/config_${family}_${config_mode}.json")
    candidates+=("configs/run/config_${family}_${config_mode}.json")

    for config_file in "${candidates[@]}"; do
        if [[ -s "$project_dir/$config_file" ]]; then
            printf '%s\n' "$config_file"
            return 0
        fi
    done

    khipu_fail "No existe config para familia=$family COMPLETE=$complete_value EXPLORE=$explore_value. Probé: ${candidates[*]}"
}

khipu_activate_env() {
    local conda_env="${CONDA_ENV:-ditox-cuda}"
    local conda_env_prefix="${CONDA_ENV_PREFIX:-}"
    local conda_install_dir="${CONDA_INSTALL_DIR:-$HOME/.local/miniforge3}"
    local candidate local_conda default_env_prefix

    export LD_PRELOAD="${LD_PRELOAD-}"
    if command -v module >/dev/null 2>&1; then
        module purge || true
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

    command -v conda >/dev/null 2>&1 \
        || khipu_fail "Conda no está disponible. Ejecuta khipu/setup.sh o define CONDA_INSTALL_DIR."

    find_prefix_from_conda() {
        local conda_command="$1"
        local prefix
        prefix="$("$conda_command" env list 2>/dev/null \
            | awk -v env="$conda_env" '$1 == env { print $NF; exit }' || true)"
        if [[ -n "$prefix" && -x "$prefix/bin/python" ]]; then
            printf '%s\n' "$prefix"
            return 0
        fi
        return 1
    }

    if [[ -n "$conda_env_prefix" ]]; then
        [[ -x "$conda_env_prefix/bin/python" ]] \
            || khipu_fail "CONDA_ENV_PREFIX no contiene un Python de entorno: $conda_env_prefix"
    else
        conda_env_prefix="$(find_prefix_from_conda conda || true)"
        default_env_prefix="$HOME/.conda/envs/$conda_env"
        if [[ -z "$conda_env_prefix" && -x "$default_env_prefix/bin/python" ]]; then
            conda_env_prefix="$default_env_prefix"
        fi
        if [[ -z "$conda_env_prefix" && -f "$HOME/.conda/environments.txt" ]]; then
            while IFS= read -r candidate; do
                if [[ "${candidate##*/}" == "$conda_env" && -x "$candidate/bin/python" ]]; then
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
            printf 'Conda environments visible to %s:\n' "$(command -v conda)" >&2
            conda env list >&2 || true
            khipu_fail "El entorno Conda '$conda_env' no existe. Ejecuta khipu/setup.sh con la misma cuenta o define CONDA_ENV_PREFIX."
        fi
    fi

    eval "$(conda shell.bash hook)"
    conda activate "$conda_env_prefix" \
        || khipu_fail "No se pudo activar el entorno Conda $conda_env_prefix."
    printf 'Conda environment: %s\n' "$CONDA_PREFIX"
    python -c 'import sys; print(sys.executable)' >/dev/null \
        || khipu_fail "Python no funciona dentro de $CONDA_PREFIX."
    export PYTHONUNBUFFERED=1
}

khipu_export_overrides() {
    local model_workers="$1"
    local threads_per_worker="$2"

    if [[ -n "$model_workers" ]]; then
        [[ "$model_workers" =~ ^[1-9][0-9]*$ ]] \
            || khipu_fail "MODEL_WORKERS debe ser un entero >= 1 (recibido: '$model_workers')."
        export DITOX_MODEL_WORKERS="$model_workers"
    else
        unset DITOX_MODEL_WORKERS
    fi

    if [[ -n "$threads_per_worker" ]]; then
        [[ "$threads_per_worker" =~ ^[0-9]+$ ]] \
            || khipu_fail "THREADS_PER_WORKER debe ser un entero >= 0 (recibido: '$threads_per_worker')."
        export DITOX_THREADS_PER_WORKER="$threads_per_worker"
        if (( threads_per_worker > 0 )); then
            export OMP_NUM_THREADS="$threads_per_worker"
            export MKL_NUM_THREADS="$threads_per_worker"
            export OPENBLAS_NUM_THREADS="$threads_per_worker"
            export NUMEXPR_NUM_THREADS="$threads_per_worker"
        fi
    else
        unset DITOX_THREADS_PER_WORKER
    fi
}

khipu_validate_config() {
    local family="$1"
    local config_file="$2"
    local expected_backend="$3"

    python - "$family" "$config_file" "$expected_backend" "$project_dir" <<'PY'
import sys
from pathlib import Path

family, config_file, expected_backend, project_root = sys.argv[1:5]
root = Path(project_root).resolve()
sys.path.insert(0, str(root))

from configs.config import load_pipeline_config


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


try:
    config = load_pipeline_config(str(root / config_file))
except (OSError, ValueError) as exc:
    fail(str(exc))

backend = config.general.get("backend")
runtime_backend = config.runtime.get("backend", backend)
if backend != expected_backend or runtime_backend != expected_backend:
    fail(
        f"{config_file} usa backend {backend!r}/{runtime_backend!r}; "
        f"se esperaba {expected_backend!r} para la familia {family!r}."
    )

images = config.images
chunk = images.get("images_chunk")
limit = images.get("limit")
starts_from = images.get("starts_from", 0)
if type(chunk) is not int or chunk < 1:
    fail(f"{config_file}: images.images_chunk debe ser un entero >= 1.")
if type(limit) is not int or limit < 1:
    fail(f"{config_file}: images.limit debe ser un entero >= 1.")
if type(starts_from) is not int or starts_from < 0:
    fail(f"{config_file}: images.starts_from debe ser un entero >= 0.")

images_dir = images.get("images_folder_rel_path")
if not images_dir:
    fail(f"{config_file}: falta images.images_folder_rel_path.")
images_path = root / images_dir
if not images_path.is_dir():
    fail(f"No existe el directorio de imágenes {images_dir}.")

if config.hub.get("external_models_only"):
    if not (root / "configs/models/external_models.json").is_file():
        fail("No existe configs/models/external_models.json.")
else:
    manifest = config.hub.get("model_manifest_rel_path")
    if not manifest or not (root / manifest).is_file():
        fail(f"No existe el manifiesto de modelos {manifest!r}.")

task = config.task
for key in ("dataset_path", "images_dir"):
    value = task.get(key)
    if value and not (root / value).exists():
        fail(f"No existe task.{key}: {value}")
if config.text.get("dataset") and not (root / config.text["dataset"]).is_file():
    fail(f"No existe text.dataset: {config.text['dataset']}")

if family in {"vision", "body"}:
    required = limit
    if family == "body":
        required = task.get("limit", limit)
    available = sum(1 for _ in images_path.glob("*.jpg"))
    if available < required:
        fail(
            f"{images_dir} contiene {available} imágenes y la config requiere {required}."
        )

tvm = config.runtime.get("tvm", {})
print(
    f"Config OK: {config_file} | backend={backend} | "
    f"model_workers={tvm.get('model_workers', 1)} | "
    f"threads_per_worker={tvm.get('threads_per_worker', 0)} | "
    f"images_dir={images_dir}"
)
PY
}

khipu_run_pipeline() {
    local family="$1"
    local config_file="$2"
    local threads="${SLURM_CPUS_PER_TASK:-1}"

    [[ -s "$project_dir/main.py" ]] || khipu_fail "No existe main.py en $project_dir."

    export TVM_NUM_THREADS="${TVM_NUM_THREADS:-$threads}"
    export OMP_NUM_THREADS="${OMP_NUM_THREADS:-$threads}"
    export MKL_NUM_THREADS="${MKL_NUM_THREADS:-$threads}"
    export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-$threads}"
    export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-$threads}"
    export TF_NUM_INTRAOP_THREADS="${TF_NUM_INTRAOP_THREADS:-$threads}"
    export TF_NUM_INTEROP_THREADS="${TF_NUM_INTEROP_THREADS:-$threads}"

    printf 'Lanzando %s: %s\n' "$family" "$config_file"
    printf 'Job: %s | CPUs: %s | Memory: %s | Time limit: %s\n' \
        "${SLURM_JOB_ID:-manual}" \
        "${SLURM_CPUS_PER_TASK:-$threads}" \
        "${SLURM_MEM_PER_NODE:-unknown} MB" \
        "${SLURM_JOB_TIME_LIMIT:-unknown}"
    srun --ntasks=1 --cpus-per-task="$threads" \
        python -u "$project_dir/main.py" "$config_file"
}
