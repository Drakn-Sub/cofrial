# Guion de la demo: Cofrial SpA (Hito 2)

**Duración objetivo:** 15 minutos de demo + 5 de preguntas · **Presentan:** Benjamín (B) y Daniel (D)

> Idea fuerza: *"Cofrial pasó de WhatsApp, Excel y un servidor en una bodega a una cadena de frío
> visible en tiempo real, segura por diseño y verificable con pruebas automáticas."*

---

## Antes de empezar (30 minutos antes)

1. **Iniciar el laboratorio** de Daniel en AWS Academy (*Start Lab*) y esperar el círculo verde. RDS puede tardar unos 10 minutos en estar disponible.
2. En CloudShell, comprobar que todo responde:
   ```bash
   bash ~/cofrial/infra/scripts/pruebas_seguridad.sh   # debe decir 29 pasan
   ```
3. Abrir estas pestañas en este orden y **dejar las sesiones iniciadas**, para que el 2FA no se coma tiempo:
   1. Tienda, **sin sesión**: https://tienda.cofrial-temuco.duckdns.org
   2. Tienda en ventana de incógnito, con sesión de `compras@hospital-demo.cl`.
   3. CRM con `vendedor@cofrial.cl`: https://crm.cofrial-temuco.duckdns.org
   4. Torre de control con `despacho@cofrial.cl`: https://ops.cofrial-temuco.duckdns.org
   5. Metabase: https://bi.cofrial-temuco.duckdns.org/dashboard/2
   6. Consola AWS → EC2 → Instancias, más una pestaña de **CloudShell**.
   7. GitHub: https://github.com/Drakn-Sub/cofrial (pestaña *Actions*).
4. **Ver la hora de la falla de CF-027.** En la torre de control, la sección "alertas recientes" muestra a qué minuto empezó la última. La falla se repite cada 60 minutos y dura 10, así que hay que calcular cuándo llega la próxima para mostrarla en vivo. Si no coincide, hay alertas pasadas para mostrar y una tabla de "pedidos afectados" en Metabase.
5. Celular con Google Authenticator a mano.

Si un gráfico de Metabase muestra "Hubo un problema", **recarga la página** (F5). En el mapa de Metabase, no uses la rueda del mouse encima del mapa porque hace zoom.

---

## 1. El problema y la solución (1,5 min) · B

> "Cofrial tiene 50 camiones que operan a ciegas: la temperatura se controla por WhatsApp, los pedidos
> llegan por teléfono y los vendedores manejan sus clientes en el celular. Todo depende de un servidor en
> una bodega. Construimos un ecosistema en AWS con cuatro canales conectados a una sola base de datos:
> tienda, CRM, torre de control IoT y BI, con IA para atender clientes."

Mostrar el diagrama de arquitectura del Hito 1 o el de la sección 1 de `02-evidencias-hito2.md`.

## 2. Infraestructura en AWS (3 min) · D

En la consola de AWS:

1. **EC2 → Instancias:** `cofrial-app-a` en la zona **1a** y `cofrial-app-b` en la **1b**.
   > "Dos servidores en dos zonas de disponibilidad detrás de un balanceador: si se cae una zona, el
   > sitio sigue arriba. Ninguno tiene IP pública ni llave SSH; los administramos con Session Manager."
2. **RDS → cofrial-db:** Multi-AZ, cifrada, *Publicly accessible: No*.
   > "La base de datos es RDS PostgreSQL con réplica en otra zona y respaldos de 7 días. No es
   > alcanzable desde internet."
3. **VPC → Subredes** (la pregunta que el profe ya hizo):
   > "Tenemos una subred por **capa** y por **zona**: públicas solo para el balanceador, de aplicación
   > para Django y de datos sin ninguna ruta a internet. Duplicarlas en 1a y 1b es lo que permite la alta
   > disponibilidad. La subred IoT separa a los sensores, que solo pueden insertar datos."
4. **Auditoría:** abrir `docs/01-auditoria-inicial.md` en GitHub.
   > "Antes de programar auditamos lo que había. Encontramos SSH abierto a todo internet y la base en una
   > EC2. Lo corregimos y lo demostramos: antes la conexión abría, ahora no."
   >
   > Mostrar las capturas `ssh-antes` y `ssh-despues`.

## 3. Tienda B2B / B2C (3 min) · B

1. **Pestaña sin sesión:** catálogo con 20 productos refrigerados. Abrir uno, por ejemplo "Posta negra", y anotar el precio público: **$8.990**.
2. **Pestaña del hospital (incógnito):** el mismo producto cuesta **$7.990**.
   > "La tienda reconoce que es un cliente institucional y aplica la lista de precios de su convenio.
   > Si el convenio vence, vuelve al precio público."
3. Agregar 2 productos al **carrito** → *Ir a la caja* → completar el pedido → mostrar el **número de orden**.
4. En la pestaña del CRM → **Administración → Interacciones**: la primera fila es "Pedido web …" del hospital.
   > "La tienda y el CRM comparten la base: el vendedor ve el pedido sin que nadie lo llame."
5. Seguridad visible: en la pestaña sin sesión, ir a `tienda…/admin/` → **404**.
   > "Las rutas internas no existen en el sitio público."

## 4. CRM e IA (2,5 min) · D

