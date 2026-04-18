import uvicorn
from fastapi import FastAPI
from app.routers import health, llm, auth, whatsapp

app = FastAPI(title="credio-bot")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(llm.router)
app.include_router(whatsapp.router)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
