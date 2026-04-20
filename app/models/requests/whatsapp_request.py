from pydantic import BaseModel
from typing import Optional


class WhatsAppIncomingMessage(BaseModel):
    """
    Modelo genérico para recibir mensajes entrantes desde el webhook de WhatsApp.
    Adaptar según el proveedor (Twilio, Meta Cloud API, etc.)
    """
    from_number: str          # Número del remitente, ej: "whatsapp:+18095551234"
    body: str                  # Texto del mensaje
    profile_name: Optional[str] = None  # Nombre del perfil (si el proveedor lo envía)