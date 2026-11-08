## Ejemplos introductorios

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/ejemplos/introductorios/

Introductorios
Enviar jobs
Software
Ejemplos
Ejemplos
Introductorios
Introductorios
Imprimir la fecha actual
Imprimir las variables de ambiente de Slurm
MPI/OpenMP
Python
Miniconda
Imprimir la fecha actual
Imprimir las variables de ambiente de Slurm
Introductorios
Imprimir la fecha actual
Crear el archivo fecha_actual.sh:
#!/bin/bash
# Nombre del job:
#SBATCH --job-name=fecha_actual
# Cantidad de CPUs cores a usar:
#SBATCH -c 1
# Tamaño de memoria del job:
#SBATCH --mem-per-cpu=100mb
date
sleep 10 # duerme 10s, solo para visualizar el job en la fila
Enviar a ejecutar el job:
sbatch fecha_actual.sh
Imprimir las variables de ambiente de Slurm
Crear el archivo env_vars.sh:
#!/bin/bash
# Nombre del job:
#SBATCH --job-name=env_vars
# Comandos:
set | grep SLURM
Enviar a ejecutar el job:
sbatch env_vars.sh

---

## Ejemplo: Python

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/ejemplos/python/

Python
Enviar jobs
Software
Ejemplos
Ejemplos
Introductorios
MPI/OpenMP
Python
Miniconda
Python
Ejecución del programa en Python, prueba_python.py:
from math import factorial as f
print("Hola mundo")
N = 100
print("%d! = %d" %(N, f(N)))
Crear el archivo ej5.sh:
#!/bin/bash
#SBATCH -J ej5 # nombre del job
#SBATCH -p debug # nombre de la particion
#SBATCH -c 1  # numero de cpu cores a usar
module load python3/3.10.2 # carga el modulo de python version 3.10.2
python3 prueba_python.py # siendo prueba_python.py el nombre del programa python
module unload python3/3.10.2
Enviar a ejecutar el job:
sbatch ej5.sh

---

## Ejemplo: Miniconda

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/ejemplos/miniconda/

Miniconda
Enviar jobs
Software
Ejemplos
Ejemplos
Introductorios
MPI/OpenMP
Python
Miniconda
Miniconda
Creación de ambiente de trabajo
Creación de batch script
Creación de ambiente de trabajo
Creación de batch script
Miniconda
En Khipu, se puede emplear el gestor de paquetes conda a través del módulo Miniconda. Para ello será necesario necesario ejecutar los siguiente pasos:
Creación de ambiente de trabajo
Desde el nodo de acceso, cargaremos el modulo de Miniconda.
module load miniconda/3.0
- Crearemos el ambiente de conda sobre el cual trabajaremos.
conda create --name my-env
Si deseamaos crear un ambiente y a la vez instalar paquetes.
conda create --name my-env pytorch torchvision
Creación de batch script
En el script que creemos, deberemos especificar la cantidad de recursos que necesitamos. Luego deberemos cargar el módulo de Miniconda y activar nuestro ambiente de trabajo. Finalmente, escribiremos el comando necesario para ejecutar nuestro programa.
#!/bin/bash
#SBATCH --job-name=app-test      # nombre del job
#SBATCH --nodes=1                # cantidad de nodos
#SBATCH --ntasks=1               # cantidad de tareas
#SBATCH --cpus-per-task=1        # cpu-cores por task
#SBATCH --mem=4G                 # memoria total por nodo
#SBATCH --gres=gpu:1             # numero de gpus por nodo
#SBATCH --time=00:05:00          # limite total de ejecucion
module purge
module load miniconda/3.0
conda activate my-env
python app-test.py
conda deactivate
Si al momento de enviar su job obtienen el siguiente mensaje.
CommandNotFoundError: Your shell has not been properly configured to use 'conda activate'.
To initialize your shell, run
$ conda init <SHELL_NAME>
Currently supported shells are:
- bash
- fish
- tcsh
- xonsh
- zsh
- powershell
See 'conda init --help' for more information and options.
IMPORTANT: You may need to close and restart your shell after running 'conda init'.
Deberan adicionar  eval "$(conda shell.bash hook)" a su batch script luego de haber cargado el modulo de miniconda. Por lo tanto, el batch script resultante será el siguiente.
#!/bin/bash
#SBATCH --job-name=app-test      # nombre del job
#SBATCH --nodes=1                # cantidad de nodos
#SBATCH --ntasks=1               # cantidad de tareas
#SBATCH --cpus-per-task=1        # cpu-cores por task
#SBATCH --mem=4G                 # memoria total por nodo
#SBATCH --gres=gpu:1             # numero de gpus por nodo
#SBATCH --time=00:05:00          # limite total de ejecucion
module purge
module load miniconda/3.0
eval "$(conda shell.bash hook)"
conda activate my-env
python app-test.py
conda deactivate

---

## Ejemplo: MPI / OpenMP

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/ejemplos/mpi-openmp/

