# Libreto completo del video · Cofrial SpA (Hito 2)

**Narran:** Benjamín (**B**) y Daniel (**D**). Duración: unos 22 minutos.

**Cómo leer este libreto:**
- **🖥 PANTALLA** dice qué tiene que estar a la vista y de qué tipo es.
- **🖱 HACER** es el clic o la tecla.
- **B:** y **D:** son las frases, en el orden en que se dicen. Se pueden decir con sus palabras, pero sin saltarse la idea.

### Los cuatro tipos de pantalla (para no confundirse)

Todas las pantallas internas tienen el mismo menú lateral y el mismo diseño, pero no son lo mismo:

| Etiqueta en este libreto | Menú lateral | Qué es | Dirección |
| --- | --- | --- | --- |
| **[INTRANET PROPIA]** | Ventas (CRM), Torre de control | Programado por nosotros desde cero | `/crm/`, `/ops/` |
| **[PANEL DE OSCAR]** | Pedidos y catálogo | El panel de gestión que trae django-oscar, la librería de la tienda | `/dashboard/` |
| **[FICHA DJANGO-ADMIN]** | Prospectos y mensajes, Camiones y despachos, Administración | El administrador de Django, con nuestro diseño y solo con nuestras tablas | `/admin/...` |
| **[TIENDA]** | (sin menú lateral) | La tienda pública, hecha con django-oscar | `tienda.` |

**Si el profe pregunta "¿eso es el admin de Django?", la respuesta es:**
> "Sí. Para las fichas de datos (camiones, despachos, prospectos, usuarios) usamos el administrador de Django, porque ya trae edición, búsqueda, historial y permisos probados. Le pusimos el mismo diseño y el mismo menú que la intranet, dejamos solo las tablas de Cofrial y cada rol ve solo las suyas. Lo que necesitaba lógica propia, el embudo del CRM y la torre de control con el mapa, lo programamos nosotros."

### Ventanas que hay que tener abiertas antes de empezar

Una ventana (o perfil de navegador) por cada una, ya con sesión iniciada salvo donde se indique:

1. Tienda **sin sesión**.
2. Tienda con sesión de `compras@hospital-demo.cl`.
3. Intranet **sin sesión** (Daniel inicia la sesión de vendedor en el video).
4. Intranet con sesión de `despacho@cofrial.cl`.
5. Intranet con sesión de `benjamin`.
6. Metabase (dashboard 2).
7. Consola de AWS en us-east-1 y una pestaña de CloudShell.
8. GitHub, repositorio `Drakn-Sub/cofrial`.

En CloudShell, antes de grabar: `bash ~/cofrial/infra/scripts/levantar.sh`. Anotar la **hora de la falla de CF-027**: la escena 6 se graba dentro de esos 10 minutos.

---

## Escena 0 · Presentación · B y D · 30 s

🖥 **PANTALLA:** ventana 3, la página de ingreso de la intranet `crm.cofrial-temuco.duckdns.org/ingresar/` (abajo aparecen los nombres de los dos).

**B:** "Hola, somos Benjamín Aguilar y Daniel Jara, de Transformación Digital de INACAP Temuco. Este es el Hito 2 del proyecto Cofrial."

**D:** "En este video mostramos todo el sistema funcionando en AWS Academy: la infraestructura, la tienda con sus precios para instituciones y público general, el CRM, la simulación IoT de los camiones, el dashboard de inteligencia de negocios, la inteligencia artificial y las pruebas de seguridad."

**B:** "Todo lo que van a ver está en vivo, conectado a la misma base de datos en la nube."

---

## Escena 1 · El problema y la arquitectura · B · 2 min

🖥 **PANTALLA:** GitHub → `docs/02-evidencias-hito2.md`, en el diagrama de arquitectura (o el diagrama del informe del Hito 1).

**B:** "Primero, el problema. Cofrial es una distribuidora de alimentos refrigerados con 30 años en La Araucanía, y tenía tres dolores."

**B:** "Uno: toda la empresa dependía de un único servidor en una bodega, sin respaldo, y cada área trabajaba en sus propias planillas."

