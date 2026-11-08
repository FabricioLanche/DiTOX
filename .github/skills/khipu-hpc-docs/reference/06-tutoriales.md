## Visual Studio Code remoto

Fuente: https://docs.khipu.utec.edu.pe/tutoriales/vs-code-remote/

Visual Studio Code
Inicializando búsqueda
Visual Studio Code
Visual Studio Code
Instalación
Requisitos
¿Cómo Usar?
¿Como terminar mi sesión?
Recomendaciones Generales
Reinicio de Jobs
Apptainer
Instalación
Requisitos
¿Cómo Usar?
¿Como terminar mi sesión?
Recomendaciones Generales
Visual Studio Code Remoto en Khipu
En este tutorial vamos a mostrar cómo conectarse a un nodo de cómputo de Khipu usando Remote - SSH. Remote - SSH, es una extensión de Visual Studio que facilita la conexión a un servidor remoto a través del protocolo SSH. A través de esta herramienta es posible:
Crear, editar y eliminar archivos de manera directa en el servidor remoto.
Copiar archivos locales al servidor remoto usando drag-and-drop.
Descargar sus archivos remotos.
Crear sesiones de terminal y ejecutar comandos.
Redirección automática de puertos, y más.
Hasta ahora todo esto era posible de hacer solamente en el nodo líder. Sin embargo, su uso se limitaba a la ejecución de tareas administrativas y comandos cortos. A partir de ahora será posible obtener los beneficios listados directamente en un nodo de cómputo. Y lo mejor de todo es que cada sesión se instanciará de manera automática a un job en Slurm.
Info
Por el momento, el único nodo habilitado para este fin será el nodo ds001 de la particion de data-science. Cada sesión contará con un reserva de 8 núcleos CPU, 32GB de RAM, 4 shards de GPU y un tiempo límite de 4 horas. No es posible tener más de una sesión por usuario y una vez acabado el tiempo límite, se tendrá que instanciar nuevamente la sesión.
A continuación se muestran los pasos a seguir para configurar nuestra sesión de Visual Studio directamente en un nodo de cómputo.
Instalación
Requisitos
Visual Studio Code
Remote - SSH
Para instanciar nuestro Visual Studio haremos uso del script vscode-remote-hpc que fue adaptado para su funcionamiento en Khipu. Este script se encargará de configurar una sesión de Remote - SSH, a partir del cual usted podrá iniciar un batch job, o reusar uno existente, directamente desde su Visual Studio. Este script funciona para Linux , Windows  y Mac .
Linux y    MacOS Windows
Abrimos una sesión de terminal y ejecutaremos el siguiente comando:
curl -fsSL https://raw.githubusercontent.com/khipu-utec/vscode-remote-hpc/refs/heads/main/client/setup.sh | bash
- Seguiremos los pasos que se nos indique en pantalla, tal y como se muestra a continuación:
Abrimos una sesión de PowerShell y ejecutaremos el siguiente comando:
irm https://raw.githubusercontent.com/khipu-utec/vscode-remote-hpc/refs/heads/main/client/setup.ps1 | iex
Seguiremos los pasos que se nos indique en pantalla, tal y como se muestra a continuación:
¿Cómo Usar?
Una vez realizado el paso anterior, vscode-remote-khipu estará disponible en el Remote Explorer de Visual Studio.
Al hacer click en él, automáticamente se lanzará un batch job en Khipu. Deberemos esperar unos momentos hasta que el job se inicie y podamos conectarnos a él. Si nos conectamos al cluster y observamos la fila de slurm con squeue --me notaremos que existe un nuevo job llamado vscode-remote.
Info
Si no logramos observar nuestro job, es probable que se deba a que la fila de acceso a ese nodo ya se llenó y debamos intentar más tarde.
Luego que la sesión termine de configurarse, podremos seleccionar un directorio para trabajar y usar nuestro Visual Studio remoto. Puede crear previamente un directorio para trabajar, o hacerlo directamente desde su $HOME.
Es importante mencionar que el job permanecerá en ejecución hasta que el tiempo límite se alcance. Es por ello que sí termina antes del tiempo límite, deberá cancelar su job manualmente para liberar espacio en la cola. Recuerde que el cluster es un compartido por todos y por ello debemos hacer un uso responsable y empático de sus recursos.
Warning
Cerrar su Visual Studio no cancela automáticamente su job, deberá hacerlo de manera manual!
¿Como terminar mi sesión?
Para cancelar su job puede hacerlo con el clásico scancel <job-id> usando el job-id de su sesión, o ejecutando:
vscode-remote cancel
Recomendaciones Generales
Actualmente, estamos experimentando con esta nueva herramienta y lo estamos haciendo únicamente en el nodo ds001 de la particion de data-science. Ese nodo cuenta con GPU y acceso a internet (a diferencia de los demás nodos de cómputo). Nuestra intención es que este nodo sirva para ejecutar notebooks de Python de manera similar a como se realiza en Google Colab, sin embargo no contamos con recursos infinitos para poder proveer un acceso ilimitado a las sesiones en Visual Studio. Es por ello que dejamos las siguientes recomendaciones.
Si va a ejecutar trabajos de Inteligencia Artificial, use este nodo para configurar su virtual enviroment, instalar sus dependencias, descargar sus datos, visualizar la cantidad de parámetros que serán optimizados y hacer una prueba inicial de la ejecución de su modelo.
Si ve que su modelo tiene una gran cantidad de parámetros (mayor a 4GB de GPU RAM) y/o demorará en ejecutarse, genere su script en Slurm y mándelo de la manera tradicional.
No genere una sesión para empezar a codear su modelo desde cero. Recuerde que cada sesión reserva una cantidad grande de recursos que serían mal aprovechados realizando esa tarea. Puede usar herramientas como Google Colab para codear sus modelos y una vez listos, traerlos a Khipu para su ejecución. Recuerde que, al igual que usted, hay alguien más esperando por usar Khipu.
No olvide cerrar su sesión al término de su trabajo.

