from mangum import Mangum
from fastapi import FastAPI

fastapi = FastAPI(title="Ejemplo FastAPI + Mangum")
mangum_handler = Mangum(fastapi)

@fastapi.get("/")
def root():
    return {"message": "API funcionando correctamente."}

@fastapi.get("/api/hello")
def say_hello(name: str = "Mendez"):
    return {"message": f"Hola, {name}! Bienvenido a FastAPI en Lambda."}

