# Cómo levantar Cofrial

Guía de operación para quien tenga el laboratorio de AWS Academy (Daniel). Explica cómo encender todo, revisar que funcione, publicar cambios y resolver los problemas típicos. **No hace falta saber de memoria nada de lo que hay aquí:** basta seguir los pasos en orden.

## Resumen en 5 pasos

1. AWS Academy → **Start Lab** → esperar el punto verde → botón **AWS**.
2. En la consola, abrir **CloudShell** (ícono `>_` arriba a la derecha).
3. Solo la primera vez: pegar el bloque de la sección 3.
4. Ejecutar `bash ~/cofrial/infra/scripts/levantar.sh`.
5. Si todo sale con ✔ verde: abrir los links que entrega al final. Listo.

Desde que se hace clic en Start Lab hasta que todo funciona pasan unos **15 minutos**, casi todo esperando a la base de datos. Por eso el día de grabar hay que empezar **una hora antes**.

## 1. Iniciar el laboratorio

1. Entrar al curso en AWS Academy → *Modules* → *Launch AWS Academy Learner Lab*.
2. Clic en **Start Lab**. El círculo junto a "AWS" pasa de rojo a amarillo y después a **verde** (1 a 3 minutos).
3. Clic en **AWS** (el texto con el punto verde). Se abre la consola en otra pestaña.
4. Revisar arriba a la derecha que la región sea **Estados Unidos (Norte de Virginia) / us-east-1**.

> **El laboratorio dura 4 horas.** Al terminar, AWS apaga los servidores solo. Se puede extender con *Start Lab* otra vez antes de que se acabe. Revisar también **"Used $ of $50"** en la página del laboratorio: si el saldo se acaba, se pierde todo.

## 2. Abrir CloudShell

CloudShell es una terminal dentro de la consola de AWS que ya tiene permisos sobre la cuenta. Todo se hace desde ahí; **no se necesita SSH ni llaves**.

- Ícono `>_` en la barra superior de la consola, o buscar "CloudShell".
- La carpeta personal (`~`) se conserva entre sesiones. Por eso el paso 3 se hace solo una vez.

**Si aparece un error de credenciales** (`ExpiredToken`, `voc-cancel-cred`, `AccessDenied` en todo): el laboratorio se reinició y CloudShell quedó con las credenciales viejas. Cerrar la pestaña de la consola, volver a hacer clic en **AWS** desde la página del laboratorio, y en CloudShell ir a **Acciones → Reiniciar AWS CloudShell**.

## 3. Preparar CloudShell (solo la primera vez)

Descarga el código del proyecto a la carpeta `~/cofrial`. Usa el token de solo lectura guardado en Secrets Manager (`cofrial/github`), así que **no hay que escribir ninguna clave**. Pegar esto completo y presionar Enter:

```bash
TK=$(aws secretsmanager get-secret-value --secret-id cofrial/github --query SecretString --output text | jq -r .token); H="Authorization: Basic $(printf 'x-access-token:%s' "$TK" | base64 -w0)"; unset TK; if [ -d ~/cofrial/.git ]; then git -C ~/cofrial -c http.extraHeader="$H" pull -q; else git -c http.extraHeader="$H" clone -q https://github.com/Drakn-Sub/cofrial.git ~/cofrial; fi; unset H; git -C ~/cofrial log --oneline -1
```

Debe terminar mostrando el último commit (por ejemplo `24799c6 levantar.sh: ...`). **El mismo bloque sirve para actualizar** la copia de CloudShell cuando alguien sube cambios a GitHub. Si después dice "No such file" con algún script, es porque la copia está vieja: volver a pegar este bloque.

Después de la primera vez, el atajo es:

```bash
bash ~/cofrial/infra/scripts/primera_vez_cloudshell.sh
```

## 4. Levantar todo

```bash
bash ~/cofrial/infra/scripts/levantar.sh
```

Se puede ejecutar todas las veces que se quiera: lo que ya está bien no lo toca. Tarda entre 2 minutos (todo encendido) y 15 minutos (todo apagado). Cada línea con **✔ verde** está bien; una con **✘ roja** explica qué falló.

