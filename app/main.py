from fastapi import FastAPI
from app.routers import health

app = FastAPI(title="credio-bot")

app.include_router(health.router)
