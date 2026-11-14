# Auditoría inicial de la infraestructura AWS

- **Fecha:** 13 de noviembre de 2026
- **Cuenta revisada:** Learner Lab de Daniel Jara (curso 193918), región us-east-1
- **Método:** inventario de solo lectura con AWS CLI desde CloudShell (`describe-*`, `list-*`). No se modificó ningún recurso.
- **Referencia:** Informe del Hito 1 (Tablas 5 y 6) y guía paso a paso.

## Resumen

La **red está bien construida** y sigue el diseño del informe: VPC `10.20.0.0/16`, 7 subredes en dos zonas, la base de datos sin ruta a Internet, NAT Gateway y endpoint de S3. Los problemas están en **cómo se publicaron los servidores**: el servidor de aplicación está en una subred pública con IP pública y **SSH abierto a todo Internet**, y la base de datos corre en una EC2 en vez de RDS, que es lo que exige la pauta.

| Severidad | Cantidad |
| --- | --- |
| Crítica | 2 |
| Alta | 4 |
| Media | 4 |
| Correcto | 8 |

## Hallazgos

| # | Severidad | Hallazgo | Riesgo | Corrección |
| --- | --- | --- | --- | --- |
| H1 | Crítica | `cofrial-sg-app` permite **SSH (22) desde 0.0.0.0/0** | Fuerza bruta y explotación de SSH desde cualquier lugar del mundo | Eliminar la regla y administrar con Session Manager |
| H2 | Crítica | `cofrial-app-server` está en `cofrial-pub-a` con **IP pública 13.220.218.234** y recibe HTTP 80 directo | El servidor queda expuesto; no hay balanceador ni segunda zona | Servidores en `cofrial-app-a` y `cofrial-app-b` sin IP pública, detrás del ALB |
| H3 | Alta | **No hay RDS**: PostgreSQL corre en `cofrial-db-server` (EC2) | Sin respaldos automáticos, parches gestionados ni réplica; la pauta exige RDS | Crear RDS PostgreSQL 16 cifrado en `cofrial-db-subnets` |
| H4 | Alta | Solo **HTTP 80**, sin TLS | Credenciales y sesiones viajan en texto claro | HTTPS con Let's Encrypt en el balanceador y redirección 80 → 443 |
| H5 | Alta | Discos EBS **sin cifrar** | Datos legibles si se copia un snapshot | Discos nuevos cifrados con KMS |
| H6 | Alta | Instancias **sin perfil IAM** (`LabInstanceProfile`) | Sin Session Manager ni Secrets Manager: los secretos quedan en archivos | Asignar `LabInstanceProfile` |
| H7 | Media | `cofrial-sg-db` permite SSH desde `cofrial-sg-app` | Si se compromete la app, se salta a la base de datos | Desaparece al pasar a RDS |
| H8 | Media | `cofrial-iot-a` no tiene tabla de rutas propia (usa la principal, sin NAT) | El nodo IoT no puede descargar imágenes ni paquetes | Asociarla a `cofrial-rtb-private1-us-east-1a` |
| H9 | Media | Sin NACL propia en datos (solo la por defecto, que permite todo) | Falta una capa de defensa en profundidad | Crear `cofrial-nacl-datos` (guía, Fase 1.6) |
| H10 | Media | Sin secretos en Secrets Manager ni bucket S3 | Secretos en archivos; imágenes no compartidas entre nodos | Crear `cofrial/app`, `cofrial/iot` y el bucket de medios |

## Lo que ya está correcto

- VPC `cofrial-vpc` con el direccionamiento del informe y la convención de nombres.
- 7 subredes: públicas, aplicación y datos en dos zonas, más IoT en la zona a.
- Tabla `cofrial-rtb-db`: las subredes de datos **solo tienen la ruta local**, sin salida a Internet.
- NAT Gateway disponible en `cofrial-pub-a`.
- Endpoint de tipo Gateway hacia S3.
- **IMDSv2 obligatorio** (`HttpTokens = required`) en ambas instancias.
- `cofrial-db-server` sin IP pública y con el puerto 5432 limitado a `cofrial-sg-app`.
- Sistema operativo actualizado: Ubuntu 24.04 LTS (imagen de octubre de 2026).