| Paso | Qué hace | Si sale ✘ |
| --- | --- | --- |
| 1. Credenciales | Revisa que CloudShell tenga permisos vigentes | Ver "error de credenciales" en la sección 2 |
| 2. Servidores | Enciende `cofrial-app-a`, `cofrial-app-b` y `cofrial-iot` | Revisar en EC2 que existan y no estén terminados |
| 3. Base de datos | Enciende RDS `cofrial-db` y espera (hasta 10 min) | Esperar y volver a ejecutar |
| 4. Servidores viejos | Detiene los 2 servidores de la auditoría, que AWS Academy enciende solo al iniciar el lab | Detenerlos a mano en EC2 (etiqueta `Estado=reemplazado-auditoria-H2-H3`). **Nunca terminarlos**: son evidencia del Hito 2 |
| 5. Aplicación | Levanta los contenedores (tienda, CRM, torre, Metabase, simulador) y revisa `/salud/` | Ver la sección 8 |
| 6. Seguridad | Corre las 29 pruebas | Si falla alguna, casi siempre es un servidor viejo encendido: volver a ejecutar en 1 minuto |
| 7. Próxima falla | Dice a qué hora falla el camión CF-027 | Si dice "no pude leer el simulador", esperar 1 minuto |

Así se ve cuando todo está bien:

```
5. Aplicación y sensores
  ✔ cofrial-app-a: tienda, CRM, torre y Metabase funcionando
  ✔ cofrial-app-b: tienda, CRM, torre y Metabase funcionando
  ✔ Simulador IoT: ciclo 159: 50 lecturas, 1 fuera de rango
6. Pruebas de seguridad
Resultado: 29 pruebas pasan, 0 fallan
7. Próxima falla del camión CF-027 (para grabar)
CF-027 está bien. La próxima falla empieza en 50 min, a las 03:54.
```

**Sobre la hora de la falla:** el simulador cuenta los ciclos desde que arrancó su contenedor, así que la hora cambia cada vez que se reinicia el laboratorio. La falla dura 10 minutos y se repite cada hora. Para saberla otra vez sin levantar todo: `bash ~/cofrial/infra/scripts/proxima_falla.sh`.

## 5. Links

| Qué | Link | Quién entra |
| --- | --- | --- |
| Tienda | https://tienda.cofrial-temuco.duckdns.org | Clientes (`compras@hospital-demo.cl`) |
| Intranet | https://crm.cofrial-temuco.duckdns.org | Personal, con 2FA. Cada rol llega a su pantalla |
| Metabase | https://bi.cofrial-temuco.duckdns.org/dashboard/2 | Cuentas de Metabase (Benjamín y Daniel) |
| Código | https://github.com/Drakn-Sub/cofrial | |

`ops.cofrial-temuco.duckdns.org` es la misma intranet que `crm.`: todos los ingresos llegan a `/ingresar/` y desde ahí cada rol va a su sección.

## 6. Ejecutar comandos en un servidor

Para cualquier cosa que haya que hacer dentro de un servidor, cargar el ayudante una vez por sesión:

```bash
. ~/cofrial/infra/scripts/correr.sh
```

Muestra los IDs de los tres servidores y deja las variables `$A`, `$B` e `$I`. Ejemplos:

```bash
correr $A 'docker ps --format "{{.Names}} {{.Status}}"'          # contenedores de app-a
correr $I 'docker logs --tail 5 $(docker ps -q | head -1)'        # últimas lecturas del simulador
correr $A 'bash /opt/cofrial/infra/scripts/verificar_privilegios_nodo.sh' 25   # 20 privilegios de la BD
```

## 7. Publicar un cambio de código

Cuando alguien sube un cambio a la rama `main` en GitHub (y el pipeline de GitHub Actions está en verde), hay que actualizar **los dos** servidores de aplicación, uno después del otro, para que la tienda nunca se caiga:

```bash
. ~/cofrial/infra/scripts/correr.sh
for S in $A $B; do
  correr $S 'DOMINIO=cofrial-temuco.duckdns.org bash /opt/cofrial/infra/scripts/preparar_nodo_app.sh && bash /opt/cofrial/infra/scripts/desplegar_app.sh --migrar --bi' 15
done
```

`preparar_nodo_app.sh` descarga el código nuevo y renueva las variables desde Secrets Manager. `desplegar_app.sh` construye y reinicia los contenedores. Cada servidor tarda unos 3 a 5 minutos y al final debe mostrar `{"estado": "ok"}`. Si se cambió el simulador, lo mismo con `$I` y `preparar_nodo_iot.sh`.

> Las migraciones (`--migrar`) usan el rol `cofrial_migrate`. La aplicación en operación usa `cofrial_app`, que no puede crear ni borrar tablas. Esto es parte del mínimo privilegio que se muestra en el video.

## 8. Tareas de administración

