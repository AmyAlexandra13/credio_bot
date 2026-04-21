"""
Router de WhatsApp — Chatbot conversacional SGCC / Credio
---------------------------------------------------------
Estados por sesión (SESSIONS[numero]):
  - "menu"              → Mostrando menú inicial
  - "sgcc_chat"         → Preguntas sobre el documento SGCC
  - "awaiting_id"       → Esperando cédula para consultar pagos
  - "awaiting_id_status"→ Esperando cédula para consultar estado de solicitudes
"""

import os
import traceback
from functools import lru_cache
from pypdf import PdfReader
from fastapi import APIRouter, Request, HTTPException, Query
from app.services.whatsapp_service import WhatsAppService
from app.services.ollama_service import OllamaService
from app.services.lending_service import LendingService
from app.recursos.utils import Environment

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# ── Estado de conversaciones en memoria ──────────────────────────────────────
# { numero: { "state": str, "history": list, "name": str } }
SESSIONS: dict[str, dict] = {}

# ── Textos del bot ────────────────────────────────────────────────────────────
WELCOME_MESSAGE = (
    "👋 ¡Hola{name}! Bienvenido al asistente virtual del *SGCC*\n"
    "_(Sistema Integral de Gestión de Créditos y Cobranza)_\n\n"
    "¿En qué puedo ayudarte hoy? Elige una opción:\n\n"
    "  *1* — Consultar información sobre el proyecto SGCC\n"
    "  *2* — Ver mis próximos pagos\n"
    "  *3* — Ver el estado de mis solicitudes\n\n"
    "Responde con el número de la opción. 😊"
)

MENU_REMINDER = (
    "Elige una opción para continuar:\n\n"
    "  *1* — Consultar información sobre el proyecto SGCC\n"
    "  *2* — Ver mis próximos pagos\n"
    "  *3* — Ver el estado de mis solicitudes\n\n"
    "_(Escribe *menu* en cualquier momento para volver aquí)_"
)

SGCC_INTRO = (
    "📄 *Modo: Información del SGCC*\n\n"
    "Puedes hacerme cualquier pregunta sobre el proyecto. "
    "Responderé únicamente basándome en la documentación oficial.\n\n"
    "_(Escribe *menu* para volver al inicio)_"
)

ASK_IDENTITY_PAYMENTS = (
    "🔍 *Consulta de pagos*\n\n"
    "Por favor, escribe tu *número de cédula o documento de identidad* "
    "para buscar tus préstamos activos.\n\n"
    "_(Escribe *menu* para cancelar)_"
)

ASK_IDENTITY_STATUS = (
    "📋 *Consulta de solicitudes*\n\n"
    "Por favor, escribe tu *número de cédula o documento de identidad* "
    "para ver el estado de tus solicitudes recientes.\n\n"
    "_(Escribe *menu* para cancelar)_"
)

ERROR_AUTH = (
    "❌ Ocurrió un problema al conectar con nuestro sistema. "
    "Por favor intenta más tarde o comunícate con tu asesor."
)

ERROR_PAYMENTS = (
    "⚠️ No pude obtener información de pagos para ese documento. "
    "Verifica que el número sea correcto o comunícate con tu asesor."
)

ERROR_STATUS = (
    "⚠️ No pude obtener el estado de solicitudes para ese documento. "
    "Verifica que el número sea correcto o comunícate con tu asesor."
)

INVALID_DOC = (
    "⚠️ El número de documento no parece válido. "
    "Por favor ingresa solo los dígitos de tu cédula.\n\n"
    "_(Escribe *menu* para cancelar)_"
)


# ── Carga del PDF (cacheada) ──────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _get_pdf_context() -> str:
    pdf_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "documento_proyecto.pdf"
    )
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
        print(f"[WhatsApp] Error cargando PDF: {e}")
        return "Ocurrió un error al leer el documento del proyecto."


# ── System prompt SGCC ────────────────────────────────────────────────────────
def _sgcc_system_prompt() -> str:
    pdf_content = _get_pdf_context()
    return (
        "Eres un asistente virtual del proyecto SGCC (Sistema Integral de Gestión de Créditos y Cobranza). "
        "Tu ÚNICO propósito es responder basándote ESTRICTAMENTE en el siguiente documento:\n\n"
        "--- INICIO DEL DOCUMENTO (SGCC) ---\n"
        f"{pdf_content}\n"
        "--- FIN DEL DOCUMENTO ---\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "1. Si la pregunta no está respondida en el documento, responde EXACTAMENTE: "
        "\"Lo siento, no puedo contestar esa pregunta. Solo hablo sobre los detalles especificados en el documento del SGCC.\"\n"
        "2. Responde siempre en español, MUY BREVE y DIRECTO (máximo 2 oraciones).\n"
        "3. No uses markdown con asteriscos ni guiones bajos. Responde en texto plano.\n"
        "4. No salgas del contexto del documento bajo ninguna circunstancia."
    )


# ── Helpers ───────────────────────────────────────────────────────────────────
def _welcome(name: str = "") -> str:
    name_str = f", *{name}*" if name else ""
    return WELCOME_MESSAGE.format(name=name_str)


def _get_or_create_session(number: str, name: str = "") -> dict:
    if number not in SESSIONS:
        SESSIONS[number] = {"state": "menu", "history": [], "name": name or ""}
    return SESSIONS[number]


def _validate_document(text: str) -> str | None:
    """Limpia y valida el número de documento. Retorna el número limpio o None."""
    identity = text.replace("-", "").replace(" ", "")
    if identity.isdigit() and 7 <= len(identity) <= 15:
        return identity
    return None


