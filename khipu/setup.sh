#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
target_dir="$project_root/images/COCO"
download_url="${COCO_VAL2017_URL:-https://s3.amazonaws.com/images.cocodataset.org/zips/val2017.zip}"
expected_images=5000
environment_name="ditox-cuda"
python_version="3.11"
environment_prefix="${CONDA_ENV_PREFIX:-}"
conda_install_dir="${CONDA_INSTALL_DIR:-${HOME}/.local/miniforge3}"
miniforge_version="${MINIFORGE_VERSION:-24.11.3-2}"
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

printf 'Preparando el entorno CUDA de DiTOX y COCO val2017.\n'

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
    python -c 'import torch; print(torch.version.cuda or "")')"
if [[ -z "$cuda_version" ]]; then
    printf 'Error: PyTorch no tiene soporte CUDA en el entorno %s.\n' "$environment_name" >&2
    exit 1
fi
printf 'Entorno %s listo; PyTorch incluye runtime CUDA %s.\n' "$environment_name" "$cuda_version"
printf 'Para usar la GPU, ejecuta DiTOX dentro de un job/nodo con GPU asignada en Slurm.\n'

# Dataset failures must not remove an environment that was prepared successfully.
environment_created=0

printf 'Preparando el catálogo y los modelos ONNX de visión para ejecución offline...\n'
conda run --no-capture-output --prefix "$environment_prefix" \
    python "$project_root/khipu/download_vision_models.py" "$project_root"

mkdir -p "$target_dir"

image_count=0
for image in "$target_dir"/*.jpg; do
    [[ -e "$image" ]] || continue
    filename="${image##*/}"
    if [[ "$filename" =~ ^[0-9]{12}\.jpg$ ]]; then
        image_count=$((image_count + 1))
    fi
done

if [[ "$image_count" -eq "$expected_images" ]]; then
    printf 'COCO val2017 ya está completo en %s (%s imágenes).\n' "$target_dir" "$image_count"
    exit 0
fi

if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    printf 'Error: se requiere curl o wget para descargar COCO val2017.\n' >&2
    exit 1
fi

temp_dir="$(mktemp -d)"
archive="$temp_dir/val2017.zip"

printf 'Descargando COCO val2017 desde %s...\n' "$download_url"
if command -v curl >/dev/null 2>&1; then
    if ! curl --fail --location --retry 3 --show-error --output "$archive" "$download_url"; then
        printf 'Error: no se pudo descargar COCO val2017 desde %s; verifica el acceso HTTPS y el certificado TLS.\n' \
            "$download_url" >&2
        exit 1
    fi
else
    if ! wget --https-only --tries=3 --output-document="$archive" "$download_url"; then
        printf 'Error: no se pudo descargar COCO val2017 desde %s; verifica el acceso HTTPS y el certificado TLS.\n' \
            "$download_url" >&2
        exit 1
    fi
fi

"$environment_prefix/bin/python" - "$archive" "$target_dir" "$expected_images" <<'PY'
import re
import shutil
import sys
import zipfile
from pathlib import Path

archive_path = Path(sys.argv[1])
target_dir = Path(sys.argv[2])
expected_images = int(sys.argv[3])
image_pattern = re.compile(r"^val2017/[0-9]{12}\.jpg$")

with zipfile.ZipFile(archive_path) as archive:
    damaged_member = archive.testzip()
    if damaged_member is not None:
        raise SystemExit(f"Error: el ZIP está dañado en {damaged_member}.")

    image_members = [
        name for name in archive.namelist() if image_pattern.fullmatch(name)
    ]
    if len(image_members) != expected_images:
        raise SystemExit(
            f"Error: el ZIP contiene {len(image_members)} imágenes val2017; "
            f"se esperaban {expected_images}."
        )

    for member in image_members:
        destination = target_dir / Path(member).name
        with archive.open(member) as source, destination.open("wb") as output:
            shutil.copyfileobj(source, output)

print(f"ZIP validado y extraído: {len(image_members)} imágenes.")
PY

image_count=0
for image in "$target_dir"/*.jpg; do
    [[ -e "$image" ]] || continue
    filename="${image##*/}"
    if [[ "$filename" =~ ^[0-9]{12}\.jpg$ ]]; then
        image_count=$((image_count + 1))
    fi
done

if [[ "$image_count" -ne "$expected_images" ]]; then
    printf 'Error: se encontraron %s imágenes val2017 en %s; se esperaban %s.\n' \
        "$image_count" "$target_dir" "$expected_images" >&2
    exit 1
fi

printf 'COCO val2017 descargado y extraído en %s (%s imágenes).\n' "$target_dir" "$image_count"
