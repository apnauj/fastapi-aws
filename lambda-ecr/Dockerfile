# ==========================================
# Fase 1: Build (Instalación de dependencias)
# ==========================================
FROM public.ecr.aws/lambda/python:3.11 AS builder

# Instalar herramientas de compilación por si alguna dependencia lo requiere
RUN pip install --no-cache-dir --upgrade pip

# Copiar solo el archivo de requerimientos para aprovechar la caché de Docker
COPY requirements.txt .

# Instalar dependencias en un directorio específico para luego copiarlo
# --target asegura que todo se instale en una estructura limpia
RUN pip install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# ==========================================
# Fase 2: Runtime (Imagen final ligera)
# ==========================================
FROM public.ecr.aws/lambda/python:3.11

# Definir el directorio de trabajo nativo de AWS Lambda
WORKDIR ${LAMBDA_TASK_ROOT}

# Copiar las dependencias instaladas desde la fase de compilación
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copiar el código de la aplicación (asumiendo que tu archivo se llama app.py)
# Cambia 'app.py' por el nombre real de tu archivo si es diferente
COPY app.py .

# Indicar el "Handler" de la Lambda. 
# Estructura: [nombre_archivo_python].[nombre_variable_mangum]
CMD [ "app.mangum_handler" ]