**B:** "Dos: los 50 camiones frigoríficos andaban a ciegas. Nadie sabía la temperatura de la carga; se coordinaba por WhatsApp, y cuando una carga perdía el frío, se enteraban cuando el cliente reclamaba."

**B:** "Tres: no había canal digital. Los pedidos llegaban por teléfono y correo, y cada vendedor llevaba su cartera en su celular."

🖱 **HACER:** recorrer el diagrama con el mouse de arriba hacia abajo mientras se habla.

**B:** "Nuestra respuesta son cuatro canales que comparten una sola base de datos: la tienda, el CRM, la torre de control IoT y el dashboard. Al compartir la base, se rompen los silos: un pedido de la tienda aparece en el CRM sin que nadie lo copie, y si un camión pierde el frío, el sistema sabe qué pedidos lleva."

**B:** "Una visita entra así: internet, un balanceador de red con IP fija, un balanceador de aplicación que descifra HTTPS y reparte por nombre: tienda, CRM, operaciones y BI. De ahí pasa a uno de los dos servidores, que están en dos zonas distintas de AWS, y finalmente a la base de datos RDS, que tiene una réplica en la otra zona."

**B:** "Si se cae una zona completa, la otra sigue atendiendo. Daniel les muestra cómo está montado."

---

## Escena 2 · La infraestructura en AWS · D · 3,5 min

🖥 **PANTALLA:** consola de AWS, región Norte de Virginia.

🖱 **HACER:** VPC → Subredes → filtrar por `cofrial`.

**D:** "Esta es la red. Son siete subredes, separadas por capa y por zona: las públicas, donde vive solo el balanceador; las de aplicación, para los servidores; las de datos, para la base de datos; y una para los sensores IoT. Cada capa solo habla con la siguiente."

🖱 **HACER:** EC2 → Instancias. Mostrar `cofrial-app-a`, `cofrial-app-b` y `cofrial-iot`. Clic en `cofrial-app-a`.

**D:** "Tenemos tres servidores: dos de aplicación, uno en la zona 1a y otro en la 1b, y uno dedicado al simulador IoT."

🖱 **HACER:** señalar "Dirección IPv4 pública" vacía y "Par de claves" con un guion.

**D:** "Fíjense que no tienen IP pública ni llave SSH. Desde internet no se puede llegar a ellos. Los administramos con Session Manager de AWS, que no necesita puertos abiertos y deja registro de cada acceso."

🖱 **HACER:** EC2 → Grupos de seguridad → `cofrial-sg-rds` → Reglas de entrada.

**D:** "Este es el firewall de la base de datos. Solo acepta el puerto 5432 de PostgreSQL, y no desde una IP, sino desde el grupo de seguridad de los servidores. Es una cadena: balanceador, aplicación, base de datos. Nadie se puede saltar un eslabón."

🖱 **HACER:** VPC → ACL de red → `cofrial-nacl-datos` → Reglas de entrada.

**D:** "Además pusimos una segunda barrera a nivel de subred, una lista de control de acceso. Solo deja entrar PostgreSQL desde la aplicación y desde el IoT. Si alguien un día configura mal un grupo de seguridad, esta lista sigue bloqueando. Eso es defensa en profundidad."

🖱 **HACER:** RDS → Bases de datos → `cofrial-db`. Mostrar Multi-AZ, cifrado, acceso público y respaldos.

**D:** "La base de datos es PostgreSQL 16 en RDS. Multi-AZ: sí, o sea que tiene una réplica en la otra zona que toma el control sola si la principal falla. Cifrado: habilitado. Accesible públicamente: no. Y tiene respaldos automáticos de siete días. Esto reemplaza el servidor de la bodega sin respaldo."

🖱 **HACER:** Secrets Manager → solo la lista. **No abrir ninguno.**

**D:** "Ninguna contraseña está en el código. Están acá, en Secrets Manager. Cada servidor las lee al arrancar usando su rol de AWS, así que no hay claves guardadas en archivos."

