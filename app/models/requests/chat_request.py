from pydantic import BaseModel, Field


class ChatConversationRequest(BaseModel):
    session_id: str = Field(..., description="ID único para la sesión del usuario (ejemplo: 'usuario-123')")
    prompt: str = Field(..., max_length=1000, description="Pregunta para el asistente, máximo 1000 caracteres.")
