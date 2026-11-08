#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
target_dir="$project_root/images/COCO"
download_url="https://images.cocodataset.org/zips/val2017.zip"
expected_images=5000
environment_name="ditox-cuda"
python_version="3.11"
environment_created=0
temp_dir=""

cleanup() {
    status=$?
    trap - EXIT

    if [[ "$status" -ne 0 && "$environment_created" -eq 1 ]]; then
        if conda env list | awk -v env="$environment_name" '$1 == env { found=1 } END { exit !found }'; then
            printf 'La configuración falló; eliminando el entorno recién creado %s...\n' "$environment_name" >&2
            if ! conda env remove --yes --name "$environment_name"; then
                printf 'Error: no se pudo eliminar el entorno %s durante el rollback.\n' "$environment_name" >&2
            fi
        fi
    fi

    if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
        rm -rf -- "$temp_dir"
    fi

    exit "$status"
}
trap cleanup EXIT

printf 'Preparando el entorno CUDA de DiTOX y COCO val2017.\n'

if ! command -v conda >/dev/null 2>&1; then
    printf 'Error: se requiere Conda; inicialízalo y vuelve a ejecutar este script.\n' >&2
    exit 1
fi

if [[ ! -f "$project_root/requirements.txt" ]]; then
    printf 'Error: no se encontró %s.\n' "$project_root/requirements.txt" >&2
    exit 1
fi

if ! conda env list | awk -v env="$environment_name" '$1 == env { found=1 } END { exit !found }'; then
    printf 'Creando el entorno Conda %s con Python %s...\n' "$environment_name" "$python_version"
    environment_created=1
    conda create --yes --name "$environment_name" "python=$python_version" pip
else
    printf 'El entorno Conda %s ya existe; se actualizarán sus dependencias. No se eliminará en caso de error.\n' "$environment_name"
fi

printf 'Instalando dependencias de %s...\n' "$project_root/requirements.txt"
conda run --no-capture-output --name "$environment_name" \
    python -m pip install -r "$project_root/requirements.txt"

cuda_version="$(conda run --no-capture-output --name "$environment_name" \
    python -c 'import torch; print(torch.version.cuda or "")')"
if [[ -z "$cuda_version" ]]; then
    printf 'Error: PyTorch no tiene soporte CUDA en el entorno %s.\n' "$environment_name" >&2
    exit 1
fi
printf 'Entorno %s listo; PyTorch incluye runtime CUDA %s.\n' "$environment_name" "$cuda_version"
printf 'Para usar la GPU, ejecuta DiTOX dentro de un job/nodo con GPU asignada en Slurm.\n'

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

if ! command -v unzip >/dev/null 2>&1; then
    printf 'Error: se requiere unzip para extraer COCO val2017.\n' >&2
    exit 1
fi

if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    printf 'Error: se requiere curl o wget para descargar COCO val2017.\n' >&2
    exit 1
fi

temp_dir="$(mktemp -d)"
archive="$temp_dir/val2017.zip"

printf 'Descargando COCO val2017 desde %s...\n' "$download_url"
if command -v curl >/dev/null 2>&1; then
    curl --fail --location --retry 3 --output "$archive" "$download_url"
else
    wget --tries=3 --output-document="$archive" "$download_url"
fi

unzip -tq "$archive" >/dev/null
archive_images="$(unzip -Z1 "$archive" | awk '/^val2017\/[0-9]{12}\.jpg$/ { count++ } END { print count+0 }')"
if [[ "$archive_images" -ne "$expected_images" ]]; then
    printf 'Error: el ZIP contiene %s imágenes val2017; se esperaban %s.\n' "$archive_images" "$expected_images" >&2
    exit 1
fi

unzip -j -o -q "$archive" 'val2017/*.jpg' -d "$target_dir"

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