🖱 **HACER:** S3 → `cofrial-media-605885` → Permisos.

**D:** "Las fotos de los productos están en este bucket, con todo el acceso público bloqueado. La tienda entrega enlaces firmados que vencen en una hora."

🖱 **HACER:** EC2 → Balanceadores de carga → `cofrial-alb` → Agentes de escucha.

**D:** "Y este es el balanceador de aplicación, con el certificado HTTPS de Let's Encrypt importado a Certificate Manager. Todo el tráfico va cifrado."

**D:** "Antes de construir todo esto, revisamos lo que había en la cuenta. Benjamín."

---

## Escena 3 · La auditoría inicial · B · 1,5 min

🖥 **PANTALLA:** GitHub → `docs/01-auditoria-inicial.md`. Después, las fotos de la carpeta 4 del ZIP: `01_ANTES_SSH_abierto_a_internet` y `02_DESPUES_SSH_cerrado`.

**B:** "Antes de programar, hicimos una auditoría de la cuenta. Encontramos diez problemas, dos de ellos críticos."

**B:** "El primero: el puerto SSH abierto a todo internet. Cualquiera en el mundo podía intentar adivinar la clave del servidor. El segundo: el servidor de la aplicación expuesto con IP pública. Además, la base de datos corría dentro de una máquina virtual, sin respaldos automáticos ni réplica, y los discos no estaban cifrados."

🖱 **HACER:** mostrar la foto del ANTES.

**B:** "Esta es la prueba de antes: la conexión al puerto 22 se abría."

🖱 **HACER:** mostrar la foto del DESPUÉS.

**B:** "Y esta es después de corregirlo: la conexión ya no abre. Los servidores viejos los detuvimos, no los borramos, porque son la evidencia de la auditoría."

**B:** "Ahora vamos a lo que ve el cliente: la tienda."

---

## Escena 4 · La tienda B2C y B2B · B · 3 min

🖥 **PANTALLA:** ventana 1 **[TIENDA]**, sin sesión, `tienda.cofrial-temuco.duckdns.org/catalogue/`.

**B:** "Esta es la tienda de Cofrial, hecha con django-oscar, una librería de código abierto para comercio electrónico. Corre en nuestros servidores y guarda todo en RDS."

🖱 **HACER:** abrir **Posta negra de vacuno 1 kg**.

**B:** "Sin sesión, soy público general, un cliente B2C. Este producto cuesta 8.990 pesos."

🖱 **HACER:** cambiar a la ventana 2 **[TIENDA]**, sesión del hospital, mismo producto.

**B:** "Ahora estoy conectado como el área de compras de un hospital, un cliente B2B. El mismo producto cuesta 7.990. La tienda reconoce a qué institución pertenezco y le aplica su lista de precios del convenio. Si el convenio vence, vuelve solo al precio público."

🖱 **HACER:** GitHub → `app/apps/partner/strategy.py` → clase `PrecioConvenio` (10 segundos).

**B:** "Esta es la regla que elige el precio, en el código."

🖱 **HACER:** ventana 2. Agregar **Pechuga de pollo**, cantidad 20, **Ir a la caja**, completar la dirección y **Confirmar pedido**.

**B:** "Voy a comprar 20 kilos de pechuga de pollo para el hospital. Carrito, caja, dirección de despacho y confirmo."

🖱 **HACER:** señalar el número del pedido. **Anotarlo** (lo van a buscar en las escenas 5 y 6).

**B:** "Pedido confirmado, con este número. Ya está guardado en RDS, con el estado Recibido y asociado al hospital. No hubo ninguna llamada ni correo."

🖱 **HACER:** ventana 1. Escribir `tienda.cofrial-temuco.duckdns.org/admin/` → aparece **404**.

**B:** "Una prueba de seguridad: si alguien busca el panel de administración en la dirección de la tienda, no existe. Las pantallas internas solo viven en la dirección de la intranet, y además piden segundo factor. Así reducimos lo que un atacante puede ver."

