from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List

from app.database import obter_sessao
from app.models import Servico

router = APIRouter(prefix="/servicos", tags=["Serviços e Preços"])

# Rota para cadastrar um novo serviço ou produto
@router.post("", response_model=Servico)
def cadastrar_servico(novo_servico: Servico, session: Session = Depends(obter_sessao)):
    session.add(novo_servico)
    session.commit()
    session.refresh(novo_servico)
    return novo_servico

# Rota atualizada que busca os serviços e preços direto do Banco de Dados
@router.get("", response_model=List[Servico])
def listar_servicos(session: Session = Depends(obter_sessao)):
    servicos = session.exec(select(Servico)).all()
    return servicos