---

## Uso de Apptainer

Fuente: https://docs.khipu.utec.edu.pe/tutoriales/apptainer/

Apptainer
Visual Studio Code
Reinicio de Jobs
Apptainer
Apptainer
Descripción general de la interfaz de Apptainer
Descarga de imágenes
Interacción con contenedores existentes
Run
Shell
Exec
Trabajo con archivos
Construcción de imágenes personalizadas
Soporte para GPU
Descarga de imágenes
Modo interactivo
Caché de Apptainer
Script de envío a SLURM
Descripción general de la interfaz de Apptainer
Descarga de imágenes
Interacción con contenedores existentes
Run
Shell
Exec
Trabajo con archivos
Construcción de imágenes personalizadas
Soporte para GPU
Descarga de imágenes
Modo interactivo
Caché de Apptainer
Script de envío a SLURM
Apptainer
Apptainer (anteriormente conocido como Singularity) es una plataforma de contenedores de código abierto, segura, portable y fácil de usar que permite a los usuarios crear y ejecutar contenedores que empaquetan software de forma portable y reproducible. Puedes construir un contenedor para Apptainer en tu laptop y luego ejecutarlo en otra PC, estación de trabajo, clúster HPC, servidor en la nube, etc. Apptainer permite a usuarios sin privilegios usar contenedores y prohíbe la escalada de privilegios dentro del contenedor; los usuarios son los mismos dentro y fuera del contenedor. Apptainer puede importar cualquier contenedor de registros OCI (Open Containers Initiative), lo que significa que puedes descargar, ejecutar y construir desde la mayoría de los contenedores en Docker Hub sin modificaciones. Más información sobre Apptainer se puede encontrar en su sitio web oficial.
Descripción general de la interfaz de Apptainer
Los comandos de Apptainer pueden ejecutarse de forma nativa en el nodo maestro o en cualquier nodo de cómputo, sin necesidad de cargar ningún módulo adicional.
El comando help ofrece una descripción general de las opciones y subcomandos de Apptainer:
$ apptainer help
Linux container platform optimized for High Performance Computing (HPC) and
Enterprise Performance Computing (EPC)
Usage:
apptainer [global options...]
Description:
Apptainer containers provide an application virtualization layer enabling
mobility of compute via both application and environment portability. With
Apptainer one is capable of building a root file system that runs on any
other Linux system where Apptainer is installed.
Options:
--build-config    use configuration needed for building containers
-c, --config string   specify a configuration file (for root or
unprivileged installation only) (default
"/etc/apptainer/apptainer.conf")
-d, --debug           print debugging information (highest verbosity)
-h, --help            help for apptainer
--nocolor         print without color output (default False)
-q, --quiet           suppress normal output
-s, --silent          only print errors
-v, --verbose         print additional information
--version         version for apptainer
Available Commands:
build       Build an Apptainer image
cache       Manage the local cache
capability  Manage Linux capabilities for users and groups
checkpoint  Manage container checkpoint state (experimental)
completion  Generate the autocompletion script for the specified shell
config      Manage various apptainer configuration (root user only)
delete      Deletes requested image from the library
exec        Run a command within a container
help        Help about any command
inspect     Show metadata for an image
instance    Manage containers running as services
key         Manage OpenPGP keys
keyserver   Manage apptainer keyservers
oci         Manage OCI containers
overlay     Manage an EXT3 writable overlay image
plugin      Manage Apptainer plugins
pull        Pull an image from a URI
push        Upload image to the provided URI
registry    Manage authentication to OCI/Docker registries
remote      Manage apptainer remote endpoints
run         Run the user-defined default command within a container
run-help    Show the user-defined help for an image
search      Search a Container Library for images
shell       Run a shell within a container
sif         Manipulate Singularity Image Format (SIF) images
sign        Add digital signature(s) to an image
test        Run the user-defined tests within a container
verify      Verify digital signature(s) within an image
version     Show the version for Apptainer
Examples:
$ apptainer help <command> [<subcommand>]
$ apptainer help build
$ apptainer help instance start
For additional help or support, please visit https://apptainer.org/help/
Descarga de imágenes
Las imágenes de contenedor son ejecutables que agrupan todos los componentes necesarios para una aplicación o entorno, como una plantilla para los contenedores.
Los contenedores son la instancia en ejecución de las imágenes.
Los contenedores preconstruidos pueden obtenerse de diversas fuentes como:
Apptainer/Singularity Hub
Docker Hub
NVIDIA NGC Catalog
Otros registros OCI
Puedes usar los comandos pull y build para descargar imágenes de un recurso externo como Docker:
(master)$ apptainer pull docker://alpine
(master)$ apptainer build <container-name>.sif docker://alpine
¡Recuerda! Los comandos pull y build deben ejecutarse en el nodo maestro. El nodo maestro es el único con acceso a internet.
Interacción con contenedores existentes
Run
Una vez descargada la imagen, estás listo para ejecutarla. Como ejemplo, descargaremos el contenedor lolcow y lo ejecutaremos.
# Container downloading
(master)$ apptainer pull docker://ghcr.io/apptainer/lolcow
INFO:    Converting OCI blobs to SIF format
INFO:    Starting build...
Copying blob 5ca731fc36c2 done   |
Copying blob 16ec32c2132b done   |
Copying config fd0daa4d89 done   |
Writing manifest to image destination
2025/02/28 14:04:53  info unpack layer: sha256:16ec32c2132b43494832a05f2b02f7a822479f8250c173d0ab27b3de78b2f058
2025/02/28 14:04:54  info unpack layer: sha256:5ca731fc36c28789c5ddc3216563e8bfca2ab3ea10347e07554ebba1c953242e
INFO:    Creating SIF file...
# Container running in the system host
(master)$ apptainer run lolcow_latest.sif
______________________________
< Fri Feb 28 14:05:17 -03 2025 >
------------------------------
\   ^__^
\  (oo)\_______
(__)\       )\/\
||----w |
||     ||
Como podemos ver, el contenedor fue descargado como un archivo de imagen de Apptainer lolcow_latest.sif. Este archivo fue ejecutado con el comando apptainer run <container-image-name>.sif. Sin embargo, run no es el único comando para ejecutar e interactuar con un contenedor; lo discutiremos en las siguientes líneas.
Shell
Puedes crear un nuevo shell dentro de tu contenedor e interactuar con él como si fuera una máquina virtual.
(master)$ apptainer shell lolcow_latest.sif
Apptainer>
El cambio en el prompt (de (master)$ a Apptainer>) indica que ahora estás dentro del contenedor. Además, eres el mismo usuario que en el sistema anfitrión y tienes acceso al directorio home del usuario.
# I executing apptainer in the master node
Apptainer> hostname
khipu
# My user in the host system is aturing, in apptainer too
Apptainer> whoami
aturing
# I can access my home directory inside the container
Apptainer> pwd
/home/aturing
Nota: Puedes ejecutar apptainer shell en el nodo maestro, pero se recomienda hacerlo usando un trabajo interactivo de Slurm. Para ello, debes agregar el siguiente comando antes de tus comandos de Apptainer: srun --pty --mem=2G -p debug <apptainer command>.
A continuación se muestra el ejemplo anterior usando un trabajo interactivo de Slurm:
# I will execute an apptainer shell in a compute node
srun --pty --mem=2G -p debug apptainer shell lolcow_latest.sif
Apptainer> hostname
n003
Recuerda que los trabajos en la partición debug tienen un límite de tiempo de 30 minutos. Para trabajos de larga duración, debes ejecutarlos usando un trabajo batch de Slurm. Explicaremos esto más adelante.
Exec
Con el comando exec puedes ejecutar un comando personalizado dentro de un contenedor. Por ejemplo, para ejecutar el programa cowsay dentro del contenedor lolcow_latest.sif:
[rubaldo@khipu ~]$ apptainer exec lolcow_latest.sif cowsay Khipu
_______
< Khipu >
-------
\   ^__^
\  (oo)\_______
(__)\       )\/\
||----w |
||     ||
Trabajo con archivos
Los archivos del sistema anfitrión son accesibles desde dentro del contenedor.
[rubaldo@khipu ~]$ echo "Hello from Khipu" > $HOME/testfile.txt
[rubaldo@khipu ~]$ apptainer exec lolcow_latest.sif cat $HOME/testfile.txt
Hello from Khipu
Por defecto, Apptainer monta $HOME, el directorio de trabajo actual y ubicaciones adicionales del sistema anfitrión dentro del contenedor.
Referencias:
https://apptainer.org/docs/user/main/quick_start.html
Construcción de imágenes personalizadas
Apptainer permite a los usuarios construir contenedores a partir de un archivo de definición (como Docker con un Dockerfile). Dentro de este archivo puedes agregar variables de entorno o instalar dependencias de software para reproducir y compartir fácilmente tus contenedores.
Un archivo de definición tiene una cabecera y un cuerpo. La cabecera determina el contenedor base con el que comenzar, y el cuerpo se divide en secciones que realizan tareas como la instalación de software, la configuración del entorno y la copia de archivos al contenedor desde el sistema anfitrión. Más información sobre cómo crear el archivo de definición de Apptainer se puede encontrar aquí.
Por ejemplo, crearemos un archivo lolcow.def para definir un contenedor basado en ubuntu e instalar cowsay dentro de él.
BootStrap: docker
From: ubuntu:24.04
%post
apt-get -y update
apt-get -y install cowsay lolcat
%environment
export LC_ALL=C
export PATH=/usr/games:$PATH
%runscript
date | cowsay | lolcat
%labels
Author Khipu
Exec: apptainer
En este ejemplo, la cabecera le indica a Apptainer que comience con la imagen base ubuntu:24.04 de la biblioteca de contenedores de Docker. La sección %post se ejecuta en tiempo de construcción después de que la imagen base ha sido descargada. En este ejemplo, la usamos para actualizar la biblioteca de paquetes e instalar cowsay y lolcat. La sección %environment define variables de entorno para el contenedor. La sección %runscript se usa para definir las acciones del contenedor cuando es ejecutado (estos comandos no se ejecutan en tiempo de construcción). Finalmente, la sección %labels se usa para colocar información sobre el contenedor, como el autor, cómo usarlo, ejemplos, etc.
Para construir el contenedor a partir del archivo anterior, necesitamos ejecutar apptainer build <container-name>.sif <container-definition-file>.def:
[rubaldo@khipu apptainer]$ apptainer build lolcow.sif lolcow.def
INFO:    Starting build...
...
INFO:    Adding labels
INFO:    Adding environment to container
INFO:    Adding runscript
INFO:    Creating SIF file...
INFO:    Build complete: lolcow.sif
Luego, para ejecutar el contenedor basta con ejecutar apptainer run lolcow.sif o ./lolcow.sif.
Soporte para GPU
Apptainer tiene soporte para contenedores que usan el framework de computación GPU CUDA de NVIDIA. Las siguientes líneas muestran cómo crear y ejecutar contenedores con GPU en Khipu.
Descarga de imágenes
El primer paso, como se mostró anteriormente, es descargar y construir la imagen del contenedor. Como ejemplo, descargaremos una imagen nvidia-cuda12.8.0.
[rubaldo@khipu]$ apptainer pull docker://nvidia/cuda:12.8.0-base-ubuntu20.04
INFO:    Converting OCI blobs to SIF format
INFO:    Starting build...
...
INFO:    Creating SIF file...
# Or
[rubaldo@khipu]$ apptainer build cuda12.sif docker://nvidia/cuda:12.8.0-base-ubuntu20.04
Recuerda: el comando apptainer pull <something> solo funciona en el nodo maestro.
Los nodos GPU en Khipu son accesibles a través de Slurm. En las siguientes líneas mostraré cómo compilar y ejecutar tu código CUDA usando Apptainer y Slurm.
Como ejemplo, usa el código gpu-info.cu y compílalo en el nodo maestro:
# Load cuda module
[rubaldo@khipu]$ ml load cuda
[rubaldo@khipu]$ nvcc -o gpu_info gpu_info.cu
Luego, para ejecutar el código:
[rubaldo@khipu]$ srun --mem=1G -p gpu apptainer exec --nv cuda_12.8.0-base-ubuntu20.04.sif ./gpu_info
CUDA Device(s) Found: 1
Device 0 Information:
Name: Tesla T4
Compute Capability: 7.5
Total Global Memory: 14915 MB
Shared Memory per Block: 48 KB
Registers per Block: 65536
Max Threads per Block: 1024
Max Block Dimensions: (1024, 1024, 64)
Max Grid Dimensions: (2147483647, 65535, 65535)
Clock Rate: 1590 MHz
Memory Clock Rate: 5001 MHz
Memory Bus Width: 256 bits
Total Constant Memory: 64 KB
Warp Size: 32
Multiprocessor Count: 40
Como puedes ver, --nv se pasa al comando exec para configurar el entorno y usar una GPU NVIDIA con las bibliotecas básicas de CUDA. Sin este flag, los dispositivos y bibliotecas CUDA no pueden ser utilizados. Este flag no es necesario en tiempo de construcción.
Se recomienda ampliamente compilar el código CUDA en el nodo maestro, ya que las imágenes CUDA con el compilador de NVIDIA incluido (imágenes devel) son mucho más grandes que las imágenes base.
Como prueba de concepto, podemos compilar el mismo código usando Apptainer. Para ello necesitamos descargar una imagen CUDA de tipo devel, como nvidia/cuda:12.5.1-devel-ubuntu20.04 (3.6 GB), que es más de 30 veces más grande que una imagen base (~95 MB).
[rubaldo@khipu]$ apptainer pull docker://nvidia/cuda:12.5.1-devel-ubuntu20.04
INFO:    Converting OCI blobs to SIF format
INFO:    Starting build...
...
INFO:    Creating SIF file...
Para compilar el código, ejecuta:
[rubaldo@khipu]$ srun --mem=1G -p gpu apptainer exec --nv cuda_12.5.1-devel-ubuntu20.04.sif nvcc -o gpu_info gpu_info.cu
Y finalmente para ejecutar el código:
[rubaldo@khipu]$ srun --mem=1G -p gpu apptainer exec --nv cuda_12.5.1-devel-ubuntu20.04.sif ./gpu_info
CUDA Device(s) Found: 1
Device 0 Information:
Name: Tesla T4
Compute Capability: 7.5
Total Global Memory: 14915 MB
Shared Memory per Block: 48 KB
Registers per Block: 65536
Max Threads per Block: 1024
Max Block Dimensions: (1024, 1024, 64)
Max Grid Dimensions: (2147483647, 65535, 65535)
Clock Rate: 1590 MHz
Memory Clock Rate: 5001 MHz
Memory Bus Width: 256 bits
Total Constant Memory: 64 KB
Warp Size: 32
Multiprocessor Count: 40
Para practicar los comandos anteriores, puedes intentar ejecutarlos en todos nuestros nodos GPU agregando --nodelist=<nombre del nodo gpu> al comando srun. Para ver la lista de nodos GPU, ejecuta sinfo.
En todos los ejemplos anteriores se usó el comando srun para lanzar los trabajos de Slurm. Este comando es adecuado para trabajos de corta duración, pero si tu trabajo requiere mucho más tiempo, debes lanzarlo en modo batch con sbatch.
Más información sobre el soporte GPU de Apptainer se puede encontrar aquí.
Modo interactivo
A veces quieres interactuar con tu contenedor como si estuvieras en un shell. Puedes hacerlo usando un trabajo interactivo de Slurm. Los trabajos interactivos deben ejecutarse en la partición debug-gpu y tienen un límite de tiempo de 30 minutos. Recuerda que los contenedores en Apptainer son inmutables después de la construcción.
[rubaldo@khipu]$ srun --pty -p debug-gpu apptainer run --nv cuda_12.8.0-base-ubuntu20.04.sif
Apptainer>
# To check the nvidia driver
Apptainer> nvidia-smi
Sun Mar  2 09:20:22 2025
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 560.35.03              Driver Version: 560.35.03      CUDA Version: 12.6     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  Tesla T4                       On  |   00000000:37:00.0 Off |                    0 |
| N/A   78C    P0             51W /   70W |   13831MiB /  15360MiB |     55%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI        PID   Type   Process name                              GPU Memory |
|        ID   ID                                                               Usage      |
...
Caché de Apptainer
Cuando generas una imagen SIF desde fuentes remotas, Apptainer almacena la imagen en caché. Por defecto, la carpeta de caché se crea en la variable de entorno HOME ($HOME/.apptainer/cache). El comando apptainer cache te permite listar y limpiar tu caché.
# List your cache
[rubaldo@khipu]$ apptainer cache list
There are 4 container file(s) using 7.31 GiB and 88 oci blob file(s) using 13.18 GiB of space
Total space used: 20.49 GiB
# The same command with details
apptainer cache list -v
NAME                     DATE CREATED           SIZE             TYPE
03bb9eb021f579ed871d5f   2025-03-02 07:52:09    4.41 MiB         blob
093f9cb4ed5900be5b069a   2025-02-08 14:25:21    0.18 KiB         blob
...
There are 4 container file(s) using 7.31 GiB and 88 oci blob file(s) using 13.18 GiB of space
Total space used: 20.49 GiB
# Clean you cache
apptainer cache clean
# Clean you cache files older than 15 days
apptainer cache clean --days 15
Intenta liberar tu caché de Apptainer regularmente.
Script de envío a SLURM
Puedes lanzar tus trabajos de Apptainer en modo batch con un script de Slurm. Se recomienda ampliamente cuando tu trabajo tomará mucho tiempo de ejecución. Como ejemplo, el contenedor lolcow_latest.sif del primer ejemplo se ejecutará usando un archivo de envío lolcow.slurm.
#!/bin/bash
## Slurm Directives
#SBATCH --job-name=apptainer_lolcow
#SBATCH --output=apptainer_lolcow-%j.out
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=1G
#SBATCH -p debug
## Load modules, if needed
## Place to the directory where you container is, for example $HOME
cd $HOME
## Run the program using use 'srun'.
srun apptainer run lolcow_latest.sif
En el script anterior, se solicitó 1 CPU con 1GB de RAM por CPU en la partición debug para la tarea. Este contenedor se ejecutará una sola vez (--ntasks=1); si deseas ejecutarlo más veces, intenta cambiar el valor de --ntasks=, pero recuerda que esto solo funciona cuando el comando se ejecuta con srun.
Para enviar este script, simplemente ejecuta:
[rubaldo@khipu]$ sbatch lolcow.slurm
# When the job finish, check you output with cat
[rubaldo@khipu]$ cat apptainer_lolcow-4377.out
_____________________________
< Mon Mar 2 11:36:49 -05 2025 >
-----------------------------
\   ^__^
\  (oo)\_______
(__)\       )\/\
||----w |
||     ||
Para trabajos con GPU NVIDIA, en este caso usando la imagen cuda_12.8.0-base-ubuntu20.04.sif, el script de Slurm gpu_info.slurm debe ser:
#!/bin/bash
## Slurm Directives
#SBATCH --job-name=apptainer_gpu_info
#SBATCH --output=apptainer_gpu_info-%j.out
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=1G
#SBATCH --gres=gpu:1
#SBATCH -p debug-gpu
## Load modules, if needed
## Place to the directory where you container is, for example $HOME
cd $HOME/apptainer
## Run the program using use 'srun'.
srun apptainer exec --nv cuda_12.8.0-base-ubuntu20.04.sif ./gpu_info
Luego, para enviar este script:
[rubaldo@khipu]$ sbatch gpu_info.slurm
# Wait until the job finish. Then you will have an output like this:
[rubaldo@khipu]$ cat apptainer_gpu_info-4576.out
CUDA Device(s) Found: 1
Device 0 Information:
Name: Tesla T4
Compute Capability: 7.5
Total Global Memory: 14915 MB
Shared Memory per Block: 48 KB
Registers per Block: 65536
Max Threads per Block: 1024
Max Block Dimensions: (1024, 1024, 64)
Max Grid Dimensions: (2147483647, 65535, 65535)
Clock Rate: 1590 MHz
Memory Clock Rate: 5001 MHz
Memory Bus Width: 256 bits
Total Constant Memory: 64 KB
Warp Size: 32
Multiprocessor Count: 40
Si deseas recibir una notificación cuando tu trabajo falle o finalice, no olvides agregar las siguientes líneas a tu script de Slurm:
#SBATCH --mail-type=fail        # send email when job begins
#SBATCH --mail-type=end          # send email when job ends
#SBATCH --mail-user=<your email>
Referencias:
https://hpc.nmsu.edu/discovery/software/apptainer/using-containers/