MPI y OpenMP
Enviar jobs
Software
Ejemplos
Ejemplos
Introductorios
MPI/OpenMP
MPI/OpenMP
OpenMP de un solo thread
OpenMP de múltiples threads
MPI multi-proceso
MPI Y OpenMP a la vez (Híbrido)
Python
Miniconda
OpenMP de un solo thread
OpenMP de múltiples threads
MPI multi-proceso
MPI Y OpenMP a la vez (Híbrido)
MPI/OpenMP
Para los siguientes dos ejemplos con OpenMP usaremos el siguiente código  en C++ prueba_openmp.cpp.
#include <stdio.h>
#include <stdlib.h>
#include <omp.h>
void Hello(void); /* Thread function */
/*--------------------------------------------------------------------*/
int main(int argc, char* argv[]) {
int thread_count = strtol(argv[1], NULL, 10);
# pragma omp parallel num_threads(thread_count)
Hello();
return 0;
}
/* main */
/*-------------------------------------------------------------------
* * Function: Hello
* * Purpose: Thread function that prints message
* */
void Hello(void) {
int my_rank = omp_get_thread_num();
int thread_count = omp_get_num_threads();
printf("Hello from thread %d of %d\n", my_rank, thread_count); /* Hello */
}
Compilaremos el programa antes de crear y enviar el batch script.
module load gcc/5.5.0
g++ prueba_openmp.cpp -fopenmp -lpthread -o prueba_openmp
module unload gcc/5.5.0
OpenMP de un solo thread
Crear el archivo single_thread_openmp.sh:
#!/bin/bash
# Nombre del job:
#SBATCH --job-name=single_thread_openmp
# Límite de tiempo de 10 min:
#SBATCH --time=10:00
./prueba_openmp
Enviar a ejecutar el job:
sbatch single_thread_openmp.sh
OpenMP de múltiples threads
Crear el archivo multi_thread_openmp.sh:
#!/bin/bash
# Nombre del job:
#SBATCH --job-name=multi_thread_omp_job
# Nombre del archivo de salida:
#SBATCH --output=multi_thread_omp_job.txt
# Numero de tasks:
#SBATCH --ntasks=1
# Numero de CPUs por task:
#SBATCH --cpus-per-task=4
# Límite de tiempo de 10 min:
#SBATCH --time=10:00
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
./prueba_openmp
Enviar a ejecutar el job:
sbatch multi_thread_openmp.sh
MPI multi-proceso
Para el siguiente ejemplo usaremos el código prueba_mpi.c:
#include <mpi.h>
#include <stdio.h>
int main(int argc, char** argv) {
// Initialize the MPI environment
MPI_Init(NULL, NULL);
// Get the number of processes
int world_size;
MPI_Comm_size(MPI_COMM_WORLD, &world_size);
// Get the rank of the process
int world_rank;
MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);
// Get the name of the processor
char processor_name[MPI_MAX_PROCESSOR_NAME];
int name_len;
MPI_Get_processor_name(processor_name, &name_len);
// Print off a hello world message
printf("Hello world from processor %s, rank %d out of %d processors\n",
processor_name, world_rank, world_size);
// Finalize the MPI environment.
MPI_Finalize();
}
Compilar el programa mpi:
module load mpich/4.0
mpicc prueba_mpi.c -o prueba_mpi
module unload mpich/4.0
Crear el archivo multi_process_mpi.sh:
#!/bin/bash
# Nombre del job:
#SBATCH -J prueba_mpi
# Nombre de la partición:
#SBATCH -p investigacion
# Número de nodos:
#SBATCH -N 2
# Número de tasks por nodo:
#SBATCH --tasks-per-node=3
# Carga del modulo MPICH 4.0
module load mpich/4.0
# Ejecución del compilado
mpirun  prueba_mpi
# Descarga del módulo
module unload mpich/4.0
Enviar a ejecutar el job:
sbatch multi_process_mpi.sh
MPI Y OpenMP a la vez (Híbrido)
Para este ejemplo usaremos el siguiente codigo hibrido y lo guardaremos en un archivo hibrido.c.
#include <stdio.h>
#include <omp.h>
#include "mpi.h"
int main(int argc, char *argv[]) {
int numprocs, rank, namelen;
char processor_name[MPI_MAX_PROCESSOR_NAME];
int iam = 0, np = 1;
MPI_Init(&argc, &argv);
MPI_Comm_size(MPI_COMM_WORLD, &numprocs);
MPI_Comm_rank(MPI_COMM_WORLD, &rank);
MPI_Get_processor_name(processor_name, &namelen);
#pragma omp parallel default(shared) private(iam, np)
{
np = omp_get_num_threads();
iam = omp_get_thread_num();
printf("Hello from thread %d out of %d from process %d out of %d on %s\n",
iam, np, rank, numprocs, processor_name);
}
MPI_Finalize();
}
Compilar el programa híbrido:
module load mpich/4.0
mpicc -fopenmp hibrido.c -o hibrido
module unload mpich/4.0
Crear el archivo hibrido_mpi_openmp.sh:
#!/bin/bash
# Un Job script para la ejecución de un código híbrido MPI-OpenMP
#SBATCH --job-name=hibrido_mpi_openmp
#SBATCH --output=hibrido_mpi_openmp.out
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=8
#SBATCH --partition=docencia
# Cargar el modulo MPI.
module load mpich/4.0
# Configurar el valor de  OMP_NUM_THREADS con el numero de CPUs por task solicitado.
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
# Ejecutar el proceso con mpirun. Puede notar que no es necesario especificar el flag de MPI
# '-n' puesto que automaticamente utiliza el valor de la configuración de Slurm realizada
mpirun ./hibrido
module unload mpich/4.0
Enviar a ejecutar el job:
sbatch hibrido_mpi_openmp.sh

---

## Ejemplo: GPU (pagina vacia en la fuente)

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/ejemplos/gpu/

GPU
GPU

---