1. **Kanban:** mover una oportunidad de *Propuesta* a *Negociación*.
   > "Este vendedor solo ve sus oportunidades; si cambia el número en la URL para ver la de otro, recibe 404."
2. **IA:** en **Administración → Interacciones → Añadir**: elegir el cliente "Hospital…", canal *Correo* y escribir:
   *"El camión no llegó y necesitamos la leche antes del almuerzo de los pacientes"* → Guardar.
   Aparece **Despacho / Alta** sin que nadie la clasifique.
   > "Usamos Gemini en su plan gratuito. Antes de enviar el texto le quitamos RUT, correos y teléfonos, y
   > validamos la respuesta contra una lista cerrada. Si la IA no responde, el CRM sigue funcionando."
3. **2FA:** mostrar el celular con el código de Authenticator.
   > "Todo el personal interno entra con segundo factor."

## 5. IoT y torre de control (3 min) · B. **El momento clave**

1. **Torre de control:** mapa de La Araucanía con 50 camiones, tabla de temperaturas y "se actualiza cada 30 s".
   > "Cada camión es un contenedor Docker en el nodo IoT que envía temperatura, coordenadas, combustible
   > y la alerta cada 30 segundos, con un usuario de base de datos que solo puede insertar."
2. **CF-027 en falla** (en vivo o en el historial): punto rojo en el mapa y alerta activa con sus pedidos.
   > "El sistema cruzó los silos solo: los pedidos de ese camión pasaron a 'En ruta con alerta' y el
   > hospital tiene un aviso de urgencia alta en el CRM. Antes esto se enteraba por WhatsApp, horas después."
3. **Tomar la alerta:** escribir *"Conductor revisa el equipo de frío"* → *Tomar alerta*. Queda el responsable con su nombre.
4. *(Opcional)* en CloudShell, mostrar los contenedores insertando datos:
   ```bash
   aws ssm send-command --instance-ids <id cofrial-iot> --document-name AWS-RunShellScript \
     --parameters 'commands=["docker logs --tail 3 $(docker ps -q)"]'
   ```

## 6. Dashboard de BI (1,5 min) · D

En Metabase:
- **Indicadores:** ventas de 30 días, pedidos, camiones fuera de rango ahora y alertas.
- **Ventas por canal**: B2B es el 84 %.
- **Mapa y temperatura en vivo.**
- **Pedidos afectados por alertas:** el cruce que pide la pauta, ventas con cadena de frío.

> "Metabase se conecta con un usuario que solo lee vistas agregadas: no puede ver nombres, RUT ni contraseñas."

## 7. Seguridad verificable (1 min) · B

En CloudShell, ejecutar en vivo:
```bash
bash ~/cofrial/infra/scripts/pruebas_seguridad.sh
```
> "29 controles automáticos: cifrado, superficie de ataque, fuerza bruta (al 5.º intento te bloquea) y la
> configuración de AWS. Además, cada cambio en GitHub pasa por un pipeline que busca secretos,
> vulnerabilidades en el código y en las dependencias, y prueba los privilegios de la base."

Mostrar la pestaña *Actions* de GitHub con el pipeline en verde.

## Cierre (30 s) · D

> "Cumplimos los cinco puntos del Hito 2 con todo conectado en AWS, y lo hicimos seguro por diseño: sin
> servidores expuestos, con secretos fuera del código, mínimo privilegio y pruebas que cualquiera puede
> repetir."

---

## Preguntas probables

| Pregunta | Respuesta corta |
| --- | --- |
| ¿Por qué tantas subredes? | Una por capa (pública, aplicación, datos, IoT) y por zona (1a y 1b). Aísla responsabilidades y permite alta disponibilidad. |
| ¿Qué pasa si se cae una zona? | El ALB deja de mandar tráfico al nodo caído y RDS conmuta a la réplica de la otra zona. El simulador se reconecta solo. |
| ¿Por qué NLB y ALB? | DuckDNS necesita una IP fija (el NLB tiene IP elásticas) y el ALB termina el TLS y enruta por nombre (tienda, crm, ops, bi). |
| ¿Por qué Django y no Laravel? | Python para todo: el simulador IoT (exigido en Python), la tienda con django-oscar y la IA. Un solo lenguaje y un solo equipo. |
| ¿Dónde están las contraseñas? | En Secrets Manager. Los servidores las leen con su rol IAM al arrancar; nunca están en el código. Gitleaks lo verifica en cada push. |
| ¿Cómo evitan que alguien adivine claves? | Nginx limita la frecuencia y django-axes bloquea tras 5 fallos. Las contraseñas usan Argon2 y el personal tiene 2FA. |
| ¿La IA ve datos personales? | No: se seudonimiza (RUT, correos y teléfonos) antes de enviar, y la respuesta se valida contra una lista cerrada. |
| ¿Por qué Metabase? | Es open source y gratis, se conecta directo a PostgreSQL y corre en nuestros propios servidores. Se le da un usuario de solo lectura. |
| ¿Cuánto cuesta? | Todo cabe en el crédito de AWS Academy. La IA y Metabase cuestan cero, y el dominio es gratuito. |
| ¿Usaron IA para programar? | Sí, como apoyo, y está declarado en el README. Las decisiones, la operación de AWS y la validación las hicimos nosotros. |
