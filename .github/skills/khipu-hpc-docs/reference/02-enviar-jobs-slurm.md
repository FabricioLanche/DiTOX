## Enviar jobs (overview + uso del nodo de acceso)

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/enviar-jobs/

Sobre el envío de Jobs
Enviar jobs
Enviar jobs
Comandos Básicos
Particiones
Nodos
Opciones de Slurm
Jobs interactivos
Monitoreo de jobs
Carpeta /local
Software
Ejemplos
Uso del nodo de acceso
Sobre el envío de Jobs
¡El nodo de acceso no es para realizar cómputos!
Use Slurm para enviar sus cargas de trabajo a los diferentes nodos de cómputo.
Khipu es un recurso compartido por múltiples usuarios al mismo tiempo. Para asignar y gestionar los recursos de manera justa hacemos uso del gestor de trabajos Slurm. A través de Slurm los usuarios puede enviar, cancelar y revisar sus cargas de trabajo o jobs a los diferentes nodos de cómputo disponibles.
Los jobs pueden ser ejecutados de dos maneras distintas:
Modo batch: permite enviar un script que contiene todo lo necesario para la ejecución de su job. El cual se ejecutará de manera ininterrupida por el perido de tiempo asignado en el script y permitido a su tipo de cuenta. De esta manera usted manda a ejecutar su carga de trabajo y no tiene la necesitar de mantenerse conectado a Khipu para que continue su ejecución. La salida de su job será escrita de manera continua en un archivo, el cual usted puede consultar multiples veces para ver el avance de su trabajo hasta su finalización.
Modo interactivo: permite a los usuarios interactuar con su job en ejecución de manera directa a través de la línea de comandos. Este modo es similar a reservar recursos en una nodo, conectarte a él y luego de manera manual (interactiva) ejecutar cada unos de los comandos que requiera para completar su trabajo. Sin embargo, si su conexión con el nodo es interrupida o deja de tener actividad, su job será terminado. Este tipo de jobs es ideal para cargas de trabajo pequeñas, preparar o realizar pequeñas pruebas de la ejecución de jobs más largos o realizar labores de debugging.
Los jobs que envíe a través de Slurm serán puestos en ejecución dependiendo de su tipo de cuenta y la cantidad de recursos solicitados (núcleos CPU, memoría RAM o  GPU). Generalmente, los jobs con pedidos de recursos más modestos y acotados suelen esperar menos tiempo en la fila de Slurm. Si desconoce la cantidad de recursos que su job demandará puede usar las particiones debug o debug-gpu para realizar pruebas antes de enviar sus jobs a otras particiones más demandadas.
Uso del nodo de acceso
El nodo de acceso es compartido por todos los usuarios y, como su nombre lo indica, debe ser usado para el acceso al cluster y la ejecución de tareas administrativas como:
Compilación de código.
Descarga de archivos. El nodo de acceso es el único nodo con salida a internet.
Creación de ambientes de trabajo (virtualenv) e instalación de paquetes de Python
Envío y manejo de jobs
Transferencia de archivos
Pequeñas tareas de pre y post-procesamiento que no demanden de uso alto de recursos en CPU y RAM.
Todas las tareas que no se ajusten a las indicaciones dadas sobre el uso del nodo de acceso serán canceladas sin previo aviso y el usuario responsable será sancionado de acuerdo a nuestra política de uso.

---

## Comandos basicos de Slurm

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/enviar-jobs/comandos-basicos/

