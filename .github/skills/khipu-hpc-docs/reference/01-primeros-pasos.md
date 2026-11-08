## Primeros pasos (overview)

Fuente: https://docs.khipu.utec.edu.pe/primeros-pasos/

Empezar a usar Khipu
Solicitar acceso
Acceder a Khipu
Cambiar contraseña
Configurar llaves SSH
Transferir archivos
Siguientes pasos
Empezar a usar Khipu
Para empezar a usar Khipu es necesario seguir los siguientes pasos:
Solicitar una cuenta de usuario y esperar el envío de sus credenciales.
Acceder a Khipu con un cliente SSH y cambiar su contraseña (Opcional).
Configurar un par de llaves SSH (Opcional si desea acceder sin escribir su contraseña).
Si fuera necesario, transferir sus archivos a Khipu.
Revisar la demás guías de uso de Khipu.
¿Necesita ayuda?
Si en caso necesita ayuda o requiere mayor información para realizar el primer paso, por favor escribir al correo  khipu@utec.edu.pe. Si ya posee sus credenciales y tiene problemas del segundo paso en adelante, por favor genere un ticket a través del portal de  mesa de ayuda.

---

## Solicitar acceso

Fuente: https://docs.khipu.utec.edu.pe/primeros-pasos/solicitar-acceso/

Solicitar acceso
Solicitar acceso
Acceder a Khipu
Cambiar contraseña
Configurar llaves SSH
Transferir archivos
Siguientes pasos
Solicitar acceso a Khipu
Para poder acceder a Khipu, es necesario formar parte de UTEC o de un proyecto en conjunto con UTEC.
El acceso puede darse a través de proyectos (para su uso en investigación) o cursos (para su uso académico).
Si desea solicitar acceso para su  proyecto, el investigador principal (PI) debe completar el siguiente formulario.
Si el proyecto es una  tesis de pregrado o posgrado, el alumno responsable de la tesis en conjunto con su asesor deberá completar el siguiente formulario.
Si desea solicitar acceso a Khipu para su  curso, el profesor responsable (PR) del dictado del curso debe completar el siguiente formulario.
Una vez completado el formulario respectivo, la solicitud de acceso será revisada y la respuesta comunicada al correo electrónico registrado.
Si la solicitud es favorable, se comunicará la respuesta y se realizará el envío de credenciales de acceso a los correos electrónicos de cada miembro registrado. Una vez que un usuario recibe sus credenciales, se compromete a cumplir con las políticas de uso.
Si la solicitud no es favorable o se requiere mayor información, la comunicación se realizará por correo electrónico.

---

## Acceder a Khipu (SSH)

Fuente: https://docs.khipu.utec.edu.pe/primeros-pasos/acceder-a-khipu/

