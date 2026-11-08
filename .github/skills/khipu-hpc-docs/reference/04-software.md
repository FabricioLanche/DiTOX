## Software disponible (lista de modulos)

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/software/lista/

Software disponible
Enviar jobs
Software
Software
Uso de software
Software disponible
Software disponible
Módulos disponibles
Instalación
Ejemplos
Módulos disponibles
Lista de software
Módulos disponibles
A continuación se comparte la lista de software disponible:
------------------------------- /opt/ohpc/pub/moduledeps/gnu12-openmpi4 -------------------------------
ParMETIS/4.0.3        imb/2021.3                  petsc/3.18.1        sionlib/1.7.7
SuiteSparse/7.11.0    mfem/4.4                    phdf5/1.10.8        slepc/3.18.0
adios/1.13.1          mpiP/3.5                    pnetcdf/1.12.3      superlu_dist/6.4.0
boost/1.81.0          mumps/5.2.1                 ptscotch/7.0.1      tau/2.31.1
dimemas/5.4.2         netcdf-cxx/4.3.1     (D)    py3-mpi4py/3.1.3    trilinos/13.4.0
dune/2.10.0           netcdf-fortran/4.6.0 (D)    py3-scipy/1.5.4     zoltan/16.1.0
extrae/3.8.3          netcdf/4.9.0         (D)    scalapack/2.2.0
fftw/3.3.10           omb/6.1                     scalasca/2.5
hypre/2.18.1          opencoarrays/2.10.1         scorep/7.1
----------------------------------- /opt/ohpc/pub/moduledeps/gnu12 ------------------------------------
GKlib/0.0.1        impi/2021.10.0   (D)    netcdf-fortran/4.6.0        python3/3.8.0
METIS/5.2.1        impi/2021.15            netcdf/4.9.0                python3/3.10.2
R/4.2.1            likwid/5.2.2            openblas/0.3.21             python3/3.11.11
cjson/1.7.18       metis/5.1.0             openmpi4/4.1.6       (L)    python3/3.13.2  (D)
flexiblas/3.4.5    mpfr/4.2.2              pdtoolkit/3.25.1            scotch/6.0.6
gmp/6.3.0          mpich/3.4.3-ofi         plasma/21.8.29              superlu/5.2.1
gsl/2.7.1          mvapich2/2.3.7          py3-numpy/1.19.5
hdf5/1.10.8        netcdf-cxx/4.3.1        python3/3.7.0
-------------------------------------- /opt/ohpc/pub/modulefiles --------------------------------------
EasyBuild/4.9.4          cuda/12.8      (D)    intel/2025.1.0          pmix/4.2.9
autotools         (L)    gnu10/10.5.0          intel/2025.1            prun/2.2        (L)
charliecloud/0.15        gnu12/12.4.0   (L)    julia/1.11.3            spack/0.22.2
cmake/3.24.2             gnu14/14.2.0          libfabric/1.19.0 (L)    spack/1.0.1     (D)
cmake/4.3.2       (D)    gnu9/9.2.1            magpie/3.0              speedtest/1.2.0
comsol/6.0               gnu9/9.4.0     (D)    miniconda/3.0           texlive/2025
comsol/6.4        (D)    gromacs/2026.1        nvidia/2025             ucx/1.15.0      (L)
cuda/10.1                gurobi/12.0.1         nvtop/3.2.0      (L)    valgrind/3.19.0
cuda/11.4                hwloc/2.7.2    (L)    ohpc             (L)
cuda/11.8                ib-mon/1.3.3          os
cuda/12.6                intel/2023.2.1 (D)    papi/6.0.0
Where:
D:  Default Module
L:  Module is loaded

---

## Uso de software (modulos)

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/software/uso/

Uso de software
Enviar jobs
Software
Software
Uso de software
Uso de software
Módulos
Buscar módulos
Cargar módulos
Descargar módulos
Colección de módulos
Obtener información y ayuda de los módulos
Software disponible
Instalación
Ejemplos
Módulos
Buscar módulos
Cargar módulos
Descargar módulos
Colección de módulos
Obtener información y ayuda de los módulos
Uso de software
Módulos
Usted puede listar los módulos que se encuentran disponibles con el siguiente comando.
ml av
# O también
module avail
Buscar módulos
Usted también puede buscar módulos mediante el comando avail. Por ejemplo, para listar todas las versiones de MPICH 3, ejecutaremos:
module avail mpich/3
Y obtendremos una salida similar a:
--------------------------------------- /opt/apps/modulefiles ----------------------------------------
mpich/1.5   mpich/3.1.4 mpich/3.2.1 mpich/3.3.2 mpich/3.4.0 mpich/4.0
Cargar módulos
Usted puede cargar un modulo a su ambiente de trabajo a traves del comando module load. Al cargar un modulo, usted carga todas las variables de ambiente necesarias para poder utilizar dicho paquete de software.
Es importante tomar en cuenta que:
El comando es case-sensitive a los nombres de los módulos
Cuando usted usa module load se cargan también las dependencias del modulo. No es necesario cargarlas de manera separada.
Cuando usted enviá sus jobs que requieren de un módulo, no olvide añadirlo con module load a su bash script.
Por ejemplo, si desea cargar gcc versión 7.5.0, deberá ejecutar:
module load gcc/7.5.0
También puede cargar varios módulos al mismo tiempo:
module load gcc/7.5.0 mpich/3.3.2
Descargar módulos
Una vez terminado de usar el software, es recomendable hacer module unload <modulename>. Este proceso también se debe realizar e los scripts de los jobs.
module unload gcc/7.5.0
También puede descargar todos los módulos a la vez con:
module purge
Colección de módulos
En casos cuando se trabaja con gran cantidad de módulos, puede ser molestoso estar cargando cada uno de ellos. Ante esto existe la opción de añadir dicho módulos a una colección y de este modo solo cargar la colección en lugar que todos los módulos de manera individual.
Guardar colecciones
Para ello, usted deberá cargar previamente los módulos que desea añadir a la colección y despues ejecutar.
module save <collection-name>
Cargar colecciones
Usted podrá cargar la colección creada con:
module restore <collection-name>
Listar colecciones
Para listar las colecciones creadas:
module savelist
Obtener información y ayuda de los módulos
Si desea mostrar la información de configuración de un modulo en especifico:
module show <modulename> #or
module display <modulename>
Usted puede obtener una breve descripción sobre un módulo ejecutando:
module help <modulename>/<version>
Si usted no encuentra un paquete y considera que su instalación como modulo podría ser beneficiosa para otros usuarios más, puede escribirnos a khipu@utec.edu.pe para solicitar su instalación.