Comandos básicos de SLURM
Enviar jobs
Enviar jobs
Comandos Básicos
Comandos Básicos
Creación de un batch script
Envío de un batch job
Examinar la cola de ejecución
Cancelar trabajos
Ver información sobre los nodos y particiones
Bonus: Obtener detalles de un job
Particiones
Nodos
Opciones de Slurm
Jobs interactivos
Monitoreo de jobs
Carpeta /local
Software
Ejemplos
Creación de un batch script
Envío de un batch job
Examinar la cola de ejecución
Cancelar trabajos
Ver información sobre los nodos y particiones
Bonus: Obtener detalles de un job
Comandos Básicos
En esta guía se van a desarrollar algunos comandos básicos de Slurm. Si es su primera vez usando Slurm, le será de mucha utilidad acompañar esta lectura realizando pruebas de los comandos mencionados en el cluster. Al inicio puede resultar un poco tedioso escribir nuestras cargas de trabajo en scripts, sin embargo poco a poco le resultará más sencillo y a la larga usted manejará una herramiento valiosa y ampliamente usada en el mundo del HPC.
Los principales comandos de Slurm se muestran en la siguiente tabla:
Comando
Descripción
sbatch
Envía un batch script
srun
Ejecuta un job paralelo (step)
squeue
Muestra información de la cola de trabajos
scancel
Envía un signal o cancela un job, array de jobs o job steps.
sinfo
Muestra información de las particiones.
Creación de un batch script
Un batch script es un archivo que indica los recursos necesarios y los pasos a seguir para la ejecución de un determinado job. A continuación se muestra un ejemplo:
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
20#!/bin/bash
#SBATCH --job-name=nombre_del_job
#SBATCH --partition=debug
#SBATCH --ntasks=1 --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=nombre_archivo.out
#SBATCH --error=nombre_archivo.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=user@example.com
## Especificar el directorio de trabajo
cd <mi-directorio-de-trabajo>
## Cargar los módulos necesarios
ml load <module>/<version>
## Ejecute su programa
srun <mi-programa>
En este ejemplo #!/bin/bash indica que debe ser interpretado como un script de bash. Las siguientes líneas que contienen #SBATCH son directivas que especifican determinadas opciones disponibles en Slurm usando la siguiente sintaxis:
#SBATCH <opción>=<valor>
Por ejemplo, la línea 3 #SBATCH --job-name=nombre_del_job indica cual es el nombre del job.
La línea 4, especifica que el job se ejecutará en la partición debug.
Las línea 5 y 6, especifican los recursos computacionales que serán usados para la ejecución del job. En este ejemplo, --ntasks indica que se ejecutará un proceso, --cpus-per-task que se usarán 4 núcleos CPU por cada proceso y --mem que se utilizará 4GB de RAM en total.
La línea 7 indica que el límite máximo de duración del job será de 10 minutos. Si el job pasa de esa duración, será cancelado.
Las líneas 8 y 9 indican donde se escribirán la salida estandar --output y la salida en caso de error --error. Si no se indican, tomaran un valor por defecto adicionado al identificador del job.
La línea 10 indica que se envíe un mail cuando el job llegue a los estados de END (culminación normal) o FAIL (culminación por error).
La línea 14 especifica el directorio de trabajo donde se encuentra el programa que será ejecutado. Si no lo especifica, usará el directorio desde donde esté enviando el job. Es altamente recomendado especificar su directorio de trabajo.
La línea 17 indica cuales [módulos][modulos] deberán ser cargados para la ejecución del job.
Finalmente, la línea 20 indica cual será el comando que será ejecutado. Es importante anteponer srun antes del comando que ejecutará. Por ejemplo: srun python3 myapp.py o srun ./myapp.
Envío de un batch job
Para enviar el job script que se creó en el paso anterior deberemos usar el comando sbatch, el cual posee la siguiente sintaxis:
sbatch [opciones] nombre-de-mi-job.slurm [argumentos del job ...]
Donde las [opciones] tienen las mismas estructura que aquellas que escribimos en el batch script, pero sin la palabra #SBATCH. Aquellas opciones que especifiquemos al momento de ejecutar sbatch tiene precedencia por sobre aquellas que se encuentren dentro del script. Por ejemplo, si yo ejecuto sbatch --partition=standard mi-scrip.slurm, donde mi-script.slurm es el batch script anterior, el job se ejecutará en la partición standard en lugar de debug que fue especificada dentro del job. No siempre será necesario sobreescribir las opciones que se encuentran dentro del script. Para la mayoría de casos bastará con ejecutar:
sbatch nombre-de-mi-job.slurm
Si bien no hay una restricción en la extensión que debe de tener nuestro batch script, es una buena paractica usar la extension *.slurm para diferenciarlo de los bash script *.sh tradicionales.
Examinar la cola de ejecución
Cuando usted envía su job, no necesariamente se ejecutará de manera inmediata. Este puede estar en espera por un tiempo hasta que se liberen los recursos necesarios para que pueda entrar a ejecución. Para ver los jobs que se encuentran en espera y en ejecución usaremos el comando squeue.
squeue
El cual nos mostrará un resultado parecido al siguiente:
JOBID PARTITION    NAME     USER   ST   TIME  NODES NODELIST(REASON)
5757       gpu pretrain some-user  PD   0:00      5 (PartitionNodeLimit)
5758  standard     bash some-user  PD   0:00      1 (QOSMaxWallDurationPerJobLimit)
5741       gpu fn_somet some-user  R    1:17:21   1 g001
Aquí podemos notar que hay tres jobs, de los cuales uno se encuentra en ejecución (por eso tienen la R de running) y otro dos se encuentra pendientes PD. Es importante visualizar que los jobs en pendiente tienen en el apartado de NODELIST(REASON), una explicación rápida de por qué se encuentra en ese estado. En este ejemplo, (PartitionNodeLimit) me indica que estoy tratando de reservar más nodos de los permitidos en esa partición y (QOSMaxWallDurationPerJobLimit) que estoy tratando de reservar más tiempo del permitido por cada job.
En algunos casos desearemos solamente visualizar el estado de nuestros jobs. Para ello ejecutaremos:
squeue --me
Cancelar trabajos
En algunos casos necesitaremos cancelar nuestro job porque tal vez faltó añadir algo, o no está ejecutando como esperamos. En sos casos bastará con ejecutar el comando scancel acompañado del id del job:
scancel <job-id>
El identificador del job puede obtenerse mirando la cola de ejecución con squeue.
Ver información sobre los nodos y particiones
Para obtener información sobre las particiones, su estado y nodos disponibles ejecutaremos  el comando sinfo. El cual nos mostrará en patalla una salida similar a la siguiente:
PARTITION    AVAIL  TIMELIMIT  NODES  STATE NODELIST
debug*          up   infinite      1   idle n003
debug-gpu       up   infinite      1    mix g001
standard        up   infinite      4   idle n[003-006]
big-mem         up   infinite      3   idle ag001,g002,n006
gpu             up   infinite      1    mix g001
gpu             up   infinite      2   idle ag001,g002
data-science    up   infinite      1   down ds001
Ahí podemos ver que algunos nodos/particiones se encuentran sin uso ìdle, mientras que otras poseen algunos nodos en uso y otros en desuso mix, o se encuentran caídos down. Los nodos pueden encontrarse caídos por errores en su funcionamiento, fallas en la conectividad o por la realización de trabajos de mantenimiento. Si desea obtener mayores detalles del porqué del estado de un nodo caído, puede ejecutar el comando sinfo -R. El cual nos mostrará en patalla una salida similar a la siguiente:
REASON               USER      TIMESTAMP           NODELIST
Mantenimiento progra root      2025-05-05T17:56:50 ds001
En este caso podemos observar que el motivo de la caída del nodo es debido a unos trabajos de manteniento.
Bonus: Obtener detalles de un job
En algunas ocasiones, olvidamos detalles del job que estamos ejecutando o que se encuentra por ejecutar. En esos casos podemos usar el comando scontrol show job <job-id> para obtener mayor información sobre ese job.
Por ejemplo, si quiero ver detalles del job 1077 ejecutaré:
scontrol show job 1077
Y obtendré una respuesta en pantalla parecida a la siguiente:
JobId=1077 JobName=CudaJob
UserId=alan.turing(1000) GroupId=alan.turing(1000) MCS_label=N/A
Priority=1683 Nice=0 Account=pregrado QOS=a-pregrado
JobState=COMPLETED Reason=None Dependency=(null)
Requeue=1 Restarts=0 BatchFlag=1 Reboot=0 ExitCode=0:0
RunTime=00:00:02 TimeLimit=00:10:00 TimeMin=N/A
SubmitTime=2024-11-06T02:41:48 EligibleTime=2024-11-06T02:41:48
AccrueTime=2024-11-06T02:41:48
StartTime=2024-11-06T02:41:48 EndTime=2024-11-06T02:41:50 Deadline=N/A
SuspendTime=None SecsPreSuspend=0 LastSchedEval=2024-11-06T02:41:48 Scheduler=Main
Partition=debug AllocNode:Sid=khipu:2943597
ReqNodeList=(null) ExcNodeList=(null)
NodeList=n005
BatchHost=n005
NumNodes=1 NumCPUs=1 NumTasks=1 CPUs/Task=1 ReqB:S:C:T=0:0:*:*
ReqTRES=cpu=1,mem=100M,node=1,billing=1
AllocTRES=cpu=1,mem=100M,node=1,billing=1
Socks/Node=* NtasksPerN:B:S:C=0:0:*:* CoreSpec=*
MinCPUsNode=1 MinMemoryCPU=100M MinTmpDiskNode=0
Features=(null) DelayBoot=00:00:00
OverSubscribe=OK Contiguous=0 Licenses=(null) Network=(null)
Command=/home/alan.turing/gpu_job_shard.sh
WorkDir=/home/alan.turing
StdErr=/home/alan.turing/slurm-1077.out
StdIn=/dev/null
StdOut=/home/alan.turing/slurm-1077.out
Power=

