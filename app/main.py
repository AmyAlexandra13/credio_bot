import uvicorn
from fastapi import FastAPI
from app.routers import health, llm, auth

app = FastAPI(title="credio-bot")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(llm.router)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
