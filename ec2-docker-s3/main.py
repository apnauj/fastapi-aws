import os
from datetime import datetime
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="S3 Image Management API",
    description="API profesional para cargar y gestionar imágenes de usuarios en AWS S3 usando Pydantic.",
    version="1.1.0"
)

# Configuración de AWS
BUCKET_NAME = os.environ["AWS_S3_BUCKET_NAME"]
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Inicializar el cliente de S3
s3_client = boto3.client('s3', region_name=AWS_REGION)

# Formatos permitidos
ALLOWED_EXTENSIONS = {"image/jpeg", "image/jpg", "image/png"}


# --- MODELOS DE PYDANTIC (Esquemas de Respuesta) ---

class UploadImageResponse(BaseModel): 
    message: str = Field(..., example="Imagen subida exitosamente")
    user: str = Field(..., example="juan_perez")
    s3_key: str = Field(..., example="juan_perez/foto_perfil.png")


class RetrieveImageResponse(BaseModel):
    username: str = Field(..., example="juan_perez")
    image_name: str = Field(..., example="foto_perfil.png")
    storage_date: datetime = Field(..., description="Fecha de almacenamiento en formato ISO obtenido de S3")
    presigned_url: str = Field(..., description="URL prefirmada temporal de AWS S3 para acceder al recurso")


# --- ENDPOINTS ---

@app.post(
    "/images/upload", 
    status_code=status.HTTP_201_CREATED,
    response_model=UploadImageResponse,
    summary="Subir imagen de usuario",
    tags=["Imágenes"]
)
async def upload_image(
    username: str = Form(..., description="Nombre del usuario"),
    file: UploadFile = File(..., description="Imagen en formato PNG o JPG/JPEG")
):
    """
    Sube una imagen directamente a un bucket de AWS S3 estructurado por carpetas de usuario (`username/filename`).
    """
    # 1. Validar formato de archivo
    if file.content_type not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Formato de archivo no permitido. Tipos aceptados: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Sanitizar strings para evitar problemas de rutas en S3
    sanitized_username = username.strip().replace(" ", "_").lower()
    filename = file.filename.replace(" ", "_")
    s3_key = f"{sanitized_username}/{filename}"
    
    try:
        # 2. Upload eficiente usando streams de memoria directo a S3
        s3_client.upload_fileobj(
            Fileobj=file.file,
            Bucket=BUCKET_NAME,
            Key=s3_key,
            ExtraArgs={"ContentType": file.content_type}
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en AWS S3: {e.response['Error']['Message']}"
        )
    finally:
        await file.close()

    # El diccionario retornado se valida automáticamente contra el modelo 'UploadImageResponse'
    return {
        "message": "Imagen subida exitosamente",
        "user": sanitized_username,
        "s3_key": s3_key
    }


@app.get(
    "/images/retrieve", 
    response_model=RetrieveImageResponse,
    summary="Obtener URL e información de una imagen",
    tags=["Imágenes"]
)
async def get_image_url(
    username: str,
    image_name: str
):
    """
    Verifica la existencia del archivo en el bucket S3, extrae su fecha de modificación original
    y genera una URL prefirmada segura válida por 1 hora.
    """
    sanitized_username = username.strip().replace(" ", "_").lower()
    s3_key = f"{sanitized_username}/{image_name}"
    
    try:
        # 1. HeadObject para verificar existencia rápida y obtener metadata
        metadata = s3_client.head_object(Bucket=BUCKET_NAME, Key=s3_key)
        last_modified = metadata['LastModified']
        
        # 2. Generar URL prefirmada (Expira en 1 hora)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600
        )
        
    except ClientError as e:
        # Captura el error específico si el objeto o la "carpeta" de usuario no existen
        if e.response['Error']['Code'] == "404":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la imagen '{image_name}' asociada al usuario '{sanitized_username}'."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al conectar con S3: {e.response['Error']['Message']}"
        )
        
    # Pydantic se encarga de serializar el objeto 'datetime' de AWS a un string ISO 8601 estándar automáticamente
    return {
        "username": sanitized_username,
        "image_name": image_name,
        "storage_date": last_modified,
        "presigned_url": presigned_url
    }