**B:** "Ese pedido ahora tiene que llegar al equipo comercial. Daniel."

---

## Escena 5 · CRM, roles e inteligencia artificial · D · 3,5 min

🖥 **PANTALLA:** ventana 3, página de ingreso de la intranet. Celular a mano.

🖱 **HACER:** ingresar con `vendedor@cofrial.cl` (**cortar en la edición la parte en que se escribe la clave**).

**D:** "Ahora entro a la intranet como vendedora. Después de la contraseña, me pide el código de seis dígitos del celular."

🖱 **HACER:** mostrar el celular con Google Authenticator y escribir el código.

**D:** "Todo el personal entra con segundo factor. Aunque alguien robe una contraseña, sin el celular no entra. Y si alguien pierde el celular, desde esta misma pantalla puede pedir un código QR nuevo, que el administrador aprueba."

🖥 **PANTALLA:** **[INTRANET PROPIA]** Ventas (CRM). Es lo primero que ve la vendedora.

**D:** "Esto lo programamos nosotros: el embudo comercial. Cada columna es una etapa de la venta, de prospecto a ganada, con el monto total de cada etapa."

🖱 **HACER:** mover una oportunidad de *Propuesta* a *Negociación*.

**D:** "Muevo esta oportunidad a negociación y queda guardado. Esto reemplaza la cartera que cada vendedor llevaba en su teléfono. Ahora la empresa ve todo el embudo, y cada vendedor ve solo sus oportunidades."

🖱 **HACER:** señalar el menú lateral.

**D:** "Miren el menú: la vendedora tiene Ventas y Prospectos y mensajes. No tiene la torre de control, porque no es su trabajo."

🖱 **HACER:** escribir a mano `crm.cofrial-temuco.duckdns.org/ops/` en la barra de direcciones.

**D:** "¿Y si intento entrar escribiendo la dirección a mano? Me devuelve al CRM con el aviso: tu perfil no tiene acceso a esa sección. Y el intento queda registrado en la auditoría."

🖥 **PANTALLA:** **[FICHA DJANGO-ADMIN]** menú **Prospectos y mensajes** → **Interacciones** → **Añadir interacción**.

**D:** "Ahora la inteligencia artificial. Esta es la ficha de interacciones con clientes. Para estas fichas de datos usamos el administrador de Django con nuestro diseño, porque ya trae formularios, búsqueda y permisos."

🖱 **HACER:** Cliente: *Hospital Regional*. Canal: *Correo*. Contenido: *"El camión no llegó y necesitamos la leche antes del almuerzo de los pacientes"*. **Guardar**.

**D:** "Llega un correo de un hospital: el camión no llegó y necesitan la leche antes del almuerzo. Lo registro y guardo."

🖱 **HACER:** señalar los campos **Categoría (IA): Despacho** y **Urgencia (IA): Alta** (si salen vacíos, recargar la ficha).

**D:** "La IA lo clasificó sola: es un tema de despacho y es urgencia alta. Así el mensaje llega a la persona correcta sin que alguien lo lea y lo reenvíe."

🖱 **HACER:** GitHub → `app/crm/ia.py` → función `seudonimizar` (15 segundos).

**D:** "Usamos Gemini de Google en su plan gratuito, así que tiene costo cero. Antes de enviar el texto, esta función le quita los RUT, correos y teléfonos, para no mandar datos personales afuera. Y la respuesta se valida contra una lista cerrada de categorías: si la IA inventa algo, se descarta. Si la IA no responde, el mensaje queda sin clasificar y el CRM sigue funcionando igual."

🖥 **PANTALLA:** volver a **[FICHA DJANGO-ADMIN]** Interacciones (la lista).

**D:** "Y miren la lista: arriba aparece el pedido web que hizo el hospital en la tienda hace un momento. El vendedor se entera del pedido sin que nadie lo llame. Ese es el fin del pedido por teléfono."

**D:** "Ahora, ¿qué pasa con ese pedido cuando sale en un camión? Benjamín."

---

## Escena 6 · Sensores IoT y torre de control · B · 3,5 min