Acceder a Khipu
Solicitar acceso
Acceder a Khipu
Acceder a Khipu
Inicio de sesión
Problemas frequentes
1. Timeouts
2. Fallas de autenticación
Cambiar contraseña
Configurar llaves SSH
Transferir archivos
Siguientes pasos
Inicio de sesión
Problemas frequentes
1. Timeouts
2. Fallas de autenticación
Acceder a Khipu
Nota
Para los siguientes comandos necesita tener una cuenta activa en Khipu.
El acceso a Khipu se realiza a través de la  interfaz de comandos o terminal que se encuentra disponible en la mayoría de sistemas operativos. Para ello se hace uso de un cliente SSH. En  Windows, tenemos clientes como cmd, powershell o Putty. Mientras que en  Linux y  MacOS ya incluyen una terminal que viene por defecto.
Inicio de sesión
Abra una terminal y ejecute el siguiente comando. No olvide reemplazar  por su nombre de usuario.
ssh <username>@khipu.utec.edu.pe
Host keys
Si es la primera vez que accede a Khipu le aparecerá un mensaje similar al siguiente:
The authenticity of host 'khipu.utec.edu.pe' can't be established.
ED25519 key fingerprint is SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.
Are you sure you want to continue connecting (yes/no)?
Ese mensaje de advertencia es normal y aparece la primera vez que su cliente SSH se conecta a un ordenador nuevo.  Escriba yes y presione Enter para que se le solicite su contraseña de acceso.
Escriba su contraseña y presione Enter . Una vez hecho esto, usted habrá iniciado sesión en el cluster y tendrá el siguiente mensaje:
Last login: Mon Nov  4 17:30:01 2024 from *.*.*.*
--*-*- Sustainable Computing Research Center -*-*--
_  ___     _
| |/ / |   (_)
| ' /| |__  _ _ __  _   _
|  < | '_ \| | '_ \| | | |
| . \| | | | | |_) | |_| |
|_|\_\_| |_|_| .__/ \__,_| v3.0
| |
|_|
===========================================================================
This system is for authorized users only and users must comply with all
Khipu computing, network and research policies. All activity may be
recorded for security and monitoring purposes.
===========================================================================
Docs          https://docs.khipu.utec.edu.pe
Support       khipu@utec.edu.pe
===================[ Maintenance Information ]============================
No maintenance information.
===========================================================================
Good evening <username>!
Warning
Ingresar su contraseña de manera incorrecta en un periodo corto de tiempo provocará que el acceso a Khipu desde su IP pública sea bloqueado.
¡Felicidades , ya se encuentra dentro de Khipu!
¡Opcional! Revise la siguiente guía si desea acceder a Khipu usando llaves SSH.
Problemas frequentes
1. Timeouts
Si usted obtiene un mensaje de error parecido al siguiente:
ssh: connect to host khipu.utec.edu.pe port 22: Operation timed out
Pruebe connectarse a una conección de internet más estable como una red cableada o cambie de red WiFi. Si el error ocurre dentro del campus o se encuentra fuera de Perú, por favor genere un ticket en  mesa de ayuda.
2. Fallas de autenticación
ssh: connect to host khipu.utec.edu.pe port 22: Connection refused
Como medida para prevenir ataque de fuerza bruta, Khipu cuenta con un bloqueo automatizado de las IPs desde las cuales se realizan inicios fallidos de sesión en  un periodo corto de tiempo.  Si usted ingresa su contraseña de manera incorrecta más de tres veces seguidas, provocará que el acceso a Khipu desde su IP pública sea bloqueado y le aparecerá un mensaje como el de arriba. Para restablecer su contraseña o desbloquear el acceso desde su IP pública, debe generar un ticket en  mesa de ayuda.

---

## Cambiar contrasena

Fuente: https://docs.khipu.utec.edu.pe/primeros-pasos/cambiar-contrasena/

Cambiar contraseña
Solicitar acceso
Acceder a Khipu
Cambiar contraseña
Cambiar contraseña
Recomendaciones de seguridad
Configurar llaves SSH
Transferir archivos
Siguientes pasos
Recomendaciones de seguridad
Cambio de contraseña
Olvido de contraseña
Si usted olvidó su contraseña, genere un ticket en  mesa de ayuda para que se le genere una nueva contraseña. Esta guía es para cambiar su contraseña si conoce la anterior.
Usted puede cambiar la contraseña que recibió en el correo de bienvenida a Khipu.  A continuación le mostraremos como hacerlo.
Inicie sesión en Khipu. Si no sabe como hacerlo, revise el siguiente enlace.
Luego ejecute el comando passwd y siga lo que se le indica en pantalla.
Se le pedirá que escriba su contraseña actual.
Se le pedirá que escriba la nueva contraseña
Se le pedirá que repita la nueva contraseña
Listo, ya cambió su contraseña en Khipu.
Recomendaciones de seguridad
Warning
Recuerde proteger sus credenciales de acceso y no compartirlas con ningún otra persona. El uso inadecuado de los servicios del cluster es resposabilidad del titular de la cuenta.
Generar contraseñas fuertes y seguras es fundamental para garantizar su seguridad y la del cluster. Para ello le compartimos las siguientes recomendaciones.
Utilice un mínimo de 12 caracteres
Combine diferentes tipos de caracteres como números, letras o caracteres especiales.
No use palabras comunes o fáciles de adivinar.
No use información personal predecible.

---

## Configurar llaves SSH

