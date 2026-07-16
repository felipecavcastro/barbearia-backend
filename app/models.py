from sqlmodel import SQLModel, Field

class Barbeiro(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str
    especialidade: str
    # NOVOS CAMPOS: Definem a jornada de trabalho do barbeiro
    hora_inicio: str = Field(default="09:00")
    hora_fim: str = Field(default="18:00")

class Agendamento(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cliente: str
    servico: str
    data_hora: str  # Padrão: "AAAA-MM-DDTHH:MM" -> ex: "2026-07-10T14:30"
    barbeiro_id: int = Field(foreign_key="barbeiro.id")
    status: str = Field(default="Pendente")

class Servico(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str
    preco: float