> **Grabar dentro de la ventana de falla de CF-027.** Si no saben la hora: `bash ~/cofrial/infra/scripts/proxima_falla.sh`.

### Preparación (10 minutos antes de la falla, NO se graba)

Con la ventana 4 (sesión de **despacho**):

1. **[PANEL DE OSCAR]** menú **Pedidos y catálogo** → **Pedidos** → abrir el pedido de la escena 4 → cambiar el estado paso a paso: *Pagado → En preparación → Asignado → En ruta*.
2. **[FICHA DJANGO-ADMIN]** menú **Camiones y despachos** → **Despachos** → abrir el despacho **En ruta** del camión **CF-027** → en *Pedidos*, clic en la lupa, buscar el número del pedido de la escena 4, seleccionarlo → **Guardar**.

Así el pedido que compraron en el video va en el camión que va a fallar.

### Grabación

🖥 **PANTALLA:** GitHub → `iot/simulador.py`, en la sentencia `INSERT`.

**B:** "La pauta pide simular la telemetría de los camiones con contenedores Docker en un servidor dedicado. Este es el simulador. Cada 30 segundos inserta en RDS una lectura de cada uno de los 50 camiones, con los seis campos exigidos: el identificador del camión, la temperatura de la cámara, la latitud, la longitud, el porcentaje de combustible y si hay alerta de ruptura de frío."

🖥 **PANTALLA:** CloudShell (letra grande con Ctrl + `+`).

🖱 **HACER:** escribir:
```bash
. ~/cofrial/infra/scripts/correr.sh
correr $I 'docker ps --format "{{.Names}} {{.Status}}"; docker logs --tail 3 $(docker ps -q | head -1)'
```

**B:** "Este comando entra al servidor IoT sin SSH, usando Session Manager. Aquí se ve el contenedor del simulador corriendo, y sus últimas líneas: cincuenta lecturas en cada ciclo. Esto corre solo, sin que nadie toque nada."

🖥 **PANTALLA:** ventana 4, **[INTRANET PROPIA]** menú **Torre de control**.

**B:** "Esta es la torre de control que usa el despachador. Esta pantalla la programamos nosotros. El mapa 3D muestra la región con satélite y relieve, y cada camión está en su última posición, orientado según su ruta."

🖱 **HACER:** acercar el mapa a algunos camiones.

**B:** "Los camiones azules llevan carga congelada y los verdes, refrigerada. Cada uno tiene un termómetro: la franja es el rango permitido para su carga y la marca es la temperatura actual."

🖱 **HACER:** mostrar **CF-027 en rojo**: su etiqueta en el mapa, la fila roja primera en la lista y la alerta arriba con sus pedidos.

**B:** "Y aquí está el problema: el camión CF-027 está en rojo. Su equipo de frío se detuvo y la temperatura subió fuera del rango. El sistema abrió la alerta solo, después de dos lecturas seguidas fuera de rango; pedimos dos para no alarmar por un error puntual del sensor."

🖱 **HACER:** señalar en la alerta el número del pedido de la escena 4.

**B:** "La alerta dice qué pedidos lleva ese camión, y aquí está el pedido que el hospital compró en la tienda hace unos minutos. Antes, esto se sabía horas después, cuando el cliente reclamaba por WhatsApp."

🖱 **HACER:** escribir en la nota *"Llamé al conductor: la puerta de la cámara quedó mal cerrada"* → **Tomar la alerta**.

**B:** "El despachador llama al conductor, anota qué pasó y toma la alerta. Queda registrado quién la atendió y cuándo."

🖥 **PANTALLA:** ventana 4, **[PANEL DE OSCAR]** menú **Pedidos y catálogo** → el pedido de la escena 4.

**B:** "Ahora vuelvo al panel de pedidos, que es el que trae django-oscar. El pedido del hospital ya no dice En ruta: dice En ruta con alerta. El sistema lo marcó solo."

🖥 **PANTALLA:** ventana 5 (`benjamin`), **[FICHA DJANGO-ADMIN]** menú **Administración** → **Interacciones**.