Fuente: https://docs.khipu.utec.edu.pe/primeros-pasos/configurar-llaves-ssh/

Configurar llaves SSH
Solicitar acceso
Acceder a Khipu
Cambiar contraseña
Configurar llaves SSH
Configurar llaves SSH
Generación de llaves SSH
Copiar su llave pública a Khipu
Transferir archivos
Siguientes pasos
Generación de llaves SSH
Copiar su llave pública a Khipu
Configurar llaves SSH
Es posible acceder a Khipu usando un par de llaves SSH. La llave pública deberá copiarla a Khipu, mientras que la privada debe permanecer en su ordenador.
Generación de llaves SSH
Desde una terminal ( Linux,   MacOS o  Windows)
El par de llaves SSH puede ser generado usando  Linux,   MacOS o  Windows. Para ello abra una terminal en su computadora local y ejecute el siguiente comando:
ssh-keygen -t ed25519
Su terminal responderá preguntando por un nombre y lugar donde guardar el par de llaves. Si desea optar por la opción por defecto, presione Enter. Si desea un nombre y lugar distino escríbalo en pantalla. Tambien puede especificar el lugar y nombre de manera directa añadiendo el flag -f <filename> al comando  anterior. A continuación se muestra un ejemplo del comando completo:
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
Luego se le pedirá que ingrese un passphrase . Este debe tener una longitud de por lo menos 8 caracteres (preferiblemente 12). El passphrase debe ser preferiblemente una combinación de números, letras y caracteres especiales para tener mayor seguridad. Una vez escrito, presione Enter para continuar.
Olvido de passphrase
Si usted olvida su passphrase, no podrá recuperarlo. En cambio, usted deberá eliminar el par de llaves anterior y generar una nuevas.
Finalmente se generarán un par de llaves SSH en la locación que especificó (~/.ssh/ en el ejemplo anterior). El par de llaves incluye una llave privada id_ed25519 y una pública id_ed25519.pub.
Advertencia
La llave privada no debe ser compartida con nadie, incluyendo Khipu. Esta llave debe permanecer almacenada en el ordenador donde fue generada. La llave pública es la única que será compartida y almacenada en el cluster. Utilice un passphare robusto para proteger sus llaves en caso de robo y prevenir un uso no autorizado de las mismas.
Copiar su llave pública a Khipu
A continuación se muestra como copiar su clave pública a Khipu desde diferentes sistemas operativos:
Desde una terminal ( Linux y    MacOS) Windows
Ejecute desde su terminal ssh-copy-id -i <ubicación-de-la-llave-pública> <usuario-en-khipu>@khipu.utec.edu.pe. Por ejemplo, para las llaves generadas en los pasos anteriores el comando a ejecutar será:
ssh-copy-id -i ~/.ssh/id_ed25519.pub <usuario-en-khipu>@khipu.utec.edu.pe
Si el par de llaves del ejemplo anterior hubieran sido generadas en  Windows,  el comando a usar será:
type ~/.ssh/id_ed25519.pub | ssh <usuario-en-khipu>@khipu.utec.edu.pe "mkdir -p .ssh && cat >> .ssh/authorized_keys"
También, puede optar por copiar el contenido de la llave pública id_ed25519.pub y escribirlo en Khipu en .ssh/authorized_keys usando un editor de texto como vim o nano.
Info
Una vez que su llave pública fue copiada en Khipu correctamente, usted podrá acceder a Khipu usando sus llaves SSH. A diferencia del inicio de sesión con contraseña, el passphrase le será solicitado una sola vez por inicio de sesión de su ordenador local.

---

## Transferir archivos

Fuente: https://docs.khipu.utec.edu.pe/primeros-pasos/transferir-archivos/