---

## Particiones

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/enviar-jobs/particiones/

Particiones
Enviar jobs
Enviar jobs
Comandos Básicos
Particiones
Particiones
Detalles de las particiones
debug
debug-gpu
standard
big-mem
gpu
data-science
Nodos
Opciones de Slurm
Jobs interactivos
Monitoreo de jobs
Carpeta /local
Software
Ejemplos
Detalles de las particiones
debug
debug-gpu
standard
big-mem
gpu
data-science
Particiones
Las particiones son grupos de nodos que tienen características similares y que comparten un mismo conjunto de restricciones.
Las particiones permiten organizar los recursos disponibles y gestionar de manera eficiente cómo se asignan las tareas o trabajos. Khipu posee seis diferentes particiones en Slurm.
Nombre de partición
Descripción
debug
partición para probar ejecuciones pequeñas en CPU con propósitos de debugging
debug-gpu
partición para probar ejecuciones pequeñas en GPU con propósitos de debugging
standard
partición de uso general en CPU
big-mem
partición de uso general en CPU con gran cantidad de memoria
gpu
partición de uso general en GPU
data-science
partición de Ciencia de Datos
El número de jobs y la cantidad de recursos que pueden ser reservados dependerá de la partición seleccionada y su tipo de usuario. Para listar las particiones que se encuentran disponibles para su usuario, ejecute el comando:
sinfo -O "partition"
Detalles de las particiones
A continuación se listan las particiones existentes y el detalle de cada una de ellas.
Partición
Nodos
Total de Cores
Total de Memoria RAM (GB)
Total shards de GPU
Máx duración del Job (min)
debug
n003
32
160
-
30
debug-gpu
g001
32
160
32
30
standard
n00[3-6]
144
1385
-
depende del tipo de usuario
big-mem
g002, ds001, ag001
224
3095
-
depende del tipo de usuario
gpu
g00[1-2], ag001
208
2224
208
depende del tipo de usuario
data-science
ds001
96
1031
96
depende del tipo de usuario
debug
Tiempos de espera más cortos y tiempo de ejecución pequeño. Utilice esta partición para probar la ejecución de su job antes de enviarlo a una partición de más recursos.
debug-gpu
Tiempos de espera más cortos y tiempo de ejecución pequeño. Utilice esta partición para probar la ejecución de su job en GPU antes de enviarlo a una partición de más recursos.
standard
Partición de uso general para tareas que requieren cores de CPU. Utilice esta partición para ejecutar tareas intensas en uso de CPU. Los tiempos de espera en cola dependerán de la cantidad de usuarios que se encuentren usando la partición. Procure dimensionar correctamente su trabajo para disminuir su tiempo de espera en la cola. Use la partición debug para dicho propósito.
big-mem
Partición de uso general para tareas que requieren cores de CPU y gran cantidad de memoria RAM. Utilice esta partición para ejecutar tareas intensas en memoria. Los tiempos de espera en cola dependerán de la cantidad de usuarios que se encuentren usando la partición. Procure dimensionar correctamente su trabajo para disminuir su tiempo de espera en la cola. Use la partición debug para dicho propósito.
gpu
Partición de uso general para tareas que requieren cores de GPU. Es una de las particiones de mayor demanda en Khipu, es por ello que no es posible reservar GPUs de manera exclusiva. El uso de la GPU es compartido a traves de sharding. Los tiempos de espera en cola dependerán de la cantidad de usuarios que se encuentren usando la partición. Procure dimensionar correctamente su trabajo para disminuir su tiempo de espera en la cola. Use la partición debug-gpu para dicho propósito.
data-science
Partición de uso general, pero con acceso priorizado para los miembros de la facultad de Ciencia de Datos. Dentro de esta partición se encuentra el nodo ds001, el único nodo de cómputo con acceso a internet. Cuenta con una tarjeta GPU compartida a través de sharding.

