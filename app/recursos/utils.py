Environment = {
    # Definir el modelo más ligero posible para respuestas rápidas
    "modelo": "llama3.2:1b",
    
    # Opciones optimizadas de Ollama para acelerar tiempo de inferencia
    "ollama_options": {
        "num_predict": 100,    # Límite muy estricto de palabras a generar (< 2 oraciones)
        "temperature": 0.0,    # 0.0 hace que no tenga que "deliberar" creatividad y responda inmediato
        "top_p": 0.5,
        "num_ctx": 2048,       # Corta el límite de memoria del modelo para alivianar CPU/GPU
        "num_thread": 8        # Fuerza el uso multihilo de la CPU (muy útil si no tienes GPU dedicada)
    },
    
    "ollama_url": "http://localhost:11434"
}