Transferir archivos
Solicitar acceso
Acceder a Khipu
Cambiar contraseña
Configurar llaves SSH
Transferir archivos
Transferir archivos
Copiando archivos usando scp
Copiando archivos usando rsync
Siguientes pasos
Copiando archivos usando scp
Copiando archivos usando rsync
Transferir archivos hacia/desde Khipu
Info
Se recomienda realizar regularmente copias de sus archivos en Khipu a sus ordenadores locales. Es importante recordar que Khipu no es un  almacenamiento personal en la nube y que la información almacenada no posee respaldo.
La transferencia de archivos hacia/desde Khipu puede ser realizada usando scp o rsync.
Copiando archivos usando scp
Secure Copy Protocol scp
scp es un comando que permite copiar de manera secura archivos y directorios desde dos ubicaciones remotas. Con este comando podremos copiar archivos o directorios desde nuestro ordenador local a uno remoto y viceversa. Cuando se transfiere datos mediante scp los archivos y contraseñas son encriptados para evitar que alguien tenga acceso no autorizado mientras se realiza el proceso de copia.
La sintaxis básica del comando scp es la siguiente:
scp <path-origen> <path-destino>
A continuación se muestran algunos ejemplos:
Copiar desde mi ordenador local a Khipu
# Copiar `mi-archivo.txt` al directorio `/home/<usuario-en-khipu>` (`~`) en Khipu
scp mi-archivo.txt <usuario-en-khipu>@khipu.utec.edu.pe:~
# Copiar `mi-folder/` al directorio `/home/<usuario-en-khipu>` (`~`) en Khipu
# El flag -r indica que se esta ejecutando el comando de manera recursiva.
scp -r mi-folder/ <usuario-en-khipu>@khipu.utec.edu.pe:~
Copiar de Khipu a mi ordenador local
# Copiar `mi-archivo-en-khipu.txt` al directorio actual de mi ordenador
scp mi-usuario@khipu.utec.edu.pe:~/path/a/mi-archivo-en-khipu.txt .
# Copiar `mi-folder-en-khipu/` al directorio actual de mi ordenador
scp -r mi-usuario@khipu.utec.edu.pe:~/path/a/mi-folder-en-khipu/ .
Copiando archivos usando rsync
Remote Synchronization rsync
rsync es una herramienta de sincronización entre archivos remotos y locales. Este comando minimiza la cantidad de datos copiados, ya que solo copia aquellas partes que cambiaron entre ambos directorios. Este comando es recomendado para la transferencia de archivos de gran tamaño ya que mantiene un registro del progreso. De esta manera, si la transmisión es interrumpida, rsync continuará desde donde se quedó, sin necesidad de iniciar desde cero.
La sintaxis básica para el uso de rsync es la siguiente:
rsync <opciones> <path-origen> <path-destino>
rsync <opciones> <path-origen-local> <usuario-en-khipu>@khipu.utec.edu.pe:<path-destino-en-Khipu>
rsync <opciones> <usuario-en-khipu>@khipu.utec.edu.pe:<path-origen-en-Khipu> <path-destino-local>
A continuación se muestran algunos ejemplos del uso de rsync.
Sincronizar desde mi ordenador local a Khipu
# El flag -a indica que se trata de archivos
rsync -a ~/path/en/mi-folder <usuario-en-khipu>@khipu.utec.edu.pe:~/path/en/khipu
# El flag -az indica que se trata de archivos que se van a comprimir
rsync -az ~/path/en/mi-folder <usuario-en-khipu>@khipu.utec.edu.pe:~/path/en/khipu
Sincronizar un directorio remoto a uno local
# El flag -a indica que se trata de archivos
rsync -a <usuario-en-khipu>@khipu.utec.edu.pe:~/path/en/khipu ~/path/en/mi-folder-local
# El flag -azP indica que se trata de archivos que se van a comprimir y se muestra el progreso
rsync -azP <usuario-en-khipu>@khipu.utec.edu.pe:~/path/en/khipu ~/path/en/mi-folder-local

---

## Siguientes pasos

Fuente: https://docs.khipu.utec.edu.pe/primeros-pasos/siguientes-pasos/

Siguientes pasos
Solicitar acceso
Acceder a Khipu
Cambiar contraseña
Configurar llaves SSH
Transferir archivos
Siguientes pasos
Siguientes pasos
Por favor revise los siguientes enlaces:
Información sobre la infraestructura disponible.
Políticas de uso
¿Como enviar jobs?
Software disponible
¿Cómo solicitar ayuda?

---