def _auth_or_error(session: dict) -> tuple[str | None, str | None]:
    """
    Autentica contra el API. Retorna (token, None) si éxito
    o (None, mensaje_error) si falla.
    """
    token = LendingService.authenticate()
    if not token:
        session["state"] = "menu"
        return None, f"{ERROR_AUTH}\n\n{MENU_REMINDER}"
    return token, None


# ── Procesador principal ──────────────────────────────────────────────────────
def process_message(number: str, body: str, profile_name: str = "") -> str:
    text = body.strip()
    text_lower = text.lower()

    session = _get_or_create_session(number, profile_name)
    state = session["state"]

    # Comando global: volver al menú
    if text_lower in ("menu", "menú", "inicio", "start", "hola", "hi", "buenas", "hello"):
        session["state"] = "menu"
        session["history"] = []
        return _welcome(session["name"])

    # ── Menú principal ────────────────────────────────────────────────────────
    if state == "menu":
        if text == "1":
            session["state"] = "sgcc_chat"
            session["history"] = [{"role": "system", "content": _sgcc_system_prompt()}]
            return SGCC_INTRO
        elif text == "2":
            session["state"] = "awaiting_id"
            return ASK_IDENTITY_PAYMENTS
        elif text == "3":
            session["state"] = "awaiting_id_status"
            return ASK_IDENTITY_STATUS
        else:
            return _welcome(session["name"])

    # ── Chat sobre SGCC ───────────────────────────────────────────────────────
    elif state == "sgcc_chat":
        history = session["history"]
        history.append({"role": "user", "content": text})

        modelo = Environment.get("ollama_model", "qwen3.5:cloud")
        options = Environment.get("ollama_options", {})
        response_text = OllamaService.chat(history, model=modelo, options=options)

        if response_text.startswith("Error"):
            history.pop()
            return "❌ Ocurrió un error al procesar tu consulta. Por favor intenta de nuevo."

        history.append({"role": "assistant", "content": response_text})
        return f"{response_text}\n\n_(Escribe *menu* para volver al inicio)_"

    # ── Esperando cédula → consulta de pagos ─────────────────────────────────
    elif state == "awaiting_id":
        identity = _validate_document(text)
        if not identity:
            return INVALID_DOC

        token, err = _auth_or_error(session)
        if err:
            return err

        payments_data = LendingService.get_payments_summary(identity, token)
        if payments_data is None:
            session["state"] = "menu"
            return f"{ERROR_PAYMENTS}\n\n{MENU_REMINDER}"

        payments_msg = LendingService.format_payments_message(payments_data)
        session["state"] = "menu"

        return (
            f"Resumen de pagos para documento: {text}\n\n"
            f"{payments_msg}\n\n"
            "─────────────────────\n"
            f"{MENU_REMINDER}"
        )

    # ── Esperando cédula → estado de solicitudes ──────────────────────────────
    elif state == "awaiting_id_status":
        identity = _validate_document(text)
        if not identity:
            return INVALID_DOC

        token, err = _auth_or_error(session)
        if err:
            return err

        status_data = LendingService.get_application_status(identity, token)
        if status_data is None:
            session["state"] = "menu"
            return f"{ERROR_STATUS}\n\n{MENU_REMINDER}"

        status_msg = LendingService.format_application_status_message(status_data)
        session["state"] = "menu"

        return (
            f"Estado de solicitudes para documento: {text}\n\n"
            f"{status_msg}\n\n"
            "─────────────────────\n"
            f"{MENU_REMINDER}"
        )

    # ── Fallback ──────────────────────────────────────────────────────────────
    session["state"] = "menu"
    return _welcome(session["name"])


# ── GET: verificación del webhook (Meta) ──────────────────────────────────────
@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    verify_token = Environment.get("whatsapp_verify_token", "")
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        print("[WhatsApp] Webhook verificado correctamente.")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


# ── POST: recibir mensajes ────────────────────────────────────────────────────
@router.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    print("📩 PAYLOAD RECIBIDO:", body)

    try:
        entry = body["entry"][0]
        change = entry["changes"][0]["value"]

        # Meta envía notificaciones de status de entrega sin "messages"
        if "messages" not in change:
            print("⚠️ Notificación sin mensaje (status update), ignorando.")
            return {"status": "ignored"}

        message = change["messages"][0]
        from_number: str = message["from"]
        msg_type: str = message.get("type", "")
        profile_name: str = (
            change.get("contacts", [{}])[0].get("profile", {}).get("name", "")
        )

        print(f"👤 Número: {from_number} | Nombre: {profile_name} | Tipo: {msg_type}")

        if msg_type != "text":
            WhatsAppService.send_message(
                from_number,
                "Solo proceso mensajes de texto por el momento. 😊\n\nEscribe *menu* para ver las opciones."
            )
            return {"status": "ok"}

        user_text: str = message["text"]["body"]
        print(f"💬 Mensaje: {user_text!r}")

        reply = process_message(from_number, user_text, profile_name)
        print(f"🤖 Respuesta: {reply!r}")

        result = WhatsAppService.send_message(from_number, reply)
        print(f"📤 Resultado envío: {result}")

        return {"status": "ok"}

    except (KeyError, IndexError) as e:
        print(f"❌ Error parseando payload: {e}")
        return {"status": "error", "detail": str(e)}
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        traceback.print_exc()
        return {"status": "error", "detail": str(e)}