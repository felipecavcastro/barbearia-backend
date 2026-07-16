from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime, timedelta

from app.database import obter_sessao
from app.models import Barbeiro, Agendamento

router = APIRouter(prefix="/barbeiros", tags=["Barbeiros"])

@router.post("", response_model=Barbeiro)
def cadastrar_barbeiro(novo_barbeiro: Barbeiro, session: Session = Depends(obter_sessao)):
    session.add(novo_barbeiro)
    session.commit()
    session.refresh(novo_barbeiro)
    return novo_barbeiro

@router.get("", response_model=List[Barbeiro])
def listar_barbeiros(session: Session = Depends(obter_sessao)):
    barbeiros = session.exec(select(Barbeiro)).all()
    return barbeiros

# ROTA MÁGICA: Calcula os horários disponíveis de 30 em 30 minutos para uma data específica
@router.get("/{barbeiro_id}/horarios-livres")
def listar_horarios_livres(barbeiro_id: int, data: str, session: Session = Depends(obter_sessao)):
    # 1. Buscamos o barbeiro no banco
    barbeiro = session.get(Barbeiro, barbeiro_id)
    if not barbeiro:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado!")

    # Validar formato da data recebida (deve ser AAAA-MM-DD, ex: 2026-07-10)
    try:
        datetime.strptime(data, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use AAAA-MM-DD")

    # 2. Buscamos todos os agendamentos ativos desse barbeiro para ESSA DATA específica
    agendamentos_do_dia = session.exec(
        select(Agendamento)
        .where(Agendamento.barbeiro_id == barbeiro_id)
        .where(Agendamento.status != "Cancelado")
    ).all()

    # Extraímos apenas o horário (HH:MM) dos agendamentos que já existem no banco
    horarios_ocupados = []
    for agendamento in agendamentos_do_dia:
        if "T" in agendamento.data_hora:
            horario_texto = agendamento.data_hora.split("T")[1][:5]  # Pega o "HH:MM"
            horarios_ocupados.append(horario_texto)

    # 3. Geramos os horários de 30 em 30 minutos dentro da jornada do barbeiro
    horarios_livres = []

    # Transformamos as strings de horário em objetos de hora do Python para fazer cálculos
    formato_hora = "%H:%M"
    hora_atual = datetime.strptime(barbeiro.hora_inicio, formato_hora)
    hora_limite = datetime.strptime(barbeiro.hora_fim, formato_hora)

    # Definimos o intervalo de almoço fixado das 12:00 às 13:00
    inicio_almoco = datetime.strptime("12:00", formato_hora)
    fim_almoco = datetime.strptime("13:00", formato_hora)

    while hora_atual < hora_limite:
        # Regra 1: Pula se o horário estiver dentro do intervalo de almoço (12:00 até as 12:59)
        if hora_atual >= inicio_almoco and hora_atual < fim_almoco:
            hora_atual += timedelta(minutes=30)
            continue

        horario_str = hora_atual.strftime(formato_hora)

        # Regra 2: Só adiciona na lista se o horário NÃO estiver ocupado por outro cliente
        if horario_str not in horarios_ocupados:
            horarios_livres.append(horario_str)

        # Avança 30 minutos para o próximo slot
        hora_atual += timedelta(minutes=30)

    return {
        "barbeiro": barbeiro.nome,
        "data": data,
        "horarios_disponiveis": horarios_livres
    }
