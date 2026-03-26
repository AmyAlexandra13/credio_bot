from pydantic import BaseModel, Field


class ModelRequest(BaseModel):
    prompt: str = Field(..., max_length=1000, description="Pregunta para el asistente, máximo 1000 caracteres.")