---

## Nodos

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/enviar-jobs/nodos/

Nodos
Enviar jobs
Enviar jobs
Comandos Básicos
Particiones
Nodos
Nodos
Particiones del Nodo ag001
Envío de tareas con GPUs específicos
Opciones de Slurm
Jobs interactivos
Monitoreo de jobs
Carpeta /local
Software
Ejemplos
Particiones del Nodo ag001
Envío de tareas con GPUs específicos
Nodos
Los nodos están configurados en SLURM de modo que todos los recursos (memoria, CPUs, GPUs) se encuentren disponibles para reservar al enviar tareas.
Las configuraciones de cada nodo se encuentran listadas a continuación:
Nodo
Configuración
n003
CPUs: 64RealMemory: 225316MiB
n004
CPUs: 64RealMemory: 225316MiB
n005
CPUs: 64RealMemory: 193059MiB
n006
CPUs: 96RealMemory: 1031783MiB
g001
Gres:- gpu: tesla:1,shard:16CPUs: 64RealMemory: 192052MiB
g002
Gres:- gpu: rtxa6000:1,shard:48CPUs: 96RealMemory: 1031783MiB
ag001
Gres:- gpu: a100:1- gpu: a100_3g.20gb:1- gpu: a100_2g.10gb:1- gpu: a100_1g.5gb:2- shard:80CPUs: 128RealMemory: 1031900MiB
ds001
Gres:- gpu: rtxa6000:1,shard:48CPUs: 96RealMemory: 1031783MiB
Donde Gres representa recursos genéricos (Generic RESources).
Particiones del Nodo ag001
El nodo ag001 cuenta con dos GPUs NVIDIA A100 PCIe-40GB. Estos GPUs son los únicos en Khipu que soportan la funcionalidad Multi Instance GPU (MIG), que permite dividir un GPU en sub-instancias aisladas, con múltiples configuraciones posibles.
La distribución de GPUs es la siguiente:
Una de las GPUs se mantiene sin modificar
Una de las GPUs se utiliza para proporcionar 4 instancias MIG:
1 instancia de tipo 3g.20gb
1 instancia de tipo 2g.10gb
2 instancias de tipo 1g.5gb
Los nombres de cada tipo de instancia indican sus capacidades. Por ejemplo, las instancias de nombre 3g.20gb cuentan con 3/7 de la capacidad de procesamiento del GPU, y con 20GiB de VRAM. Estas instancias son detectadas por SLURM como GPUs independientes, y se pueden solicitar con normalidad. La configuración se encuentra ilustrada en la siguiente imagen:
Note
Dado que los GPUs del nodo ag001 fueron redistribuidos para contar con más instancias de distintas capacidades, se sugiere no utilizar shards cuando trabajemos con este nodo, dado que de momento estas no se encuentran distribuidas equitativamente. En lugar de eso, podemos reservar instancias más pequeñas según los recursos que necesitamos.
Envío de tareas con GPUs específicos
Si, por ejemplo, necesitamos utilizar un GPU específico, podemos especificarlo al enviar la tarea con sbatch. El siguiente ejemplo reserva dos instancias de 1g.5gb del nodo ag001:
#!/bin/bash
#SBATCH --job-name=mi_trabajo    # Nombre del trabajo
#SBATCH --partition=gpu          # Partición a usar
#SBATCH --nodelist=ag001         # Nodos a utilizar
#SBATCH --gres=gpu:a100_1g.5gb:2 # GRES a utilizar
#SBATCH ...
# Continuar con el envío de la tarea
module load ...
Cabe resaltar que no podemos reservar un GPU que no está disponible en un nodo, por lo que es mejor especificar el nodo que deseamos reservar en caso querramos utilizar un GPU en específico.