**B:** "Y en las interacciones del CRM, que es una ficha del administrador de Django, aparece un aviso automático de urgencia alta para el hospital. El vendedor ya sabe que tiene que llamar al cliente antes de que el cliente lo llame a él."

**B:** "Este es el recorrido completo, de punta a punta: un pedido hecho en la tienda, que viaja en un camión, que pierde el frío, y que el sistema detecta y avisa en segundos. Daniel les muestra cómo lo ve la gerencia."

---

## Escena 7 · Dashboard de BI con Metabase · D · 2 min

🖥 **PANTALLA:** ventana 6, Metabase, `bi.cofrial-temuco.duckdns.org/dashboard/2`. Si un gráfico dice "Hubo un problema", recargar.

**D:** "Este es el dashboard de inteligencia de negocios. Usamos Metabase, una herramienta de código abierto y gratuita que corre en nuestros propios servidores y se conecta directo a la base de datos en RDS."

🖱 **HACER:** señalar los indicadores de arriba.

**D:** "Arriba están los números clave: las ventas de los últimos 30 días, la cantidad de pedidos, cuántos camiones están fuera de rango en este momento, y las alertas del mes."

🖱 **HACER:** señalar las ventas semanales por canal y la torta.

**D:** "Aquí, las ventas semanales separadas por canal, y la torta muestra que la mayor parte de las ventas, el 84 por ciento, viene de instituciones."

🖱 **HACER:** señalar el mapa y la temperatura de la flota.

**D:** "Este es el estado de la flota en vivo: posición y temperatura de los camiones."

🖱 **HACER:** señalar **Pedidos afectados por alertas de frío** (debería aparecer el pedido del video).

**D:** "Y esto es lo que pide la pauta: cruzar lo comercial con lo operativo. Aquí aparecen los pedidos afectados por alertas de frío, y está el pedido del hospital del video. Gerencia ve en la misma pantalla cuánto vende y qué ventas están en riesgo por la cadena de frío."

🖱 **HACER:** recargar la página.

**D:** "Cada gráfico es una consulta a la base de datos que se ejecuta al abrir o recargar, por eso los datos son en tiempo real. Y Metabase se conecta con un usuario que solo puede leer cinco vistas de resumen, sin nombres, RUT ni correos."

**D:** "Por último, cómo comprobamos que todo esto es seguro."

---

## Escena 8 · Seguridad verificable y DevSecOps · D · 2,5 min

🖥 **PANTALLA:** CloudShell.

🖱 **HACER:** escribir `bash ~/cofrial/infra/scripts/pruebas_seguridad.sh` y bajar por el resultado hasta **29 pasan, 0 fallan**.

**D:** "Escribimos 29 pruebas de seguridad que cualquiera puede repetir desde aquí. Revisan que el cifrado sea TLS 1.3, que estén las cabeceras de seguridad, que las rutas internas estén ocultas en la tienda, que el bloqueo por fuerza bruta funcione, porque al quinto intento responde 429, y que la configuración de AWS siga como la dejamos. Veintinueve pasan, cero fallan."

🖱 **HACER:** escribir:
```bash
. ~/cofrial/infra/scripts/correr.sh
correr $A 'bash /opt/cofrial/infra/scripts/verificar_privilegios_nodo.sh' 25
```

**D:** "Esto revisa el mínimo privilegio en la base de datos real. Veinte de veinte: la aplicación no puede borrar tablas ni modificar la auditoría; el simulador IoT solo puede insertar lecturas, así que si alguien se apodera de ese servidor, no puede leer clientes; y Metabase solo puede leer los resúmenes."

🖥 **PANTALLA:** GitHub → Actions → `ci-seguridad` en verde → abrir una ejecución y mostrar los pasos.

**D:** "Y esto es DevSecOps: en cada cambio que subimos, GitHub revisa automáticamente que no se haya filtrado ninguna contraseña, analiza el código, busca vulnerabilidades en las librerías, prueba los privilegios y corre 32 pruebas automáticas. Si algo falla, el cambio no pasa. La seguridad se revisa sola, no al final del proyecto."

