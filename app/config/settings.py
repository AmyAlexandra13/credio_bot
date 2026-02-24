from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "credio-bot"

settings = Settings()