---

## Opciones de Slurm

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/enviar-jobs/opciones-de-slurm/

Opciones de Slurm
Enviar jobs
Enviar jobs
Comandos Básicos
Particiones
Nodos
Opciones de Slurm
Opciones de Slurm
Opciones baśicas del job
Opciones para la distribución de tareas
Opciones para la solicitud de CPU
Opciones para la solicitud de memoria RAM
Opciones para la solicitud de GPU
Opciones para el envío de mails
Jobs interactivos
Monitoreo de jobs
Carpeta /local
Software
Ejemplos
Opciones baśicas del job
Opciones para la distribución de tareas
Opciones para la solicitud de CPU
Opciones para la solicitud de memoria RAM
Opciones para la solicitud de GPU
Opciones para el envío de mails
Opciones más comunes de Slurm
A continuación se listan algunas de las opciones más comunes al momento de enviar jobs usando Slurm. Notaremos que existe una opción larga y otra corta para referirnos al mismo parámetro.
Opciones baśicas del job
Opción Larga
Opción Corta
Descripción
Ejemplo
--job-name
-J
Establece un nombre para el trabajo.
--job-name=miTrabajo
--partition
-p
Especifica la partición a la que se enviará el trabajo.
--partition=debug
--time
-t
Establece un límite de tiempo para el trabajo. Formato: días-horas:minutos:segundos.
--time=01:30:00
--output
-o
Indica el nombre del archivo donde se guadará la salida stdout
--output=salida-del-job.out
--error
-e
Indica el nombre del archivo donde se guadará la salida stderr
--error=errores-del-job.err
Si no se establecen valores para --output y/o --error se crearán archivos con el siguiente patrón slurm-%j.out donde %j% es el id del job.
Opciones para la distribución de tareas
Opción Larga
Opción Corta
Descripción
Ejemplo
--nodes
-N
Número de nodos a asignar para el trabajo.
--nodes=2
--ntasks
-n
Número de tareas a lanzar.
--ntasks=4
--ntasks-per-node
Número de tareas por nodo.
--ntasks-per-node=3
Opciones para la solicitud de CPU
Opción
Descripción
Ejemplo
--cpus-per-task
Indica el número de cores por tarea
--cpus-per-task=3
Opciones para la solicitud de memoria RAM
Opción
Descripción
Ejemplo
--mem
Establece la memoria requerida por nodo.
--mem=4G
--mem-per-cpu
Establece la mínima memoria requerida por cada núcleo CPU.
--mem-per-cpu=200M
--mem-per-gpu
Establece la mínima memoria requerida por cada GPU reservado.
--mem-per-gpu=2G
Para la memoria RAM la unidad por defecto son los MB y pueden usarse [K|M|G|T] como sufijos para expresar las unidades de memoría. Por ejemplo: 100K son 100 Kilobytes,y 10G son 10 gibabytes.
Opciones para la solicitud de GPU
Opción
Descripción
Ejemplo
--gres=shard:<numero>
Establece la cantidad de GPU shards a usar. Permite el uso compartido de GPU (Recomendado).
--gres=shard:1
--gres=gpu:<numero>
Establece la cantidad de GPUs para uso exclusivo.
--gres=gpu:1
En ambas opciones es posible adicionar el tipo de GPU que se desea reservar --gres=<recurso>:<tipo>:<cantidad>. Actualmente se dispone de los siguientes tipos de GPU: tesla, a100 y rtxa6000. Usando cualquiera de estas opciones, los ejemplos anteriores podrían variar a --gres=shard:a100:1 o --gres=gpu:tesla:1.
Opciones para el envío de mails
Es posible habilitar las notificaciones por correo electrónico cada vez que ocurra un determinado evento como el inicio de un job o su falla. Esta opción es bastante útil ya que permite conocer el estado del job sin la necesidad de estar revisando constantemente la cola de ejecución. Utilice la opción ALL para recibir notificaciones al iniciar y terminar un job. Opciones disponibles ALL, BEGIN, END, FAIL, NONE
Opción
Descripción
Ejemplo
--mail-type
Envía un mail cada vez que ocurra un determinado evento.
--mail-type=END,FAIL
--mail-user
Establece el mail al cual se enviarán las notificaciones.
--mail-user=<mi-coreo-electronico>
Para más información, revisar la documentación oficial de sbatch

