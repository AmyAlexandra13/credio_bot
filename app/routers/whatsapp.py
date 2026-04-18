from fastapi import APIRouter, Request, HTTPException, Query
from app.services.whatsapp_service import WhatsAppService
from app.services.ollama_service import OllamaService
from app.recursos.utils import Environment
import os
from functools import lru_cache
from pypdf import PdfReader

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# Historial de conversaciones por número de teléfono
CONVERSATIONS = {}


@lru_cache(maxsize=1)
def get_pdf_context() -> str:
    pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "documento_proyecto.pdf")
    if not os.path.exists(pdf_path):
        return "El documento del proyecto no se encontró."
    try:
        reader = PdfReader(pdf_path)
        text = "".join(
            page.extract_text() + "\n"
            for page in reader.pages if page.extract_text()
        )
        return text[:1500].strip()
    except Exception as e:
        return f"Error al leer el documento: {e}"


def build_system_prompt() -> str:
    pdf_content = get_pdf_context()
    return f"""Eres un asistente virtual experto cuyo ÚNICO propósito es responder basándote 
ESTRICTAMENTE en el siguiente documento del proyecto:

--- INICIO DEL DOCUMENTO (SGCC) ---
{pdf_content}
--- FIN DEL DOCUMENTO ---

Regla Estricta 1: Si la pregunta no está en el documento, responde EXACTAMENTE:
"Lo siento, no puedo contestar esa pregunta. Solo hablo sobre el SGCC."

Regla Estricta 2: Responde de manera MUY BREVE (máximo 2 oraciones).
"""


# ─── WEBHOOK VERIFICATION (GET) ───────────────────────────────────────────────
@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta llama a este endpoint para verificar el webhook."""
    verify_token = Environment.get("whatsapp_verify_token", "")

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return int(hub_challenge)  # Responde con el challenge para confirmar

    raise HTTPException(status_code=403, detail="Token de verificación inválido")


# ─── RECIBIR MENSAJES (POST) ───────────────────────────────────────────────────
@router.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    print("📩 PAYLOAD RECIBIDO:", body)

    try:
        entry = body["entry"][0]
        change = entry["changes"][0]["value"]

        if "messages" not in change:
            print("⚠️ No hay mensajes en el payload")
            return {"status": "ignored"}

        message = change["messages"][0]
        from_number = message["from"]
        msg_type = message.get("type", "")

        print("👤 Número:", from_number)
        print("💬 Tipo:", msg_type)

        if msg_type != "text":
            WhatsAppService.send_message(from_number, "Solo proceso texto 😊")
            return {"status": "ok"}

        user_text = message["text"]["body"].strip()
        print("💬 Mensaje:", user_text)

        bot_response = OllamaService.chat(
            CONVERSATIONS.get(from_number, [{"role": "user", "content": user_text}]),
            model=Environment.get("ollama_model"),
            options=Environment.get("ollama_options", {})
        )

        print("🤖 Respuesta bot:", bot_response)

        result = WhatsAppService.send_message(from_number, bot_response)
        print("📤 Resultado envío:", result)

        return {"status": "ok"}

    except Exception as e:
        print("❌ ERROR:", str(e))
        return {"status": "error"}