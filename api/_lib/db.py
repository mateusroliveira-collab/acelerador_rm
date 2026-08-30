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

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")

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