---

## Jobs interactivos

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/enviar-jobs/jobs-interactivos/

Jobs Intercativos
Enviar jobs
Enviar jobs
Comandos Básicos
Particiones
Nodos
Opciones de Slurm
Jobs interactivos
Monitoreo de jobs
Carpeta /local
Software
Ejemplos
Jobs interactivos
Para iniciar un job de manera interactiva deberá ejecutar el comando srun usando la siguiente sintaxis:
srun [recursos] --pty /bin/bash
Por defecto todos los jobs interactivos tienen una duración límite de 30 minutos. Usted puede modificar los recursos a reservarse y el tiempo límite de duración modificando [recursos] con los flags listados aquí.
Por ejemplo:
Si desea solicitar 4 cores y 4GB RAM en la partición standard.
srun -c 4 --mem=4GB -p standard --pty /bin/bash
Si desea solicitar 1 shard GPU en la partición debug-gpu.
srun --gres=shard:1 -p debug-gpu --pty /bin/bash
!!! warning Manténgase conectado mientras usa jobs interactivos
Si usted pierde conexión, deja de tener actividad o sale de su sesión, perderá acceso a su job interactivo. Para mitigar la cancelación de su job por inactividad puede usar el comando screen. Sin embargo, úselo de manera razonable ya que usted estará manteniendo en reserva recursos que no está usando.

