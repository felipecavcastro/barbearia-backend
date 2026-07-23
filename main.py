from fastapi import FastAPI
from sqlmodel import SQLModel
from app.database import engine
from app.routers import router as agendamentos_router
from app.routers_barbeiros import router as barbeiros_router
from app.routers_servicos import router as servicos_router  # <-- NOVA IMPORTAÇÃO
from app.routers_whatsapp import router as whatsapp_router

app = FastAPI(title="API da Barbearia")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

# Registrando todos os módulos de rotas do nosso sistema
app.include_router(agendamentos_router)
app.include_router(barbeiros_router)
app.include_router(servicos_router)  # <-- INCLUÍMOS AS ROTAS DE SERVIÇOS DO BANCO
app.include_router(whatsapp_router)

@app.get("/")
def ler_inicio():
    return {"mensagem": "Bem-vindo à API da Barbearia com Preços Dinâmicos!"}
