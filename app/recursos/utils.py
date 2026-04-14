Environment = {
    # Definir el modelo que utilizaremos en la nube
    "modelo": "qwen3.5:cloud",
    
    # Opciones de inferencia
    "ollama_options": {
        "num_predict": 1000,   # Aumentado para permitir que procese su bloque "thinking"
        "top_p": 0.8,
        "num_ctx": 4096
    },
    
    # Proveedor Oficial de Ollama Cloud
    "ollama_url": "https://ollama.com",
    "ollama_api_key": "729756f5e3664c70a01f8ef6befeecab.1CoO5PvIhAxKMzpQQpsw6iy_"
}