---

## Jobs GPU (pagina vacia en la fuente)

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/enviar-jobs/jobs-gpu/

Jobs gpu
Jobs gpu

---

## Monitoreo de jobs

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/enviar-jobs/monitorear/

Monitoreo de jobs
Enviar jobs
Enviar jobs
Comandos Básicos
Particiones
Nodos
Opciones de Slurm
Jobs interactivos
Monitoreo de jobs
Monitoreo de jobs
Jobs en ejecución
Jobs finalizados
sacct
Carpeta /local
Software
Ejemplos
Jobs en ejecución
Jobs finalizados
sacct
Monitoreo de jobs
Recomendación General
Asegúrese de reservar la cantidad de RAM y CPUs necesarios para la ejecución de su job. No reserve recursos que no necesita, ya que de hacerlo, perjudicará la ejecución de los demás usuarios del cluster.
A continuación se muestran algunos ejemplos de como medir el uso de CPU y RAM de su job a fin de que pueda refinar la reserva de recursos.
Jobs en ejecución
Si su job se encuentra en ejecución, usted puede revisar su uso actual de recursos. Sin embargo, deberá esperar hasta su finalización para ver el uso máximo de recursos durante toda su ejecución.
La manera más sencilla de revisar el uso instantáneo de recursos es hacer crear un job interactivo en el nodo de computación donde su job se encuentra ejecutándose. Para saber en que nodo debe crear el job interactivo, ejecute:
squeue --me
El cual nos da como salida:
JOBID PARTITION     NAME     USER  ST       TIME  NODES NODELIST(REASON)
21615 standard    bert-sar juan   PD       0:00      1 n003
En ella podemos notar que su job bert-sar se encuentra ejecutandose en el nodo n003 de la parición standard. Con esa información crearemos el job interactivo.
srun --pty -t 02:00 --mem=1G -p standard --nodelist=n003 bash
Una vez dentro del nodo de cómputo, ejecutaremos ps o htop.
ps le brindará la información instantánea del uso de recursos cada vez que ejecute el comando.
[alan.turing@n004 ~]$ ps -u$USER -o %cpu,rss,args
%CPU   RSS COMMAND
0.0  2376 python triangle.py
0.0  2380 python triangle.py
0.0  2380 python triangle.py
0.0  2380 python triangle.py
0.0  2380 python triangle.py
0.0  2380 python triangle.py
0.0  2380 python triangle.py
0.0  2380 python triangle.py
0.0  2380 python triangle.py
El reporte de memoria de ps se muestra en KB, podemos notar que los procesos listados consumen alrededor de 2000 KB de RAM y que el uso de los CPUs es casi nulo.
htop se ejecuta de manera interactiva y muestra las estadísticas de uso en vivo. Puede presionar la tecla u, ingresar su nombre de usuario y luego enter para filtrar solo sus procesos. La información del uso de memoria, se encuentra en la columna RES. Para solicitar ayuda puede presionar ? y si desea salir q .
Jobs finalizados
Slurm guarda las estadísticas de cada job, incluído cuanta memoria y CPU fue utilizada.
sacct
También se puede usar sacct para obtener la información del job. Lamentablemente, el output por defecto de sacct no es del todo entendible, por ello se recomienda procesar la salida de la siguiente manera.
[alan.turing@khipu ~]$ export SACCT_FORMAT="JobID%20,JobName,User,Partition,NodeList,Elapsed,State,ExitCode,MaxRSS,AllocTRES%32"
[alan.turing@khipu ~]$ sacct -j 21886
JobID    JobName      User  Partition        NodeList    Elapsed      State ExitCode     MaxRSS                        AllocTRES
---------- ---------- --------- ---------- --------------- ---------- ---------- -------- ---------- --------------------------------
1063 simple_ex+   alan.tur+      debug            n005   00:00:11  COMPLETED      0:0             billing=2,cpu=2,mem=200M,node=1
1063.batch      batch                                 n005   00:00:11  COMPLETED      0:0                       cpu=2,mem=200M,node=1

