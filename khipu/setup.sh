#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
environment_name="${CONDA_ENV_NAME:-ditox-cuda}"
python_version="${PYTHON_VERSION:-3.12}"
environment_prefix="${CONDA_ENV_PREFIX:-}"
conda_install_dir="${CONDA_INSTALL_DIR:-${HOME}/.local/miniforge3}"
miniforge_version="${MINIFORGE_VERSION:-24.11.3-2}"
datasets="${DATASETS:-all}"
model_config="${MODEL_CONFIG:-${CONFIG_FILE:-configs/run/complete/config_vision_explore.json}}"
environment_created=0
temp_dir=""
installer_path=""

cleanup() {
    status=$?
    trap - EXIT

    if [[ "$status" -ne 0 && "$environment_created" -eq 1 ]]; then
        if [[ -x "$environment_prefix/bin/python" ]]; then
            printf 'La configuración falló; eliminando el entorno recién creado %s...\n' "$environment_name" >&2
            if ! conda env remove --yes --prefix "$environment_prefix"; then
                printf 'Error: no se pudo eliminar el entorno %s durante el rollback.\n' "$environment_name" >&2
            fi
        fi
    fi

    if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
        rm -rf -- "$temp_dir"
    fi

    if [[ -n "$installer_path" && -f "$installer_path" ]]; then
        rm -f -- "$installer_path"
    fi

    exit "$status"
}
trap cleanup EXIT

printf 'Preparando el entorno de DiTOX para Khipu.\n'

export LD_PRELOAD="${LD_PRELOAD-}"
if command -v module >/dev/null 2>&1; then
    module purge
    if ! module load miniconda/3.0 >/dev/null 2>&1; then
        printf 'Aviso: no se pudo cargar miniconda/3.0; se usará Miniforge local si hace falta.\n' >&2
    fi
fi

if ! command -v conda >/dev/null 2>&1; then
    case "$(uname -m)" in
        x86_64) miniforge_arch="x86_64" ;;
        aarch64|arm64) miniforge_arch="aarch64" ;;
        *)
            printf 'Error: arquitectura no soportada para Miniforge: %s\n' "$(uname -m)" >&2
            exit 1
            ;;
    esac

    if [[ -e "$conda_install_dir" && ! -x "$conda_install_dir/bin/conda" ]]; then
        printf 'Error: %s existe, pero no contiene una instalación válida de Conda.\n' \
            "$conda_install_dir" >&2
        printf 'Define CONDA_INSTALL_DIR con una ruta vacía o válida e inténtalo de nuevo.\n' >&2
        exit 1
    fi

    if [[ ! -x "$conda_install_dir/bin/conda" ]]; then
        if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
            printf 'Error: se requiere curl o wget para descargar Miniforge.\n' >&2
            exit 1
        fi

        miniforge_file="Miniforge3-Linux-${miniforge_arch}.sh"
        miniforge_url="${MINIFORGE_URL:-https://github.com/conda-forge/miniforge/releases/download/${miniforge_version}/${miniforge_file}}"
        installer_path="$(mktemp "${TMPDIR:-/tmp}/Miniforge3-${miniforge_arch}.XXXXXX.sh")"
        printf 'Conda no está disponible. Instalando Miniforge en %s...\n' "$conda_install_dir"
        if command -v curl >/dev/null 2>&1; then
            curl --fail --location --retry 3 --output "$installer_path" "$miniforge_url"
        else
            wget --https-only --tries=3 --output-document="$installer_path" "$miniforge_url"
        fi
        mkdir -p "$(dirname "$conda_install_dir")"
        bash "$installer_path" -b -p "$conda_install_dir"
        rm -f -- "$installer_path"
        installer_path=""
    fi

    export PATH="$conda_install_dir/bin:$PATH"
fi

if ! command -v conda >/dev/null 2>&1; then
    printf 'Error: no se pudo disponer de Conda mediante el módulo ni Miniforge.\n' >&2
    exit 1
fi

if [[ ! -f "$project_root/requirements.txt" ]]; then
    printf 'Error: no se encontró %s.\n' "$project_root/requirements.txt" >&2
    exit 1
fi
if [[ ! -f "$project_root/download_datasets.py" ]]; then
    printf 'Error: no se encontró %s.\n' "$project_root/download_datasets.py" >&2
    exit 1
fi


find_named_environment() {
    local candidate

    candidate="$(conda env list 2>/dev/null \
        | awk -v env="$environment_name" '$1 == env { print $NF; exit }' || true)"
    if [[ -n "$candidate" && -x "$candidate/bin/python" ]]; then
        printf '%s\n' "$candidate"
        return 0
    fi

    if [[ -f "$HOME/.conda/environments.txt" ]]; then
        while IFS= read -r candidate; do
            if [[ "${candidate##*/}" == "$environment_name" \
                && -x "$candidate/bin/python" ]]; then
                printf '%s\n' "$candidate"
                return 0
            fi
        done < "$HOME/.conda/environments.txt"
    fi

    return 1
}

if [[ -z "$environment_prefix" ]]; then
    environment_prefix="$(find_named_environment || true)"
    if [[ -z "$environment_prefix" ]]; then
        environment_prefix="$HOME/.conda/envs/$environment_name"
    fi
