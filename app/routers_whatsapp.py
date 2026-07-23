from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
import httpx
from datetime import datetime

from app.database import obter_sessao

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Bot"])

# Endereço interno da sua própria API (Modo Desenvolvimento do FastAPI)
API_BASE_URL = "http://127.0.0.1:8000"

@router.post("/webhook")
async def receber_mensagem_whatsapp(dados_recebidos: dict, session: Session = Depends(obter_sessao)):
    """
    Rota Webhook para receber as mensagens do WhatsApp via Gateway (Z-API, Evolution, etc.).
    Espera receber um dicionário contendo o número do cliente e o texto digitado.
    """
    texto_cliente = dados_recebidos.get("text", "").strip().lower()
    numero_cliente = dados_recebidos.get("from_number", "")

    if not numero_cliente:
        raise HTTPException(status_code=400, detail="Número do cliente não identificado.")

    mensagem_resposta = ""

    # 1. MENU PRINCIPAL: Saudação e Opções Gerais
    if texto_cliente in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "menu"]:
        mensagem_resposta = (
            "Olá! Bem-vindo ao sistema de atendimento da Barbearia! 💈✂️\n\n"
            "Como posso te ajudar hoje? Digite apenas o número da opção desejada:\n\n"
            "*1* - Ver Serviços e Preços 💰\n"
            "*2* - Ver Nossos Barbeiros 🧔\n"
            "*3* - Consultar Horários Livres 📅\n"
            "*4* - Cancelar um Agendamento ❌"
        )

    # 2. OPÇÃO 1: Listagem Dinâmica de Serviços e Preços
    elif texto_cliente == "1":
        async with httpx.AsyncClient() as client:
            resposta = await client.get(f"{API_BASE_URL}/servicos")
            if resposta.status_code == 200:
                servicos = resposta.json()
                if not servicos:
                    mensagem_resposta = "No momento não temos serviços cadastrados."
                else:
                    mensagem_resposta = "Aqui está a nossa tabela de serviços atualizada: 💰\n\n"
                    for s in servicos:
                        mensagem_resposta += f"• *{s['nome']}* — R$ {s['preco']:.2f}\n"
            else:
                mensagem_resposta = "Desculpe, tive um problema ao consultar nossos preços. Tente novamente mais tarde."

    # 3. OPÇÃO 2: Listagem de Barbeiros Disponíveis
    elif texto_cliente == "2":
        async with httpx.AsyncClient() as client:
            resposta = await client.get(f"{API_BASE_URL}/barbeiros")
            if resposta.status_code == 200:
                barbeiros = resposta.json()
                if not barbeiros:
                    mensagem_resposta = "Não temos barbeiros cadastrados no momento."
                else:
                    mensagem_resposta = "Conheça a nossa equipe de profissionais: 🧔\n\n"
                    for b in barbeiros:
                        mensagem_resposta += f"• *ID {b['id']}*: {b['nome']} (Esp: {b['especialidade']})\n"
                    mensagem_resposta += "\n💡 Para ver a agenda de um deles, digite *3* no menu."
            else:
                mensagem_resposta = "Erro ao listar barbeiros."

    # 4. OPÇÃO 3: Instrução de como ver a Agenda de 30 em 30 min
    elif texto_cliente == "3":
        mensagem_resposta = (
            "Para consultar os horários disponíveis, preciso que você envie o ID do barbeiro e a data desejada.\n\n"
            "Escreva exatamente neste formato:\n"
            "👉 *agenda [ID do barbeiro] [Ano-Mês-Dia]*\n\n"
            "Exemplo: *agenda 1 2026-07-10*"
        )

    # 5. EXECUÇÃO DA OPÇÃO 3: Processamento do comando "agenda X AAAA-MM-DD"
    elif texto_cliente.startswith("agenda "):
        partes = texto_cliente.split(" ")
        if len(partes) == 3:
            barbeiro_id = partes[1]
            data_desejada = partes[2]

            async with httpx.AsyncClient() as client:
                resposta = await client.get(f"{API_BASE_URL}/barbeiros/{barbeiro_id}/horarios-livres?data={data_desejada}")
                if resposta.status_code == 200:
                    dados_agenda = resposta.json()
                    horarios = dados_agenda.get("horarios_disponiveis", [])
                    nome_b = dados_agenda.get("barbeiro", "Barbeiro")

                    if not horarios:
                        mensagem_resposta = f"Poxa, o barbeiro {nome_b} não tem horários disponíveis para o dia {data_desejada}."
                    else:
                        mensagem_resposta = f"Horários livres com *{nome_b}* no dia *{data_desejada}*: 📅\n\n"
                        for h in horarios:
                            mensagem_resposta += f"• {h}\n"
                        mensagem_resposta += (
                            "\nPara fechar o agendamento, responda com:\n"
                            "👉 *agendar [Seu Nome] [Serviço] [ID Barbeiro] [DataTHora]*\n"
                            "Ex: *agendar Felipe Corte Tesoura 1 2026-07-10T14:30*"
                        )
                elif resposta.status_code == 404:
                    mensagem_resposta = "Barbeiro não encontrado. Verifique o ID digitado."
                else:
                    mensagem_resposta = "Formato de data incorreto ou erro no sistema. Use AAAA-MM-DD."
        else:
            mensagem_resposta = "Comando incorreto! Use: *agenda [ID] [AAAA-MM-DD]*"

    # 6. CONFIRMAÇÃO DO AGENDAMENTO: Processamento do comando "agendar Nome Servico ID DataTHora"
    elif texto_cliente.startswith("agendar "):
        partes = texto_cliente.split(" ")
        # Ex: ['agendar', 'felipe', 'corte', 'tesoura', '1', '2026-07-10t14:30']
        if len(partes) >= 5:
            try:
                # O nome do serviço pode ter espaços (ex: "Corte Tesoura")
                # Vamos reconstruir os dados juntando os pedaços do texto
                nome_cliente = partes[1].capitalize()
                barbeiro_id = int(partes[-2])
                data_hora = partes[-1].upper() # Garante o 'T' maiúsculo

                # Junta o que sobrou no meio para formar o nome do serviço
                nome_servico = " ".join(partes[2:-2]).title()

                # Monta a estrutura para enviar via POST para a sua própria rota legítima
                dados_post = {
                    "cliente": nome_cliente,
                    "servico": nome_servico,
                    "data_hora": data_hora,
                    "barbeiro_id": barbeiro_id
                }

                async with httpx.AsyncClient() as client:
                    resposta = await client.post(f"{API_BASE_URL}/agendamentos", json=dados_post)
                    if resposta.status_code == 200:
                        res_json = resposta.json()
                        mensagem_resposta = (
                            f"🎉 *Agendamento Confirmado com Sucesso!* 🎉\n\n"
                            f"• *Cliente:* {res_json['cliente']}\n"
                            f"• *Serviço:* {res_json['servico']}\n"
                            f"• *Horário:* {res_json['data_hora'].replace('T', ' às ')}\n"
                            f"• *Protocolo/ID:* {res_json['id']}\n\n"
                            f"Te esperamos lá! Se precisar cancelar, use a opção *4*."
                        )
                    else:
                        erro_detalhe = resposta.json().get("detail", "Erro desconhecido.")
                        mensagem_resposta = f"❌ *Não consegui agendar:* {erro_detalhe}"
            except Exception:
                mensagem_resposta = "Erro ao processar as informações. Verifique a ordem dos dados no comando."
        else:
            mensagem_resposta = "Comando incompleto! Use o exemplo enviado acima."

    # 7. OPÇÃO 4: Instrução de Cancelamento via ID do agendamento
    elif texto_cliente == "4":
        mensagem_resposta = (
            "Para cancelar um horário, envie o comando com o número do seu protocolo/ID do agendamento:\n\n"
            "👉 *cancelar [Número do ID]*\n"
            "Exemplo: *cancelar 1*"
        )

    # 8. EXECUÇÃO DA OPÇÃO 4: Chamada automática da rota DELETE
    elif texto_cliente.startswith("cancelar "):
        partes = texto_cliente.split(" ")
        if len(partes) == 2 and partes[1].isdigit():
            agendamento_id = int(partes[1])
            async with httpx.AsyncClient() as client:
                resposta = await client.delete(f"{API_BASE_URL}/agendamentos/{agendamento_id}")
                dados_delete = resposta.json()
                if "mensagem" in dados_delete:
                    mensagem_resposta = f"✅ {dados_delete['mensagem']}"
                else:
                    mensagem_resposta = "❌ Agendamento não encontrado para cancelamento."
        else:
            mensagem_resposta = "Comando inválido! Use: *cancelar [Número]*"

    # 9. TRATAMENTO DE TEXTOS NÃO RECONHECIDOS
    else:
        mensagem_resposta = "Desculpe, não entendi o comando. 🤔\nDigite *Menu* ou *Oi* para iniciar nosso atendimento automático!"

    # Retorna o JSON simulando a resposta que será enviada para o celular do cliente
    return {
        "numero_destino": numero_cliente,
        "mensagem_enviada": mensagem_resposta
    }
