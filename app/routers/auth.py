from fastapi import APIRouter
import secrets

router = APIRouter(prefix="/auth", tags=["auth"])

# Almacén temporal en memoria para validar tokens dinámicos
VALID_TOKENS = set()
VALID_TOKENS.add("super-secreto-123")

@router.get("/generate-token")
def generate_token():
    token = secrets.token_hex(16)
    VALID_TOKENS.add(token)
    return {
        "token": token, 
        "message": "Envíe este token en la cabecera 'x-token' para hacer consultas al bot."
    }