---

## Carpeta /local

Fuente: https://docs.khipu.utec.edu.pe/guia-de-usuario/enviar-jobs/local/

Carpeta `/local`
Enviar jobs
Enviar jobs
Comandos Básicos
Particiones
Nodos
Opciones de Slurm
Jobs interactivos
Monitoreo de jobs
Carpeta /local
Carpeta /local
Cómo utilizar /local
Software
Ejemplos
Cómo utilizar /local
Carpeta /local
Cada nodo de cómputo en Khipu cuenta con almacenamiento local (discos) que se encuentra configurado para montarse en la carpeta /local. Esta carpeta tiene los mismos permisos que una carpeta /tmp, y su función es la de un almacenamiento temporal para tareas que requieran escribir sobre archivos.
Cómo utilizar /local
Los nodos de cómputo tienen acceso a la carpeta /home a través de NFS. Esto quiere decir que cualquier tarea en ejecución tendrá acceso a nuestra carpeta personal. Sin embargo, el acceso constante de una tarea a la carpeta /home no es deseable porque las lecturas y escrituras tienen un costo adicional de comunicación por red, que puede además saturar el ancho de banda.
Como alternativa, previo a la creación de una tarea un usuario puede crear una carpeta temporal en /local, donde su job realizará las lecturas y escrituras que necesita, sin necesidad de comunicarse por red para acceder a la carpeta /home. El siguiente script muestra el escenario descrito:
#!/bin/bash
#SBATCH --job-name=test
#SBATCH -p standard
#SBATCH --output=test_%j.out
#SBATCH --error=test_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=01:00:00
# Crear el directorio de trabajo en nodo de cómputo
mkdir -p /local/nombre.apellido/$SLURM_JOB_ID
# Copiar contenido necesario para la ejecución y moverse a la carpeta /local
cp -rp /home/mpintol/Documents/mt-test/* /local/nombre.apellido/$SLURM_JOB_ID
cd /local/nombre.apellido/$SLURM_JOB_ID
## Ejecutar el programa
srun ./test
Podemos observar que la carpeta /local/nombre.apellido/$SLURM_JOB_ID fue creada y contiene los archivos utilizados durante la ejecución de la tarea:
[nombre.apellido@n003 local]$ pwd
/local
[nombre.apelido@n003 local]$ ls -R nombre.apellido/
nombre.apellido/:
42641
nombre.apellido/42641:
test  test_42641.err  test_42641.out  test.sh
La carpeta raiz /local es compartida
Asegurarse de siempre crear una carpeta personal dentro de /local para manejar sus archivos. La carpeta /local es de por sí compartida y si se crean archivos directamente en esta ubicación, cualquier usuario podría modificarlos o eliminarlos

---

