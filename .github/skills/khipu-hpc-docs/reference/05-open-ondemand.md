## Open OnDemand (overview)

Fuente: https://docs.khipu.utec.edu.pe/ondemand/

Shell Interactiva
Desktop Gráfico
Gestor de Tareas
Jupyter Lab
¿Cómo ingresar?
Servicios Disponibles
Open Ondemand es un servicio web que permite el acceso a ambientes de HPC desde cualquier lugar a través de un navegador. No sólo provee un nuevo método de acceso sino que utiliza interfaces gráficas intuitivas para la gestión de tareas y permite la integración de una gran cantidad de aplicaciones interactivas como Jupyter, COMSOL y Matlab.
Desde diciembre del 2025, Khipu cuenta con su propio servidor de Open Ondemand. Esto permite a los usuarios interactuar con el Cluster a través de sus navegadores, y ya no exclusivamente a través de SSH.
¿Cómo ingresar?
Enlace de Login: ood.khipu.utec.edu.pe
Los usuarios de Khipu pueden acceder a los servicios de Open Ondemand a través del formulario de login ingresando sus credenciales de acceso a Khipu (las mismas que utiliza para conexiones por ssh).
Antes de acceder
Antes de poder acceder por la web, es necesario ingresar al menos una vez por ssh, ejecutando el comando ssh <mi-usuario>@khipu.utec.edu.pe e ingresando su contraseña. Esto sucede porque Khipu crea la carpeta de cada usuario en /home cuando este accede por primera vez a través de ssh. Si intena ingresar por la web sin haber hecho esto previamente, obtendrá el mensaje "Home directory not found".
Servicios Disponibles
Gestor de Tareas
Aplicaciones Interactivas
Shell Interactiva
Desktop Gráfico
Jupyter Lab
Límites de Recursos
Cabe resaltar que los límites de recursos que se pueden reservar para las sesiones de aplicaciones interactivas son los mismos que aquellos impuestos por SLURM (ya que por debajo SLURM se encarga de crear los jobs). Esto quiere decir que si intento crear una sesión interactiva con más recursos de los que tengo asignados, mi sesión nunca se creará dado que se quedará encolada. Un usuario puede ver los recursos que tiene disponibles con el comando myaccount.

---

## OnDemand: Shell

Fuente: https://docs.khipu.utec.edu.pe/ondemand/shell/

Shell Interactiva
Shell Interactiva
Desktop Gráfico
Gestor de Tareas
Jupyter Lab
Shell Interactiva
Para acceder a la shell interactiva, el usuario debe ingresar al servicio de Open Ondemand con sus credenciales. Una vez en el panel principal, acceder a la opción Clusters > Khipuhpc Shell Access.
Open Ondemand permite acceder al Cluster a través de una terminal en la Web. Dado que este servicio utiliza el mismo servicio de autenticación que las conexiones al cluster por SSH, las sesiones se abren en nombre del usuario en la ubucación /home/<mi-usuario>.

---

## OnDemand: Desktop

Fuente: https://docs.khipu.utec.edu.pe/ondemand/desktop/

Desktop Gráfico
Shell Interactiva
Desktop Gráfico
Gestor de Tareas
Jupyter Lab
Desktop Gráfico
Servicio no disponible
Actualmente la plataforma permite crear sesiones interactivas de este servicio, sin embargo estas fallarán inmediatamente.

---

## OnDemand: Jobs

Fuente: https://docs.khipu.utec.edu.pe/ondemand/jobs/

Gestor de Tareas
Shell Interactiva
Desktop Gráfico
Gestor de Tareas
Gestor de Tareas
Tareas Activas
Compositor de Tareas
Jupyter Lab
Tareas Activas
Compositor de Tareas
Gestor de Tareas
Open Ondemand cuena con una interfaz de gestión de tareas que se comunica con el servidor de SLURM (gestor de colas) de Khipu. Podemos acceder a sus herramientas ingresando a la plataforma y, una vez en el panel principal, seleccionando el menú Jobs.
Tareas Activas
En la ventana "Active Jobs" podemos ver:
Nuestras tareas activas en un cluster
Todas las tareas activas en un cluster
Nuestras tareas activas en todos los clusters
Todas las tareas activas en todos los clusters
Podemos ver los detalles de cada una por separado, incluyendo quién la envió, en qué partición se encuentra, en qué nodos y cuántos recursos requiere. También podemos eliminar tareas en ejecución.
Compositor de Tareas
El compositor de tareas es una herramienta gráfica que facilita:
La creación de scripts de ejecución
El envío de tareas
El panel principal nos permite ejecutar tareas guardadas, modificar sus parámetros, crear plantillas, cargar scripts desde otras ubicaciones.

---

## OnDemand: Jupyter

Fuente: https://docs.khipu.utec.edu.pe/ondemand/jupyter/