## Evidencias

- [Subredes, instancias y cifrado de discos](evidencias/01-auditoria/01-subredes-instancias-discos.jpg)
- [Reglas de los Security Groups](evidencias/01-auditoria/02-security-groups.png)
- [Llaves, NACL, endpoint de S3 e imagen del sistema](evidencias/01-auditoria/03-llaves-nacl-endpoint-ami.jpg)

## Cómo repetir la auditoría

En CloudShell (ícono `>_` de la barra superior de la consola):

```bash
aws ec2 describe-security-group-rules --filters Name=group-id,Values=<id-del-grupo> \
  --query 'SecurityGroupRules[].[IsEgress,IpProtocol,FromPort,ToPort,CidrIpv4,ReferencedGroupInfo.GroupId]' --output table
aws ec2 describe-instances --query 'Reservations[].Instances[].[Tags[?Key==`Name`]|[0].Value,PublicIpAddress,MetadataOptions.HttpTokens,IamInstanceProfile.Arn]' --output table
aws ec2 describe-volumes --query 'Volumes[].[VolumeId,Encrypted]' --output table
```

Para la defensa sirve mostrar el "antes y después": esta auditoría, las correcciones y la misma consulta repetida al final.

## Correcciones aplicadas

| Fecha (UTC) | Hallazgo | Cambio | Verificación |
| --- | --- | --- | --- |
| 2026-11-14 00:55 | H1 | Se eliminó la regla SSH 22 desde 0.0.0.0/0 de `cofrial-sg-app` | Prueba TCP desde Internet al puerto 22: **antes ABIERTO, después CERRADO** |
| 2026-11-14 01:00 | H8 | `cofrial-iot-a` asociada a la tabla privada con NAT | `associate-route-table` → `associated` |
| 2026-11-14 01:01 | H2, H7 | Security Groups encadenados: `cofrial-sg-alb` (443/80 desde Internet) → `cofrial-sg-app` (443 solo desde el ALB) → `cofrial-sg-rds` (5432 solo desde app e IoT). Se quitó HTTP 80 público de `cofrial-sg-app` y la salida "todo permitido" de todos los grupos | 11 reglas aplicadas con `True` |
| 2026-11-14 01:03 | H3 | RDS PostgreSQL 16.13 **Multi-AZ**, cifrado, sin acceso público, respaldo de 7 días. Contraseña maestra **generada y guardada por RDS en Secrets Manager** (nadie la conoce) | `create-db-instance` → `MultiAZ = True` |
| 2026-11-14 01:05 | H6, H10 | Secretos `cofrial/app` y `cofrial/iot` con valores aleatorios generados con `openssl rand` directamente en Secrets Manager, sin mostrarse | [captura](evidencias/02-correcciones/03-secretos-generados.png) |
| 2026-11-14 01:06 | H10 | Bucket privado `cofrial-media-605885`: bloqueo de acceso público, cifrado AES-256 y política que rechaza conexiones sin TLS | `get-bucket-encryption` → `AES256` |
| 2026-11-14 01:08 | H2, H5, H6 | 3 servidores nuevos (Amazon Linux 2023): `cofrial-app-a` (10.20.11.219), `cofrial-app-b` (10.20.12.23), `cofrial-iot` (10.20.31.232). Subredes privadas, sin IP pública, disco cifrado, IMDSv2, `LabInstanceProfile`, sin llave SSH | `run-instances` |
| 2026-11-14 01:10 | H2, H3 | `cofrial-app-server` y `cofrial-db-server` **detenidos** (no eliminados) y etiquetados `Estado=reemplazado-auditoria-H2-H3` | `stop-instances` → `stopping` |

Evidencias: [antes](evidencias/02-correcciones/01-ssh-antes-abierto.png) · [después](evidencias/02-correcciones/02-ssh-despues-cerrado.png) · GIF del cambio en la consola: `cofrial_cierre_ssh_sg_app.gif` (en la carpeta de Descargas del equipo de Benjamín).

Prueba usada (desde CloudShell, que está fuera de la VPC):

```bash
timeout 5 bash -c '</dev/tcp/IP_PUBLICA/22' && echo ABIERTO || echo CERRADO
```
