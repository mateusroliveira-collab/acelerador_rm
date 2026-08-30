"""
Conexão com banco de dados via SQLAlchemy.

Em produção, usa a variável de ambiente DATABASE_URL (Neon/Postgres).
Se não estiver definida (ex: rodando local sem configurar ainda), cai
pra um SQLite local (arquivo dev.db na raiz) -- só pra não travar o
desenvolvimento. Produção sempre deve ter DATABASE_URL configurada no
painel do Vercel.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


def _descobrir_database_url() -> str:
    """
    A integração nativa Neon<->Vercel às vezes cria a variável com nome
    diferente de DATABASE_URL (ex: POSTGRES_URL, ou só as peças soltas
    PGHOST/PGUSER/PGPASSWORD/PGDATABASE) -- confere várias
    possibilidades antes de desistir e cair pro SQLite local.
    """
    for nome in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED"):
        valor = os.environ.get(nome)
        if valor:
            return valor

    # Monta a partir das peças soltas, se existirem (padrão do Vercel Postgres/Neon)
    host = os.environ.get("PGHOST")
    user = os.environ.get("PGUSER")
    senha = os.environ.get("PGPASSWORD")
    banco = os.environ.get("PGDATABASE")
    if host and user and senha and banco:
        return f"postgresql://{user}:{senha}@{host}/{banco}?sslmode=require"

    # Reserva: SQLite -- só a pasta /tmp é gravável em ambiente
    # serverless (Vercel). Isso NÃO persiste de forma confiável entre
    # execuções (cada chamada pode cair numa instância diferente) -- é
    # só pra não derrubar o app com um erro de "arquivo não pode ser
    # aberto" enquanto a variável de banco não estiver configurada.
    pasta_gravavel = "/tmp" if os.environ.get("VERCEL") else "."
    return f"sqlite:///{pasta_gravavel}/dev.db"


DATABASE_URL = _descobrir_database_url()

# Neon (e alguns outros provedores) às vezes fornece a URL com o prefixo
# antigo "postgres://" -- o SQLAlchemy moderno exige "postgresql://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_eh_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _eh_sqlite else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def criar_tabelas():
    """Cria as tabelas que ainda não existem -- seguro rodar toda vez, não recria o que já existe."""
    from . import models  # noqa: F401 -- garante que os modelos foram importados antes de criar
    Base.metadata.create_all(bind=engine)