🖥 **PANTALLA:** ventana 5 (`benjamin`), **[FICHA DJANGO-ADMIN]** menú **Administración** → **Eventos de auditoría**.

**D:** "Por último, la auditoría, que es otra ficha del administrador de Django, visible solo para el administrador. Aquí están los inicios de sesión, el acceso denegado de la vendedora cuando intentó entrar a la torre, y la alerta del camión. Nadie puede borrar estos registros, ni siquiera la propia aplicación: la base de datos solo le permite agregar."

---

## Escena 9 · Cierre · B y D · 45 s

🖥 **PANTALLA:** página de ingreso de la intranet, o el diagrama de arquitectura.

**B:** "Para cerrar: cumplimos los cinco puntos del Hito 2. Despliegue en EC2 y RDS, tienda con precios B2B y B2C y CRM conectados a la misma base, simulación IoT con Docker, dashboard en tiempo real que cruza ventas con la cadena de frío, e inteligencia artificial gratuita clasificando mensajes."

**D:** "Y lo hicimos seguro por diseño: servidores sin exposición a internet, contraseñas fuera del código, segundo factor, roles separados, mínimo privilegio en la base de datos, y pruebas que cualquiera puede repetir."

**B:** "Usamos un asistente de inteligencia artificial como apoyo para programar y documentar, y está declarado en el repositorio. Las decisiones de arquitectura, la operación en AWS y la verificación de las pruebas las hicimos nosotros."

**D:** "Gracias."

---

## Si el profe pregunta en vivo

| Pregunta | Quién | Respuesta |
| --- | --- | --- |
| ¿Eso es el admin de Django? | B | "Sí, las fichas de datos usan el administrador de Django con nuestro diseño, solo con las tablas de Cofrial y filtradas por rol. El CRM y la torre de control los programamos nosotros." |
| ¿Y Pedidos y catálogo? | B | "Es el panel de gestión que trae django-oscar, la librería de la tienda. Lo usamos para no rehacer la gestión de pedidos, y le agregamos el estado En ruta con alerta." |
| ¿Por qué no programaron todo desde cero? | D | "Porque reutilizar componentes probados es más seguro y más rápido. Pusimos el esfuerzo donde Cofrial necesitaba algo propio: el embudo, la torre, las alertas, la IA y la seguridad." |
| ¿Los autores de Oscar pueden entrar? | D | "No. Oscar es una librería que corre en nuestros servidores; no se conecta a nada externo ni tiene cuentas de ellos." |
| ¿Por qué tantas subredes? | D | "Una por capa y por zona: aísla responsabilidades y da alta disponibilidad." |
| ¿Qué pasa si se cae una zona? | D | "El balanceador deja de mandar tráfico al servidor caído y RDS cambia sola a la réplica." |
| ¿Por qué dos balanceadores? | D | "DuckDNS necesita una IP fija, que da el de red. El de aplicación descifra HTTPS y reparte por nombre." |
| ¿Cómo detecta que un camión perdió el frío? | B | "Cada camión tiene un rango según su carga. Con dos lecturas seguidas fuera de rango se abre la alerta, y con dos dentro se cierra." |
| ¿Los datos IoT son reales? | B | "Son simulados por un contenedor Docker, como pide la pauta, con el mismo formato que mandaría un sensor real." |
| ¿La IA ve datos personales? | D | "No. Se le quitan RUT, correos y teléfonos antes de enviar, y la respuesta se valida contra una lista cerrada." |
| ¿Por qué Metabase? | D | "Es gratuito y de código abierto, corre en nuestros servidores y lee con un usuario de solo lectura." |
| ¿Cuánto cuesta? | B | "Todo cabe en el crédito de AWS Academy. Metabase, Gemini, Mapbox y el dominio son gratuitos." |
| ¿Qué harían en producción? | B | "Dominio propio, MFA en AWS, alarmas de CloudWatch, firewall web delante del balanceador y respaldos en otra región." |
