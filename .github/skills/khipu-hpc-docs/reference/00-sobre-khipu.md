## Sobre Khipu

Fuente: https://docs.khipu.utec.edu.pe/info/

Infraestructura
Políticas de uso
Tipos de cuentas
¿Cuanto cuesta acceder a Khipu?
Agradecimiento / citación
Khipu es un cluster de Computación de Alto Desempeño (HPC en inglés) que forma parte del Centro de Investigación para la Computación Sostenible (COMPSUST) de la Universidad de Ingeniería y Tecnología (UTEC). En él es posible realizar ejecuciones que requieran gran poder de cómputo ya sea en CPU o GPU.
¿Cuanto cuesta acceder a Khipu?
Khipu es gratuito para todos los miembros de la comunidad de UTEC y sus proyectos asociados que requieran de recursos computacionales para sus labores de investigación. Cualquier miembro de UTEC puede solicitar su acceso a Khipu a travez del formulario de registro que se encuentra en el portal web. Una vez su solicitud haya sido revisada, le serán enviadas sus credenciales de acceso al correo registrado en el formulario.
Info
Por el momento no se dispone de acceso para personas sin afiliación a UTEC.
Agradecimiento / citación
Alentamos a todos a los usuarios cuyo proyecto culmine en una publicación a añadir al cluster Khipu dentro de los agradecimientos. Puede añadir un mensaje de agradecimiento como el siguiente:
“El trabajo computacional del presente proyecto fue apoyado por los recursos del cluster HPC Khipu (https://web.khipu.utec.edu.pe/) de la Universidad de Ingeniería y Tecnología (UTEC)"
Si en caso necesita ayuda o requiere mayor información sobre Khipu, por favor escribir al correo  khipu@utec.edu.pe. Si ya posee sus credenciales, por favor genere un ticket a través del portal de  mesa de ayuda.

---

## Infraestructura

Fuente: https://docs.khipu.utec.edu.pe/info/infraestructura/

Infraestructura
Infraestructura
Infraestructura
Nodo de acceso
Nodos CPU
n003
n004
n005
n006
Nodos GPU
g001
g002
ag001
Nodos Ciencia de Datos
ds001
Software del sistema
Políticas de uso
Tipos de cuentas
Nodo de acceso
Nodos CPU
n003
n004
n005
n006
Nodos GPU
g001
g002
ag001
Nodos Ciencia de Datos
ds001
Software del sistema
Infraestructura
Nodo de acceso
Es el nodo mediante el cual se accede al cluster. Es usado principalmente para compilar, enviar y monitorear los jobs.
Especificaciones
Nombre
khipu
Procesador
Intel(R) Xeon(R) Gold 6230 CPU @ 2.10 GHz 20 cores por socket, 40 por nodo.
Memoria
DRAM DDR4-1333 MHz, 128 GB por nodo
Almacenamiento
1TB SSD, 40 TB HDD
Red
Infiniband FDR MT4119
Nodos CPU
Usados para procesamiento de jobs que requieren de CPU y RAM. Es gerenciado automáticamente por Slurm.
n003
Especificaciones
Nombre
n003
Procesador
Intel(R) Xeon(R) Gold 6130 CPU @2.10 GHz 16 cores por socket, 32 por nodo.
Memoria
224 GB DRAM DDR4-1333 MHz
Red
Infiniband FDR MT4119
n004
Especificaciones
Nombre
n004
Procesador
Intel(R) Xeon(R) Gold 6130 CPU @2.10 GHz 16 cores por socket, 32 por nodo.
Memoria
224 GB DRAM DDR4-1333 MHz
Red
Infiniband FDR MT4119
n005
Especificaciones
Nombre
n005
Procesador
Intel(R) Xeon(R) Gold 6130 CPU @2.10 GHz 16 cores por socket, 32 por nodo.
Memoria
224 GB DRAM DDR4-1333 MHz
Red
Infiniband FDR MT4119
n006
Especificaciones
Nombre
n006
Procesador
Intel(R) Xeon(R) Gold 5418Y 2.0 GHz 24 cores por socket, 48 por nodo.
Memoria
1TB DRAM DDR5 5600MHz
Red
Infiniband Mellanox MT28908
Nodos GPU
Usados para procesamiento de jobs que requieren de CPU, RAM y/o GPU. Es gerenciado automáticamente por Slurm.
g001
Especificaciones
Nombre
g001
Procesador
Intel(R) Xeon(R) Gold 6230 CPU @2.10 GHz 16 cores por socket, 32 por nodo.
Gráficos
NVIDIA Tesla T4 16 GB GDDR6
Memoria
192 GB DRAM DDR4-1333 MHz
Red
Infiniband FDR MT4119
g002
Especificaciones
Nombre
g002
Procesador
Intel(R) Xeon(R) Gold 5418Y 2.0 GHz 24 cores por socket, 48 por nodo.
Gráficos
NVIDIA RTX A6000 48 GB GDDR6
Memoria
1TB DRAM DDR5 5600MHz
Red
Infiniband Mellanox MT28908
ag001
Especificaciones
Nombre
ag001
Procesador
AMD EPYC 7742 64-Core Processor 64 cores por socket, 128 por nodo.
Gráficos
x2 NVIDIA A100 40 GB GDDR6
Memoria
1TB DRAM DDR4
Red
Infiniband Mellanox MT28908
Nodos Ciencia de Datos
ds001
Especificaciones
Nombre
ds001
Procesador
Intel(R) Xeon(R) Gold 5418Y 2.0 GHz 24 cores por socket, 48 por nodo.
Gráficos
NVIDIA RTX A6000 48 GB GDDR6
Memoria
1TB DRAM DDR5 5600MHz
Red
Infiniband Mellanox MT28908
Software del sistema
Sistema Operativo: Rocky Linux 8.10 (Green Obsidian)
Message Passing Library: MPICH
Compiladores: Intel, GCC, CUDA 12.8
Job Scheduler: SLURM 25.11
Manejo de software: Módulos de ambiente

---

## Politicas de uso

Fuente: https://docs.khipu.utec.edu.pe/info/politicas-de-uso/

Políticas de uso
Infraestructura
Políticas de uso
Políticas de uso
Sobre las cuentas
Sobre el uso
Incumplimiento de las reglas de uso
Agradecimientos por el uso de Khipu
Comunicación
Tipos de cuentas
Sobre las cuentas
Sobre el uso
Incumplimiento de las reglas de uso
Agradecimientos por el uso de Khipu
Comunicación
Políticas de uso
El uso del cluster HPC Khipu está sujeto al cumplimiento de sus políticas de uso. Los usuario se comprometen a cumplir con cada una de ellas una vez que reciben sus credenciales de acceso.
Sobre las cuentas
Solo los usuarios registrados pueden acceder a Khipu. Asimismo, los usuarios se hacen responsables de tomar las precauciones necesarias para proteger sus credenciales de acceso y así impedir accesos no autorizados.
Los usuarios se encuentran prohibidos de compartir sus credenciales con otras personas, así sean estos estudiantes o colaboradores. Del mismo modo, los usuarios se encuentran prohibidos de acceder a Khipu con credenciales que no son suyas, con o sin consentimiento del usuario.
En caso de existir sospecha que otros han usado su cuenta, notificarlo inmediatamente a khipu@utec.edu.pe
Las cuentas serán desactivadas si una de las siguientes condiciones se cumple:
La fecha de fin del curso o proyecto ha sido alcanzada.
El encargado del curso o proyecto indica que el usuario ya no requiere acceso.
El usuario ha recibido alguna sanción disciplinaria de parte de la universidad.
Si una cuenta se encuentra desactivada por más de 30 días, será eliminada permanentemente.
Sobre el uso
El cluster Khipu es un recurso compartido por multiples usuarios, así que las acciones que usted realice pueden afectar a otros usuarios si no se realizan de manera adecuada. Es por ello, que se brindan las siguientes recomendaciones a fin de garantizar un uso equitativo y justo de los recursos del cluster.
El uso del cluster se encuentra restringido solo para fines educativos y de investigación. Su uso no debe estar relacionado a actividades comerciales, de consultoría o creación y/o ejecución de software malicioso.
Los usuarios son responsables de usar los recursos del cluster de manera eficiente, efectiva, ética y lícita.
El nodo de acceso es usado para acceder al cluster, editar archivos, compilar código y enviar trabajos. De ninguna manera, se deben ejecutar los trabajos directamente en el nodo de acceso.
Toda ejecución de trabajos debe ser realizada a traves del gestor de colas Slurm. Es así como se garantizan un uso eficiente y justo de los recursos.
El cluster no debe ser utilizado como almacenamiento personal. Se recomienda copiar sus resultados a su máquina personal de manera periódica. Khipu no cuenta con backups de sus discos.
Los usuarios no deben intentar acceder a cualquier archivo o programa al cual no poseen autorización o un consentimiento explícito del dueño del archivo o programa.
Los usuarios pueden hacer uso de las aplicaciones ya instaladas, y también compilar nuevas aplicaciones en su espacio personal solamente si fueran necesarios para el desarrollo de su proyecto o trabajo.
Los softwares que se instalen deben incluir una licencia válida (si es aplicable). No se puede instalar software de procedencia ilegal y/o con licencia no otorgada por los desarrolladores.
La presente política será revisada y actualizada de manera periódica. Cualquier cambio será comunicado al correo electrónico registrado.
Incumplimiento de las reglas de uso
El usuario acepta cumplir con la normativa y sanciones impuestas por UTEC en sus atribuciones.
- En caso de no cumplir normas de UTEC y/o atentar contra la ley, el evento será notificado a las autoridades pertinentes.
- En caso de incumplimiento de los items anteriores, la cuenta será suspendida.
Agradecimientos por el uso de Khipu
Alentamos a todos a los usuarios, cuyo proyecto termina en una publicación o presentación, a añadir al cluster Khipu dentro de los agradecimientos. Su sola mención contribuye a comunicar el rol de Khipu en el desarrollo de investigaciones dentro de la universidad, a incentivar a más estudiantes y docentes a incorporar a Khipu dentro de sus proyectos o planes de estudio, a mantener el financiamiento y soporte que hace posible que Khipu siga creciendo cada día más.
Puede añadir un mensaje de agradecimiento como el siguiente:
"El trabajo computacional del presente proyecto fue apoyado por los recursos del cluster HPC Khipu de la Universidad de Ingeniería y Tecnología (UTEC) "
Comunicación
El correo electrónico ingresado al momento de solicitar acceso a Khipu será el medio por el cual se enviarán anuncios relevantes al funcionamiento del cluster. Si usted presenta preguntas, pedidos o requiere asistencia puede escribir de manera directa a khipu@utec.edu.pe.

---

## Grupos / tipos de cuentas

Fuente: https://docs.khipu.utec.edu.pe/info/tipos-de-cuentas/

Tipos de cuentas
Infraestructura
Políticas de uso
Tipos de cuentas
Tipos de cuentas
Grupo Educación
Pregrado
Posgrado
Docencia
Grupo Investigación
Tesis
Investigación Nivel I
Investigación Nivel II
¿Cómo puedo saber mi tipo de cuenta?
Grupo Educación
Pregrado
Posgrado
Docencia
Grupo Investigación
Tesis
Investigación Nivel I
Investigación Nivel II
¿Cómo puedo saber mi tipo de cuenta?
Tipos de cuentas
Existen diferentes grupos de usuarios que son gerenciados de manera automática por Slurm. De manera general podemos agruparlos en: educación e investigación.
Grupo Educación
Permite el uso del cluster por los estudiantes de pregrado o posgrado, a pedido de un instructor(a) registrado(a), en el marco del desarrollo de un curso. De acuerdo al tipo de estudiantes (pregrado o posgrado) se disponen los siguiente límites:
Pregrado
Particiones disponibles: debug, debug-gpu, standard, gpu
Cantidad máxima de recursos por usuario: 32 cores, 98GB RAM y 8 shards GPU
Tiempo máximo de ejecución por job (Walltime): 8 horas
Posgrado
Particiones disponibles: debug, debug-gpu, standard, gpu
Cantidad máxima de recursos por usuario: 32 cores, 98GB RAM y 8 shards GPU
Tiempo máximo de ejecución por job (Walltime): 8 horas
Docencia
Particiones disponibles: debug, debug-gpu, standard, gpu
Cantidad máxima de recursos por usuario: 32 cores, 98GB RAM y 32 shards GPU
Tiempo máximo de ejecución por job (Walltime): 8 horas
Grupo Investigación
Permite el uso del cluster para todos aquellos miembros de UTEC y asociados que requieran de recursos computacionales para el desarrollo de un proyecto de investigación. La solicitud de acceso es registrada por el investigador principal (PI). De acuerdo al proyecto se disponen los siguiente niveles y límites por nivel:
Tesis
Particiones disponibles: debug, debug-gpu, standard, gpu, big-mem
Cantidad máxima de recursos por usuario: 32 cores, 98GB RAM y 40 shards GPU
Tiempo máximo de ejecución por job (Walltime): 24 horas
Investigación Nivel I
Particiones disponibles: debug, debug-gpu, standard, gpu, big-mem
Cantidad máxima de recursos por usuario: 48 cores, 120GB RAM y 1 GPU o 40 shards GPU
Tiempo máximo de ejecución por job (Walltime): 72 horas
Investigación Nivel II
Particiones disponibles: debug, debug-gpu, standard, gpu, big-mem
Cantidad máxima de recursos por usuario: 96 cores, 162GB RAM y 2 GPU o 80 shards GPU
Tiempo máximo de ejecución por job (Walltime): 96 horas
¿Cómo puedo saber mi tipo de cuenta?
Una vez inicies sesión en Khipu, ejecuta el siguiente comando:
myaccount
Y obtendrás el nombre de tu cuenta y sus límites. La salida en pantalla será similar a:
$ myaccount
---------------------------------------------------------
Khipu account
---------------------------------------------------------
User                 Account            Default
-------------------- ------------------ -----------------
aturin               docencia           docencia
--------------------------------------------------------------
Account Limits
--------------------------------------------------------------
Account           Resources                       TimeLimit
----------------- ------------------------------- ------------
a-docencia        cpu=32,gres/shard=32,mem=98G      08:00:00

---

