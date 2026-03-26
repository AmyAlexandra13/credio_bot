import json
import urllib.request
import urllib.error
from app.recursos.utils import Environment
class OllamaService:
    @staticmethod
    @staticmethod
    def generate_text_stream(prompt: str, model: str = "llama3:8b", system: str = None):
        base_url = Environment.get("ollama_url", "http://localhost:11434")
        url = f"{base_url}/api/generate"
        data = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        
        if system:
            data["system"] = system
            
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                for line in response:
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        yield chunk.get("response", "")
        except urllib.error.URLError as e:
            yield f"Error de conexión con Ollama. Detalles: {str(e)}"
        except Exception as e:
            yield f"Error inesperado: {str(e)}"

    @staticmethod
    def generate_text(prompt: str, model: str = "llama3:8b", system: str = None, options: dict = None) -> str:
        base_url = Environment.get("ollama_url", "http://localhost:11434")
        url = f"{base_url}/api/generate"
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        if system:
            data["system"] = system
            
        if options:
            data["options"] = options
            
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('response', '')
        except urllib.error.URLError as e:
            return f"Error de conexión con Ollama. Detalles: {str(e)}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"

    @staticmethod
    def chat(messages: list, model: str = "llama3.2:1b", options: dict = None) -> str:
        """
        Hace una petición de chat multi-turno a Ollama para mantener un historial.
        """
        base_url = Environment.get("ollama_url", "http://localhost:11434")
        url = f"{base_url}/api/chat"
        data = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        if options:
            data["options"] = options
            
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                # En /api/chat la respuesta viene en iterado ['message']['content']
                return result.get('message', {}).get('content', '')
        except urllib.error.URLError as e:
            return f"Error de conexión con Ollama. Detalles: {str(e)}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"