Jupyter Lab
Shell Interactiva
Desktop Gráfico
Gestor de Tareas
Jupyter Lab
Jupyter Lab
Creación de Sesiones
Ambientes Virtuales
Ambientes virtuales globales
Ambientes virtuales personales
Utilizando venv + pip
Utilizando Miniconda
Creación de Sesiones
Ambientes Virtuales
Ambientes virtuales globales
Ambientes virtuales personales
Utilizando venv + pip
Utilizando Miniconda
Jupyter Lab
Khipu cuenta con instalaciones de Jupyter en todos sus nodos. Esto permite crear sesiones de Jupyter Lab interactivas en el navegador.
Creación de Sesiones
Para crear una sesión de Jupyter, el usuario debe ingresar a Open Ondemand con sus credenciales. Una vez en el panel principal, seleccionar la opción Interactive Apps > Jupyter Notebook.
La creación de sesiones de Jupyter funciona de manera similar a la creación de cualquier tarea en SLURM. Al crear una sesión de Jupyter, el usuario envía una tarea a la cola de ejecución de SLURM. Al igual que con otras tareas, debemos especificar parámetros para su ejecución. Los parámetros necesarios para crear una sesión de Jupyter son:
Partición
QOS (tipo de cuenta a utilizar)
Número de Horas
Número de CPUs (cores)
Cantidad de Memoria (GB)
Cantidad de Shards de GPU (sólo para particiones debug-gpu, gpu, all)
Espacio de Trabajo
Por defecto Jupyter siempre tomará el directorio /home/<mi-usuario> como espacio de trabajo. Esto quiere decir que cualquier trabajo realizado será persistente y se almacenará en dicha carpeta.
Ambientes Virtuales
Jupyter permite ejecutar notebooks con diferentes kernels. Una práctica común es utilizar ambientes virtuales (venv, conda) para separar los kernels y las dependencias de software que tienen instaladas. En nuestra instalación de Jupyter, los usuarios tienen acceso a ambientes virtuales globales (compartidos) y personales (privados).
Ambientes virtuales globales
Con el fin de proveer paquetes de software comúnmente utilizados para distintos tipos de aplicaciones (HPC, Data Science, IA, etc), Khipu cuenta con ambientes virtuales globales disponibles para todos los usuarios. En la siguiente tabla se presentan los ambientes globales disponibles con los paquetes de software que se encuentran instalados en cada uno:
Ambiente Virtual
Descripción
Paquetes de Software
General HPC
Herramientas básicas para uso general en HPC, Ciencia de datos, GPU e Inteligencia Artificial, gestionado con venv + pip
IPykernel v7.1.0, Numpy v2.3.5, Pandas v2.3.3, MatplotLib v3.10.8, Seaborn v0.13.2, Awkward v2.8.11, Dask v2025.12.0, CuPy (CUDA 12x) v13.6.0, Scipy v1.16.3, Scikit-Learn v1.8.0, Keras v3.12.0, PyTorch v2.9.1, TorchVision v0.24.1, TensorFlow v2.20.0
Conda General HPC
Herramientas básicas para uso general en HPC, Ciencia de datos, GPU e Inteligencia Artificial, gestionado con Miniconda
IPykernel v7.1.0, Numpy v2.3.5, Pandas v2.3.3, MatplotLib v3.10.8, Seaborn v0.13.2, Awkward v2.8.11, Dask v2025.12.0, CuPy (CUDA 12x) v13.6.0, Scipy v1.16.3, Scikit-Learn v1.8.0, Keras v3.12.0, PyTorch v2.9.1, TorchVision v0.24.1, TensorFlow v2.20.0
Ambientes virtuales personales
Los usuarios de Khipu son libres de instalar ambientes virtuales personales en sus entornos. De esta manera pueden instalar los paquetes de software que necesiten y utilizarlos en Jupyter.
Utilizando venv + pip
Los comandos para crear un ambiente virtual e instalar su kernel de Jupyter en su entorno utilizando venv + pip son los siguientes:
module load python3/3.13.2
python3 -m venv <my-env>
Importante
Antes de crear el ambiente, es necesario cargar el módulo python3/3.13.2 y es importante utilizar esta versión para crearlo, ya que este módulo carga la versión de Python específica que utiliza nuestra instalación de Jupyter. Si un usuario crea un ambiente virtual en base a otra versión de Python, es probable que el kernel aparezca como disponible en Jupyter Lab, pero que no pueda inicializarse correctamente.
Para instalar el kernel de un ambiente en el entorno del usuario y habilitar su uso en sesiones de Jupyter, es necesario ejecutar el siguiente comando:
source <path-to-my-env>/bin/activate
python -m ipykernel install --user --name <my-env> --display-name "Test Env"
Una vez instalado el kernel, este nos aparecerá como opción al seleccionar un kernel en las sesiones de Jupyter.
Instalación de paquetes de software
Una vez creado su ambiente, el usuario puede instalar paquetes de software utilizando pip. Una vez instalado el kernel en su entorno, este se encontrará disponible en Jupyter. El usuario puede instalar paquetes de software en su ambiente virtual antes o después de que instaló su kernel.
Para más información sobre el manejo de ambientes virtuales, ver: https://docs.python.org/3/library/venv.html
Utilizando Miniconda
Los comandos para crear un ambiente virtual e instalar su kernel de Jupyter en su entorno utilizando miniconda son los siguientes:
module load miniconda
conda create --name <my-env>
Similarmente debemos instalar el kernel y habilitar su uso en sesiones de Jupyter. Esto lo hacemos ejecutando:
conda activate <my-env>
conda install -y ipykernel
python3 -m ipykernel install --user --name <my-env> --display-name "Test Env"

---

