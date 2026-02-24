# Credio Bot

Proyecto FastAPI profesional siguiendo principios SOLID.

## Requisitos

- Python 3.11+
- pip (gestor de paquetes de Python)

## Instalación

1. Clona el repositorio o descarga el código.
2. Navega a la raíz del proyecto:
   ```bash
   cd credio-bot
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Ejecución

Para iniciar el servidor de desarrollo:

```bash
uvicorn app.main:app --reload
```

El servidor estará disponible en: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Endpoints

- **GET /health**: Verifica el estado de la aplicación.
  - Respuesta esperada:
    ```json
    {
      "status": "ok",
      "app": "credio-bot"
    }
    ```
