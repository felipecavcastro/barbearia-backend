from sqlmodel import create_engine, Session

DATABASE_URL = "sqlite:///./barbearia.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def obter_sessao():
    with Session(engine) as session:
        yield session
