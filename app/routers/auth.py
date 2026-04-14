from fastapi import APIRouter
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

# Almacén temporal en memoria para validar tokens dinámicos y su expiración
VALID_TOKENS = {}
VALID_TOKENS["super-secreto-123"] = datetime.max

@router.get("/generate-token")
def generate_token():
    token = secrets.token_hex(16)
    # Define la duración de vida del token (1 hora)
    expiration = datetime.now() + timedelta(hours=1)
    VALID_TOKENS[token] = expiration
    
    return {
        "token": token, 
        "expires_in": 3600,
        "message": "Envíe este token como 'Bearer Token' (Authorization: Bearer <token>) para hacer consultas al bot."
    }
