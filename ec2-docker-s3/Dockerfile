# 1. Usar una imagen base de Python ligera y optimizada para producción
FROM python:3.11-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar primero el archivo de dependencias para aprovechar la caché de Docker
COPY requirements.txt .

# 4. Instalar las dependencias sin guardar caché de pip (reduce el tamaño de la imagen)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copiar el resto del código de la aplicación al contenedor
COPY . .

# 6. Exponer el puerto en el que correrá Uvicorn dentro del contenedor
EXPOSE 8000

# 7. Comando para ejecutar la API (Uvicorn)
# Usamos 0.0.0.0 para que acepte conexiones externas al contenedor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]