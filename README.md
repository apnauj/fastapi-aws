# FastAPI en AWS — dos rutas de despliegue

Una misma pregunta, dos respuestas: **¿cómo se pone una API FastAPI a correr en AWS?**
Este repositorio contiene las dos implementaciones que construí para el final de Sistemas
Operativos en la Universidad EIA, cada una con su propio Dockerfile, su propio modelo de
ejecución y sus propios compromisos.

| | [`lambda-ecr/`](lambda-ecr) | [`ec2-docker-s3/`](ec2-docker-s3) |
|---|---|---|
| **Modelo** | Serverless | Servidor siempre encendido |
| **Cómputo** | AWS Lambda (imagen de contenedor) | EC2 + Docker + systemd |
| **Registro** | Amazon ECR | Imagen construida en la instancia |
| **Adaptador** | Mangum (ASGI → evento Lambda) | Uvicorn, 4 workers |
| **Estado** | Ninguno | Amazon S3 |
| **Escala a cero** | Sí | No |
| **Arranque en frío** | Sí | No |

---

## `lambda-ecr/` — FastAPI dentro de Lambda

Lambda no habla HTTP con la aplicación: le entrega un evento JSON. **Mangum** es el
adaptador que traduce ese evento a una petición ASGI y la respuesta de vuelta, lo que
permite correr una app FastAPI normal sin cambiarle una línea.

El `Dockerfile` es multi-etapa sobre `public.ecr.aws/lambda/python:3.11`: la primera etapa
instala las dependencias en `${LAMBDA_TASK_ROOT}` y la segunda solo las copia, de modo que
las herramientas de compilación no terminan en la imagen final. El `CMD` no es un comando
sino el *handler*: `app.mangum_handler`.

### Desplegar

```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1          # opcional, este es el valor por defecto
export ECR_REPO_NAME=mi-repositorio  # opcional

./deploy.sh
```

El script construye, etiqueta, autentica contra ECR y sube la imagen. Un detalle que costó
encontrar: hay que pasar `--provenance=false --output type=docker` a `docker buildx`,
porque Lambda rechaza las imágenes que traen los metadatos OCI y las *attestations* que
buildx añade por defecto.

Después, en la consola de AWS, se crea la función Lambda a partir de esa imagen.

---

## `ec2-docker-s3/` — FastAPI como servicio en una instancia

Una API de gestión de imágenes que las guarda en **S3** y devuelve **URLs prefirmadas**
para leerlas: el bucket nunca se expone públicamente, y cada enlace caduca solo.

- `POST /images/upload` — sube una imagen (`jpeg`/`jpg`/`png`) bajo la clave
  `{usuario}/{nombre}`.
- `GET /images/{usuario}/{nombre}` — devuelve la fecha de almacenamiento que reporta S3 y
  una URL prefirmada temporal.

Los esquemas de entrada y salida están tipados con **Pydantic**, así que la documentación
de OpenAPI en `/docs` sale con los ejemplos correctos sin escribirla aparte.

### Correr localmente

```bash
docker build -t fastapi-s3 .
docker run -p 8000:8000 \
  -e AWS_S3_BUCKET_NAME=mi-bucket \
  -e AWS_REGION=us-east-1 \
  fastapi-s3
```

### Correr como servicio en EC2

El contenedor por sí solo no sobrevive a un reinicio de la máquina. `fastapi_docker.service`
delega el ciclo de vida a **systemd**, que lo levanta al arrancar y lo reinicia si se cae:

```bash
sudo cp fastapi-docker.env.example /etc/fastapi-docker.env   # y editarlo
sudo cp fastapi_docker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fastapi_docker
```

Las credenciales no van en el archivo de entorno: la instancia usa un **IAM role**, y
`boto3` lo toma del metadata service automáticamente.

---

## Decisiones

- **Mangum en vez de reescribir la app.** El objetivo era comparar modelos de despliegue,
  no modelos de programación, así que la aplicación debía poder ser la misma.
- **URLs prefirmadas en vez de un bucket público.** Cuesta lo mismo implementarlo y no
  deja el almacenamiento abierto.
- **systemd en vez de `docker run --restart always`.** Con systemd el servicio queda
  integrado a `journalctl` y al arranque de la máquina, y el estado se consulta con las
  mismas herramientas que cualquier otro servicio del sistema.

## Limitaciones conocidas

- No hay pruebas automatizadas; la verificación fue manual contra los endpoints.
- El despliegue de la Lambda se termina a mano en la consola de AWS: `deploy.sh` solo
  llega hasta subir la imagen a ECR.
- No hay infraestructura como código. Con más tiempo, esto sería Terraform o AWS SAM.

---

*Universidad EIA — Sistemas Operativos, 2026. Fusiona los repositorios `FinalSO_1` y
`FinalSO_2`, hoy archivados.*