---

## Jupyter con Conda

Fuente: https://docs.khipu.utec.edu.pe/tutoriales/jupyter-conda/

[Protected] Jupyter Lab / Notebook [conda]
Requirements
Interactive session
Batch session
6H3wR38JgQ5Rjlfev0a9QA==;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
This content is protected with AES encryption.
Contact your administrator for access to this page.

---

## Jupyter con Pip

Fuente: https://docs.khipu.utec.edu.pe/tutoriales/jupyter-pip/

[Protected] Jupyter Lab / Notebook [pip]
Requirements
Interactive session
Batch session
gDO0+q7AxQpeVxdUHe1hJg==;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
This content is protected with AES encryption.
Contact your administrator for access to this page.

---

## Reinicio de jobs en Pytorch (checkpointing)

Fuente: https://docs.khipu.utec.edu.pe/tutoriales/reinicio-job-pytorch/

Reinicio de Jobs
Visual Studio Code
Reinicio de Jobs
Reinicio de Jobs
Prerequisitos
Paso a paso
Apptainer
Prerequisitos
Paso a paso
Reinicio de jobs con PyTorch
El cluster Khipu es una herramienta valiosa cuyos recursos son compartidos y limitados. Lamentablemente no se puede ofrecer recursos infinitos siempre, ya que limitaría su disponibilidad para todos. Ante esto el cluster mantiene una política de restricciones en el tiempo de ejecución basada en ciclos.
Un ciclo de ejecución es la cantidad máxima de tiempo que un trabajo o job puede ser ejecutado de manera ininterrumpida en el cluster. Una vez su ciclo de ejecución llega al tiempo máximo, su trabajo será terminado por el gestor de colas. ¿Pero qué pasa cuando su trabajo requiere un tiempo mayor al que se disponible en un ciclo de ejecución? Pues, puede usar varios ciclos de ejecución para poder completarlo. De esta manera, si el cluster se encuentra libre, usted podrá obtener todos los ciclos que necesite inmediamente despues de su anterior. Y si el cluster tiene demanda, una vez acabado su anterior ciclo, su trabajo será encolado a la espera de que se liberen los recursos solicitados para poder ejecutar un nuevo ciclo de ejecución. Y así su trabajo podrá usar todos los ciclos que necesite para poder completarse.
Ahora que se ha explicado como funcionan los ciclos de ejecución en Khipu es importante mostrarlo con un ejemplo ¿no? En esta guía se va mostrar como podemos entrenar un modelo de PyTorch usando varios ciclos de ejecución en el cluster. Este ejemplo, aunque sencillo, puede ser luego adaptado y extendido para sus diferentes casos de uso.
Prerequisitos
Tener una cuenta de Khipu activa
Cargar los módulos de Python3
ml load python3
# Crear un entorno virtual
python3 -m venv venv
source venv/bin/activate
pip install torch
Paso a paso
Para el siguiente tutorial vamos a usar el siguiendo modelo en PyTorch:
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
91
92
93
94
95
96
97
98
99
100
101
102
103
104
105
106
107
108
109
110
111
112
113
114
115
116
117
118
119
120
121
122
123
124
125
126
127
128
129
130
131
132
133
134
135
136
137
138
139
140
141
142
143
144
145
146
147
148
149
150
151
152
153
154
155
156
157
158
159
160
161
162
163
164
165
166
167
168
169
170
171
172import torch
from torch import nn # nn contains all of PyTorch's building blocks for neural networks
#########################
## Inicialización de cuda
#########################
print(f"PyTorch version: {torch.__version__}")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Usando como device: {device}")
# Función utilitaria para configurar los seed en GPU o CPU
def set_seed(seed):
torch.manual_seed(seed)
if device == "cuda": torch.cuda.manual_seed(seed)
#########################
## Creación del dataset: creación de un conjunto de valores para la función f con adición de ruido
#########################
def f(x): return 7*x*x - x + 2
print("\nFunción original\t\t : f(x) = 7x^2 - x + 2")
set_seed(42)
X_all = torch.arange(-3.0, 3.0, 0.01, dtype=torch.float64,device="cpu").unsqueeze(dim=1)
y_all_clean = f(X_all)
y_all = y_all_clean + (torch.rand(size=X_all.shape, device="cpu")*4.0 - 2.0)
# Envio de los datos al device
X_all = X_all.to(device)
y_all_clean = y_all_clean.to(device)
y_all = y_all.to(device)
#############################
## Separar datos en training, testing and validation data
############################
def sample_values_from_dataset(X, y, n_samples, random_seed=1969):
set_seed(random_seed)
# retrieve index to further use in the complete dataset
random_indices = torch.randperm(n=X_all.shape[0], device="cpu")
random_indices = random_indices.to(device)
chosen_indices = random_indices[:n_samples]
return X[chosen_indices,:], y[chosen_indices,:]
# Obtener una muestra aleatoria de 16 números
X, y = sample_values_from_dataset(X_all, y_all, 16)
X_train, y_train = X[0:8], y[0:8]
X_val, y_val = X[8:12], y[8:12]
X_test, y_test = X[12:16], y[12:16]
print(f"Forma del set de entrenamiento\t : X = {X_train.shape}, y = {y_train.shape}")
print(f"Forma del set de validación\t : X = {X_val.shape}, y = {y_val.shape}")
print(f"Forma del set de testeo\t\t : X = {X_test.shape}, y = {y_test.shape}")
#################################
## Creación del modelo
#################################
class PolynomialRegressionModel(nn.Module):
def __init__(self, polynomial_degree):
super().__init__()
self.d = polynomial_degree
self.coefficients = nn.ParameterList([nn.Parameter(torch.randn(1, dtype=torch.float64)) for i in range(self.d+1)])
def forward(self, X):
result = torch.zeros(size=(X.shape[0],1), device=X.device)
for i in range(self.d+1):
result = result + (torch.pow(X,i) * self.coefficients[i])
return result
def __str__(self):
equation = f"f(x) = {self.coefficients[self.d].item():.4f} * x^{self.d}"
for i in range(self.d-1, -1, -1):
equation = equation + f" + {self.coefficients[i].item():.4f} * x^{i}"
return equation
# Lets set the random number generator seed to ensure we always generate the same model whenever we re-execute this code block.
set_seed(1969)
my_model = PolynomialRegressionModel(polynomial_degree=2).to(device)
print("\n-- Mi modelo lineal --")
print("La función de mi modelo:", my_model)
##########################################
## Entrenamiento de mi modelo
#########################################
import os
import time
EPOCH_SAVE_PATH = "last_completed_epoch.txt"
MODEL_SAVE_PATH = "last_model_state.pth"
# función utilitaria para recuperar la última epoca ejecutada
def get_last_completed_epoch():
if os.path.exists(EPOCH_SAVE_PATH):
with open(EPOCH_SAVE_PATH, "r") as file:
last_completed_epoch = int(file.read())
file.close()
else:
last_completed_epoch = -1
return last_completed_epoch
def train_model_v1(model,
X_train, y_train,
X_val, y_val,
learning_rate = 0.01,
number_of_epochs = 10,
verbosity_skip_level = 1):
loss_fn = nn.L1Loss()
optimizer = torch.optim.SGD(params=model.parameters(), lr=learning_rate)
curr_epoch = 0
while curr_epoch < number_of_epochs:
# Verifico si ejecuté previamente mi modelo
last_epoch_completed = get_last_completed_epoch()
if last_epoch_completed >= curr_epoch:
print(f"Restaurando el último estado del modelo en la época: {last_epoch_completed}")
# continuar con la siguiente epoca y restauro estado
curr_epoch = last_epoch_completed + 1
model = torch.load(f=MODEL_SAVE_PATH, weights_only=False)
# Entrenamiento
model.train()
y_hat = model(X_train)
loss = loss_fn(y_hat, y_train)
optimizer.zero_grad()
loss.backward()
optimizer.step()
# Validación
model.eval()
with torch.inference_mode():
val_hat = model(X_val)
val_loss = loss_fn(val_hat, y_val)
if (verbosity_skip_level > 0) and (curr_epoch % verbosity_skip_level == 0):
print(f"Epoca: {curr_epoch} | MAE Train Loss: {loss} | MAE Validation Loss: {val_loss} ")
# Guardamos el estado del modelo
torch.save(model, f=MODEL_SAVE_PATH)
with open(EPOCH_SAVE_PATH, "w") as file:
file.write(str(curr_epoch))
file.close()
curr_epoch += 1
time.sleep(0.01)
#####################################
## Ejecución
#####################################
print("\n** Entrenando mi modelo hasta 1000 epocas **")
train_model_v1(my_model, X_train, y_train, X_val, y_val,
learning_rate = 0.01, number_of_epochs = 1000,
verbosity_skip_level = 100)
print("\n La función de mi modelo final:", my_model)
# Eliminando archivo de epocas
if os.path.exists(EPOCH_SAVE_PATH):
os.remove(EPOCH_SAVE_PATH)
El siguiente job script incluye el parámetro --signal el cual se usa para enviar una señal 30 segundos antes de quel job se termine por falta de tiempo. Cuando esto ocurre se captura la señal y se añade un handler propio para ella. En este handler se guarda el output actual en otro archivo y se envía una solicitud de requeue. Un job requeue permite volver a enviar a ejecución el job actual. De esta manera, se solicita un nuevo ciclo de ejecución antes de que termine el actual. Para evitar que las solicitudes de requeue no tengan fin, se establece un parámetro que establece la cantidad máxima de reinicios.
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65#!/bin/bash
## Slurm Directives
#SBATCH --job-name sample-pytorch
#SBATCH --output sample-pytorch-%J.out
#SBATCH --error sample-pytorch-%J.err
#SBATCH -t 00:01:00
#SBATCH -p debug-gpu
#SBATCH --signal=B:SIGTERM@30
export PYTHONUNBUFFERED=TRUE
##############################################################
##  Gather some information from the job and setting limits ##
max_restarts=4      # tweak this number to fit your needs
scontext=$(scontrol show job ${SLURM_JOB_ID})
restarts=$(echo ${scontext} | grep -o 'Restarts=[0-9]*****' | cut -d= -f2)
outfile=sample-pytorch-${SLURM_JOB_ID}.out
##                                                          ##
##############################################################
##  Build a term-handler function to be executed            ##
##      when the job gets the SIGTERM                       ##
term_handler()
{
echo "Executing term handler at $(date)"
if [[ $restarts -lt $max_restarts ]];then
# Copy the log file because it will be overwriten
cp -v "${outfile}" "${outfile}.${restarts}"
scontrol requeue ${SLURM_JOB_ID}
exit 0
else
echo "Your job is over the Maximun restarts limit"
exit 1
fi
}
## Call the function when the jobs recieves the SIGTERM     ##
trap 'term_handler' SIGTERM
# print some job-information
cat <<EOF
SLURM_JOB_ID:         $SLURM_JOB_ID
SLURM_JOB_NAME:       $SLURM_JOB_NAME
SLURM_JOB_PARTITION:  $SLURM_JOB_PARTITION
SLURM_SUBMIT_HOST:    $SLURM_SUBMIT_HOST
Restarts:             $restarts
EOF
##                                                          ##
##############################################################
##          Here begins your actual program                 ##
##
## Place to your working directory, for example $HOME
cd ~/my-model-dir
## Load modules
ml load python3
source venv/bin/activate
srun python3 my_model.py
Note
Si por la naturaleza de su trabajo no puede adaptarlo para su ejecución en ciclos, es posible aumentarle su tiempo límite de ejecución. Sin embargo, estos casos deberían ser la excepción y no la regla.

---

