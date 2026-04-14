import json
import urllib.request
import urllib.error
import ssl
from app.recursos.utils import Environment
class OllamaService:
    @staticmethod
    def generate_text_stream(prompt: str, model: str = None, system: str = None):
        base_url = Environment.get("ollama_url", "http://localhost:11434")
        actual_model = model or Environment.get("ollama_model", "qwen3.5:cloud")
        url = f"{base_url}/api/generate"
        data = {
            "model": actual_model,
            "prompt": prompt,
            "stream": True
        }
        
        if system:
            data["system"] = system
            
        headers = {'Content-Type': 'application/json'}
        api_key = Environment.get("ollama_api_key")
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
            
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers=headers
        )
        
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, context=ctx) as response:
                for line in response:
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        yield chunk.get("response", "")
        except urllib.error.URLError as e:
            yield f"Error de conexión con Ollama. Detalles: {str(e)}"
        except Exception as e:
            yield f"Error inesperado: {str(e)}"

    @staticmethod
    def generate_text(prompt: str, model: str = None, system: str = None, options: dict = None) -> str:
        base_url = Environment.get("ollama_url", "http://localhost:11434")
        actual_model = model or Environment.get("ollama_model", "qwen3.5:cloud")
        url = f"{base_url}/api/generate"
        data = {
            "model": actual_model,
            "prompt": prompt,
            "stream": False
        }
        
        if system:
            data["system"] = system
            
        if options:
            data["options"] = options
            
        headers = {'Content-Type': 'application/json'}
        api_key = Environment.get("ollama_api_key")
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
            
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers=headers
        )
        
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, context=ctx) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('response', '')
        except urllib.error.URLError as e:
            return f"Error de conexión con Ollama. Detalles: {str(e)}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"

    @staticmethod
    def chat(messages: list, model: str = None, options: dict = None) -> str:
        """
        Hace una petición de chat multi-turno a Ollama para mantener un historial.
        """
        base_url = Environment.get("ollama_url", "http://localhost:11434")
        actual_model = model or Environment.get("ollama_model", "qwen3.5:cloud")
        url = f"{base_url}/api/chat"
        data = {
            "model": actual_model,
            "messages": messages,
            "stream": False
        }
        
        if options:
            data["options"] = options
            
        headers = {'Content-Type': 'application/json'}
        api_key = Environment.get("ollama_api_key")
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
            
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers=headers
        )
        
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, context=ctx) as response:
                result = json.loads(response.read().decode('utf-8'))
                # En /api/chat la respuesta viene en iterado ['message']['content']
                return result.get('message', {}).get('content', '')
        except urllib.error.URLError as e:
            if hasattr(e, 'read'):
                return f"Error de conexión con Ollama. HTTP Status: {e.code}. Detalles: {e.read().decode('utf-8')}"
            return f"Error de conexión con Ollama. Detalles: {str(e)}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"