fi

if [[ -x "$environment_prefix/bin/python" ]]; then
    printf 'El entorno Conda %s ya existe en %s; se actualizarán sus dependencias. No se eliminará en caso de error.\n' \
        "$environment_name" "$environment_prefix"
elif [[ -e "$environment_prefix" ]]; then
    printf 'Error: %s existe, pero no parece un entorno Conda válido.\n' "$environment_prefix" >&2
    printf 'Revísalo o define CONDA_ENV_PREFIX con otra ruta válida.\n' >&2
    exit 1
else
    printf 'Creando el entorno Conda %s en %s con Python %s...\n' \
        "$environment_name" "$environment_prefix" "$python_version"
    environment_created=1
    mkdir -p "$(dirname "$environment_prefix")"
    conda create --yes --prefix "$environment_prefix" "python=$python_version" pip
fi

printf 'Instalando dependencias de %s...\n' "$project_root/requirements.txt"
conda run --no-capture-output --prefix "$environment_prefix" \
    python -m pip install -r "$project_root/requirements.txt"

cuda_version="$(conda run --no-capture-output --prefix "$environment_prefix" \
    python -c 'import torch; print(torch.version.cuda or "")' 2>/dev/null || true)"
if [[ -z "$cuda_version" ]]; then
    printf 'Aviso: PyTorch no reporta runtime CUDA; el backend TVM seguirá usando CPU.\n' >&2
else
    printf 'Entorno %s listo; PyTorch incluye runtime CUDA %s.\n' \
        "$environment_name" "$cuda_version"
fi

# Dataset failures must not remove an environment that was prepared successfully.
environment_created=0

read -r -a dataset_args <<< "$datasets"
printf 'Preparando datasets: %s...\n' "${dataset_args[*]}"
conda run --no-capture-output --prefix "$environment_prefix" \
    python "$project_root/download_datasets.py" --datasets "${dataset_args[@]}"

if [[ " ${dataset_args[*]} " == *" coco "* || " ${dataset_args[*]} " == *" all "* ]]; then
    coco_dir="$project_root/configs/dataset/COCO"
    shopt -s nullglob
    coco_images=("$coco_dir"/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].jpg)
    shopt -u nullglob
    if (( ${#coco_images[@]} != 5000 )); then
        printf 'Error: se esperaban 5000 imágenes COCO val2017 en %s; hay %s.\n' \
            "$coco_dir" "${#coco_images[@]}" >&2
        exit 1
    fi
    printf 'COCO val2017 listo en %s (5000 imágenes).\n' "$coco_dir"
fi

if [[ "${PREFETCH_MODELS:-1}" == "1" ]]; then
    resolved_model_config="$model_config"
    if [[ "$resolved_model_config" != /* ]]; then
        resolved_model_config="$project_root/$resolved_model_config"
    fi
    if [[ ! -s "$resolved_model_config" ]]; then
        printf 'Error: no se encontró el config de modelos %s.\n' "$resolved_model_config" >&2
        exit 1
    fi
    printf 'Descargando modelos ONNX según %s...\n' "$model_config"
    conda run --no-capture-output --prefix "$environment_prefix" \
        python -c "$(cat <<'PY'
import sys
from pathlib import Path

project_root = Path(sys.argv[1]).resolve()
config_path = Path(sys.argv[2])
if not config_path.is_absolute():
    config_path = project_root / config_path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from configs.config import load_pipeline_config
from src.model_orchestrator.model_orchestrator import ModelOrchestrator

config = load_pipeline_config(config_path)
orchestrator = ModelOrchestrator(
    config.general,
    config.hub,
    str(project_root),
    check_prob_models=False,
)

total = 0
for item in orchestrator.get_models(metadata_only=False):
    total += 1
    print(f"[{total}] {item['model_name_opset']}", flush=True)
print(f"Modelos listos en cache: {total}")
PY
)" "$project_root" "$model_config"
else
    printf 'PREFETCH_MODELS=0; se omite la descarga de modelos.\n'
fi

mkdir -p "$project_root/results/slurm"

printf 'Entorno listo. Lanza un pipeline con:\n'
printf '  sbatch khipu/vision.slurm\n'
printf '  sbatch khipu/text_qa.slurm\n'
printf '  sbatch khipu/text_sentiment.slurm\n'
printf '  sbatch khipu/text_summarization.slurm\n'
printf '  sbatch khipu/text_generation.slurm\n'
printf '  sbatch khipu/body.slurm\n'
printf '  sbatch khipu/speech.slurm\n'
printf 'Parámetros comunes: COMPLETE=true|false EXPLORE=true|false MODEL_WORKERS=N THREADS_PER_WORKER=N.\n'
printf 'Ejemplo: COMPLETE=false EXPLORE=true MODEL_WORKERS=4 THREADS_PER_WORKER=8 sbatch khipu/vision.slurm\n'
printf 'Datasets: DATASETS="coco squad_v2 imdb" (por defecto all).\n'
printf 'Modelos: MODEL_CONFIG=configs/run/complete/config_vision_isolate.json (por defecto visión explore).\n'
printf 'Omite la descarga de modelos con PREFETCH_MODELS=0.\n'
printf 'Selecciona la variante con COMPLETE y EXPLORE.\n'