---

## Instalacion de software / pedidos

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/software/instalacion/

Instalación
Enviar jobs
Software
Software
Uso de software
Software disponible
Instalación
Instalación
Requisitos para instalar software
Proceso de instalación
Ejemplos
Requisitos para instalar software
Proceso de instalación
Instalación de Software
El siguiente documento describe como instalar software en Khipu para un proyecto o curso. Antes de realizar una instalación, por favor revise si el software ya se encuentra disponible como módulo con el comando module avail o ml av.
Requisitos para instalar software
En caso de software licenciado, el usuario debe proveer la licencia y/o instalador del software al administrador para ser instalado.
El usuario puede instalar el software y libraries necesarios en su /home/<username>/, en caso de no requerir licencia o ser de código abierto.
El usuario puede compilar en el nodo líder antes de enviar un job a ejecutar. No enviar jobs de compilación a la fila del cluster.
Siendo Khipu un cluster enfocado al procesamiento y HPC; no se instalarán bases de datos, containers o máquinas virtuales.
Si el software o library requiere permisos especiales para instalación, solamente el profesor encargado del curso o un investigador de proyecto pueden solicitar la instalación bajo coordinación con el administrador.
Si el software que planea instalar posee dependencias como librerías, interfaces o módulos; revise primero si ya se encuentran disponibles en el cluster antes de instalarlas por su cuenta.
Para entrar en contacto con el administrador del cluster, por favor enviar un mensaje a khipu@utec.edu.pe.
Proceso de instalación
Tal como se mencionó anteriormente, usted puede instalar software libre o que no requiere licencia en su espacio personal de trabajo. Sin embargo, antes de proceder con la instalación asegúrese que dicho software no requiere permisos root para ser instalado. Una vez echo esto, usted deberá moverse al directorio en el cual planea realizar la instalación y seguir las instrucciones del proveedor del software que planea instalar.
Por lo general, los pasos son similares, es por ello que a continuación se muestra un ejemplo realizando la instalación de la librería Zlib, un software usado para comprimir y descomprimir data.
Creamos un directorio en el cual almacenaremos los códigos fuente y binarios de las apps que vamos a instalar.
mkdir myApps
cd myApps
APPS_DIR=$(pwd)
mkdir sources      # source files
mkdir apps         # binary files
Entraremos al directorio sources/ y descargaremos el código fuente del paquete desde su sitio web.
cd $APPS_DIR/sources
wget  https://www.zlib.net/zlib-1.2.12.tar.xz
Descomprimimos el archivo descargado.
tar -xvf zlib-1.2.12.tar.xz
Entramos al nuevo directorio con los contenidos del paquete que acabamos de descomprimir.
cd zlib-1.2.12/
Cargamos el módulo del compilador para poder crear los binarios a partir del código fuente. En este caso cargaremos GCC 7.5.0, sin embargo es recomendable seguir los requisitos de cada software.
module load gcc/7.5.0
Por lo general, muchos código fuentes se compilan usando simplemente make y make install. Sin embargo, nosotros debemos configurar previamente el lugar donde se guardaran los binarios, ya que si no hacemos esto, se guardaran en los directorios /usr/lib a los cuales no tenemos acceso. Por lo general, bastará con configurar el argumento --prefix.
./configure --prefix=$APPS_DIR/apps/zlib
Para mayor información de como configurar el path de instalación, es recomendable seguir la documentación del software a instalar.
Compilamos el código fuente.
make
Instalamos el software.
make install    # copia los binarios a --prefix
Si nos movemos al directorio donde se encuentra la instalación, encontraremos por lo general una lista de directorios como la siguiente.
cd $APPS_DIR/apps/zlib
ls
# salida del comando anterior
include  lib  share
En esos directorios se encuentran los binarios con los cuales podremos hacer uso del software.

---