Estas tareas necesitan escribir en la terminal del servidor (por ejemplo, una contraseña nueva), así que se usa una **sesión interactiva** en vez de `correr`:

```bash
. ~/cofrial/infra/scripts/correr.sh
aws ssm start-session --target $A
```

Ya dentro del servidor (el indicador cambia a `sh-5.2$`):

```bash
cd /opt/cofrial/infra
sudo docker compose -f compose.app.yml exec django python manage.py changepassword jefatura@cofrial.cl
```

| Para qué | Comando (después de `sudo docker compose -f compose.app.yml exec django python manage.py`) |
| --- | --- |
| Cambiar la clave de un usuario | `changepassword <usuario>` (por ejemplo `daniel`, `jefatura@cofrial.cl`) |
| Alguien perdió el celular del 2FA | `reiniciar_2fa <usuario>`: en su próximo ingreso verá un QR nuevo. También se puede desde *Fichas y registros → Usuarios → acción "Entregar un código QR nuevo"* |
| Alguien quedó bloqueado por 5 claves malas | `axes_reset` (desbloquea a todos) |

Salir de la sesión con `exit`. La base de datos es la misma para los dos servidores, así que basta hacerlo en `$A`.

> **Nunca escribir contraseñas en el chat, en documentos ni en GitHub.** Las claves del sistema están en Secrets Manager y las de los usuarios las elige cada uno.

## 9. Renovar el certificado HTTPS

El certificado de Let's Encrypt vence **90 días** después de emitido. La fecha está en *Certificate Manager (ACM) → `*.cofrial-temuco.duckdns.org` → "No es posterior a"*. Unas dos semanas antes de que venza:

```bash
. ~/cofrial/infra/scripts/correr.sh
correr $A 'DOMINIO=cofrial-temuco.duckdns.org bash /opt/cofrial/infra/scripts/emitir_certificado.sh' 5
```

Reemplaza el mismo certificado en ACM, así que el balanceador lo toma solo, sin tocar nada más.

## 10. Problemas comunes

| Síntoma | Causa | Qué hacer |
| --- | --- | --- |
| El navegador dice "no se puede acceder al sitio" | El laboratorio está apagado o los servidores se están encendiendo | Ejecutar `levantar.sh` y esperar a que termine |
| Error 502 o 503 un rato después de encender | Los contenedores todavía están arrancando | Esperar 1 minuto y recargar |
| `levantar.sh: No such file or directory` | La copia de CloudShell está vieja o no existe | Pegar el bloque de la sección 3 |
| `ExpiredToken` o `AccessDenied` en todo | Credenciales viejas de CloudShell | Volver a entrar con el botón **AWS** y reiniciar CloudShell |
| Pruebas de seguridad 27/29 o similar | Los servidores viejos de la auditoría se encendieron con el lab | `levantar.sh` los detiene; volver a correr las pruebas |
| La torre no muestra alerta | La falla de CF-027 todavía no empieza | `proxima_falla.sh` dice cuándo. La alerta aparece 1 a 2 minutos después |
| El mapa se ve plano o sin satélite | No cargó el token de Mapbox | Recargar con Ctrl+F5. Si sigue, revisar que `MAPBOX_TOKEN` esté en el secreto `cofrial/app` y publicar otra vez (sección 7) |
| La IA no clasifica ("sin IA") | Gemini sin cuota o caído un momento | El CRM sigue funcionando con la regla básica. Probar de nuevo en unos minutos |
| "Cuenta bloqueada" al ingresar | 5 claves malas: django-axes la bloquea por 1 hora | `axes_reset` (sección 8) |
| Metabase pide configurar todo de nuevo | Se borró la base `metabase` | No debería pasar. Avisar a Benjamín antes de tocar nada |
| Se acaba el saldo de $50 | Nat Gateway y balanceadores cobran aunque los servidores estén apagados | Revisar "Used $" cada vez que se entra. No crear recursos nuevos |

## 11. Qué no hacer nunca

- **Terminar** (borrar) servidores, la base de datos o el bucket S3: se pierde todo y no hay copia fuera del laboratorio. Para ahorrar se **detienen**.
- Abrir el puerto 22 (SSH) en los grupos de seguridad: fue uno de los hallazgos de la auditoría y las pruebas de seguridad lo revisan.
- Mostrar en el video los valores de Secrets Manager, contraseñas o el token de Mapbox.
- Hacer *Reset* del laboratorio en AWS Academy: borra **todos** los recursos de la cuenta.
