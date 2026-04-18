import json
import urllib.request
import urllib.error
import ssl
from app.recursos.utils import Environment


class WhatsAppService:

    @staticmethod
    def send_message(to: str, message: str) -> dict:
        """
        Envía un mensaje de texto a un número de WhatsApp.
        `to` debe ser el número en formato internacional sin '+': ej. '18091234567'
        """
        phone_id = Environment.get("whatsapp_phone_id")
        token = Environment.get("whatsapp_token")

        url = f"https://graph.facebook.com/v25.0/{phone_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            return {"error": f"HTTP {e.code}: {error_body}"}
        except Exception as e:
            return {"error": str(e)}