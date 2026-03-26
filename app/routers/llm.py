import os
from functools import lru_cache
from pypdf import PdfReader
from fastapi import APIRouter, HTTPException, Depends, Header
from app.services.ollama_service import OllamaService
from app.models.requests.prompt_request import PromptRequest
from app.models.requests.model_request import ModelRequest
from app.models.requests.chat_request import ChatConversationRequest
from app.routers.auth import VALID_TOKENS
from app.recursos.utils import Environment

router = APIRouter(prefix="/llm", tags=["llm"])

# Diccionario en memoria para almacenar los historiales de conversación
CONVERSATIONS = {}


@lru_cache(maxsize=1)
def get_pdf_context() -> str:
    pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "documento_proyecto.pdf")

    if not os.path.exists(pdf_path):
        return "El documento del proyecto no se encontró en la raíz."

    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"

        return text[:1500].strip()
    except Exception as e:
        print(f"Error cargando el PDF: {e}")
        return "Ocurrió un error al leer el documento del proyecto."


def verify_token(x_token: str = Header(..., description="Token de autenticación generable")):
    if x_token not in VALID_TOKENS:
        raise HTTPException(status_code=401, detail="Token inválido o no proporcionado")
    return x_token


@router.post("/ask")
def ask_ollama(request: PromptRequest):
    response = OllamaService.generate_text(request.prompt)

    if response.startswith("Error"):
        raise HTTPException(status_code=500, detail=response)

    return {"model": "llama3:8b", "response": response}


# TODO -> Conectar al pdf del resumen ejecutivo del proyecto para que no salga del scope

@router.post("/chat/sgcc")
def ask_sgcc(request: ModelRequest):
    system_prompt = """Eres un asistente virtual experto cuyo ÚNICO propósito es proveer información sobre el siguiente proyecto:

Proyecto: Sistema Integral de Gestión de Créditos y Cobranza (SGCC)
Descripción: El proyecto consiste en una plataforma web centralizada para la gestión del ciclo de vida de préstamos. El sistema automatiza el cálculo financiero, la generación de documentos legales y controla la cobranza en campo. Se integrará hardware de impresión térmica para entrega de recibos físicos y un asistente virtual básico para consultas rápidas, elevando el nivel de servicio al cliente y la profesionalización del cobro.

Regla Estricta:
Si el usuario hace cualquier pregunta que no esté relacionada con el SGCC, debes responder DE FORMA EXACTA con el siguiente mensaje y no dar más información:
"Lo siento, no puedo contestar a su pregunta. Sin embargo, puedo hablarle sobre el Sistema Integral de Gestión de Créditos y Cobranza (SGCC)."

OBLIGATORIO: Responde siempre de manera EXTREMADAMENTE BREVE y CONCISA (máximo 2 oraciones).
"""

    options = {
        "num_predict": 100
    }

    response = OllamaService.generate_text(request.prompt, system=system_prompt, options=options)

    if response.startswith("Error"):
        raise HTTPException(status_code=500, detail=response)

    return {"model": "llama3:8b", "response": response}


@router.post("/chat-sgcc-2")
def ask_sgcc_v2(request: ChatConversationRequest):
    pdf_content = get_pdf_context()

    system_prompt = f"""Eres un asistente virtual experto cuyo ÚNICO propósito es responder basándote ESTRICTAMENTE en el siguiente documento del proyecto:

--- INICIO DEL DOCUMENTO (SGCC) ---
{pdf_content}
--- FIN DEL DOCUMENTO ---

Regla Estricta 1:
Si el usuario hace CUALQUIER pregunta que no esté respondida explícitamente en el texto anterior, debes responder de manera INMEDIATA Y EXACTA con el siguiente mensaje:
"Lo siento, no puedo contestar a esa pregunta. Sólo hablo sobre los detalles especificados en el documento del Sistema Integral de Gestión de Créditos y Cobranza (SGCC)."
NO intentes adivinar ni dar información general fuera del documento. OBLIGATORIO acatar esta regla.

Regla Estricta 2:
OBLIGATORIO: Responde de manera MUY BREVE y DIRECTA (máximo 2 oraciones).
"""

    modelo = Environment["modelo"]
    options = Environment["ollama_options"]

    if request.session_id not in CONVERSATIONS:
        CONVERSATIONS[request.session_id] = [
            {"role": "system", "content": system_prompt}
        ]

    messages = CONVERSATIONS[request.session_id]
    messages.append({"role": "user", "content": request.prompt})

    response_text = OllamaService.chat(messages, model=modelo, options=options)

    if response_text.startswith("Error"):
        messages.pop()
        raise HTTPException(status_code=500, detail=response_text)

    messages.append({"role": "assistant", "content": response_text})

    return {
        "model": modelo,
        "session_id": request.session_id,
        "response": response_text
    }
