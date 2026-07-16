from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlmodel import Session, select, SQLModel
from typing import List
from datetime import datetime

from app.database import obter_sessao
from app.models import Agendamento, Barbeiro, Servico

# Configuração da segurança do Administrador
API_KEY_NAME = "X-Admin-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
TOKEN_ADMINISTRADOR = "senha_admin_123"  # Esta é a senha secreta do seu Admin

# Função auxiliar que verifica se quem está acessando é realmente o Admin
def verificar_admin(api_key: str = Security(api_key_header)):
    if api_key != TOKEN_ADMINISTRADOR:
        raise HTTPException(status_code=401, detail="Acesso negado. Apenas o administrador pode ver o faturamento.")
    return api_key

class AgendamentoComBarbeiro(SQLModel):
    id: int
    cliente: str
    servico: str
    data_hora: str
    barbeiro_id: int
    barbeiro_nome: str

router = APIRouter(prefix="/agendamentos", tags=["Agendamentos"])

@router.post("", response_model=Agendamento)
def criar_agendamento(novo_agendamento: Agendamento, session: Session = Depends(obter_sessao)):
    try:
        data_limpa = novo_agendamento.data_hora.replace("Z", "")
        datetime.fromisoformat(data_limpa)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data e hora inválido. Use o padrão do calendário.")

    barbeiro = session.get(Barbeiro, novo_agendamento.barbeiro_id)
    if not barbeiro:
        raise HTTPException(status_code=404, detail="O barbeiro informado não existe!")

    session.add(novo_agendamento)
    session.commit()
    session.refresh(novo_agendamento)
    return novo_agendamento

@router.get("", response_model=List[AgendamentoComBarbeiro])
def listar_agendamentos(session: Session = Depends(obter_sessao)):
    agendamentos = session.exec(select(Agendamento)).all()
    resposta_customizada = []
    for agendamento in agendamentos:
        barbeiro = session.get(Barbeiro, agendamento.barbeiro_id)
        nome_barbeiro = barbeiro.nome if barbeiro else "Não atribuído"
        item = AgendamentoComBarbeiro(
            id=agendamento.id,
            cliente=agendamento.cliente,
            servico=agendamento.servico,
            data_hora=agendamento.data_hora,
            barbeiro_id=agendamento.barbeiro_id,
            barbeiro_nome=nome_barbeiro
        )
        resposta_customizada.append(item)
    return resposta_customizada

@router.delete("/{agendamento_id}")
def deletar_agendamento(agendamento_id: int, session: Session = Depends(obter_sessao)):
    agendamento = session.get(Agendamento, agendamento_id)
    if not agendamento:
        return {"erro": "Agendamento não encontrado!"}
    session.delete(agendamento)
    session.commit()
    return {"mensagem": f"Agendamento do cliente {agendamento.cliente} cancelado com sucesso!"}

@router.put("/{agendamento_id}", response_model=Agendamento)
def atualizar_agendamento(agendamento_id: int, agendamento_updated: Agendamento, session: Session = Depends(obter_sessao)):
    agendamento_banco = session.get(Agendamento, agendamento_id)
    if not agendamento_banco:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado!")
    try:
        data_limpa = agendamento_updated.data_hora.replace("Z", "")
        datetime.fromisoformat(data_limpa)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data e hora inválido. Use o padrão do calendário.")
    agendamento_banco.cliente = agendamento_updated.cliente
    agendamento_banco.servico = agendamento_updated.servico
    agendamento_banco.data_hora = agendamento_updated.data_hora
    session.add(agendamento_banco)
    session.commit()
    session.refresh(agendamento_banco)
    return agendamento_banco

@router.patch("/{agendamento_id}/status")
def alterar_status_agendamento(agendamento_id: int, novo_status: str, session: Session = Depends(obter_sessao)):
    agendamento = session.get(Agendamento, agendamento_id)
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado!")
    if novo_status not in ["Pendente", "Concluido", "Cancelado"]:
        raise HTTPException(status_code=400, detail="Status inválido! Use: Pendente, Concluido ou Cancelado.")
    agendamento.status = novo_status
    session.add(agendamento)
    session.commit()
    return {"mensagem": f"Status do agendamento do cliente {agendamento.cliente} atualizado para {novo_status}!"}


# ROTAS PROTEGIDAS: Adicionamos o 'Depends(verificar_admin)' nas duas rotas abaixo
@router.get("/relatorio/previsao")
def calcular_faturamento_previsto(session: Session = Depends(obter_sessao), admin: str = Depends(verificar_admin)):
    agendamentos = session.exec(select(Agendamento).where(Agendamento.status != "Cancelado")).all()
    faturamento_total = 0.0
    for agendamento in agendamentos:
        servico_banco = session.exec(select(Servico).where(Servico.nome == agendamento.servico)).first()
        if servico_banco:
            faturamento_total += servico_banco.preco
    return {"quantidade_agendamentos": len(agendamentos), "faturamento_previsto_total": faturamento_total}

@router.get("/relatorio/real")
def calcular_faturamento_real(session: Session = Depends(obter_sessao), admin: str = Depends(verificar_admin)):
    agendamentos_concluidos = session.exec(select(Agendamento).where(Agendamento.status == "Concluido")).all()
    faturamento_real = 0.0
    for agendamento in agendamentos_concluidos:
        servico_banco = session.exec(select(Servico).where(Servico.nome == agendamento.servico)).first()
        if servico_banco:
            faturamento_real += servico_banco.preco
    return {"servicos_realizados": len(agendamentos_concluidos), "faturamento_em_caixa": faturamento_real}
