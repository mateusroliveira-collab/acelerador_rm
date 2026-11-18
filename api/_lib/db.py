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

# Fixa o driver explicitamente em "postgresql+psycopg2://" (o pacote que
# está no requirements.txt é o psycopg2-binary). Sem isso:
#  - Neon às vezes fornece o prefixo antigo "postgres://", que o
#    SQLAlchemy moderno não aceita;
#  - a partir do SQLAlchemy 2.1, "postgresql://" sem driver passou a usar
#    o psycopg (v3) por padrão -- que não está instalado. Isso derrubou a
#    API inteira em produção ("No module named 'psycopg'").
for _prefixo in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(_prefixo):
        DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len(_prefixo):]
        break

_eh_sqlite = DATABASE_URL.startswith("sqlite")

if _eh_sqlite:
    _opcoes_engine = {"connect_args": {"check_same_thread": False}}
else:
    # Serverless: poucas conexões por instância (cada uma é um slot no
    # Neon), reciclagem antes do Neon derrubar conexão ociosa e falha
    # rápida se o banco não responder. pre_ping continua: conexão
    # congelada junto com a função pode ter sido fechada pelo servidor.
    # Na Vercel, prefira a URL "-pooler" do Neon em DATABASE_URL.
    _opcoes_engine = {
        "pool_size": 2,
        "max_overflow": 3,
        "pool_recycle": 240,
        "connect_args": {"connect_timeout": 10},
    }

engine = create_engine(DATABASE_URL, pool_pre_ping=True, **_opcoes_engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _colunas_existentes() -> dict[str, set[str]]:
    """
    {tabela: {colunas}} das tabelas do projeto que já existem no banco.
    No Postgres é UMA consulta (uma ida e volta ao Neon); o inspetor do
    SQLAlchemy faria várias.
    """
    nomes = list(Base.metadata.tables)
    if _eh_sqlite:
        from sqlalchemy import inspect

        insp = inspect(engine)
        return {
            t: {c["name"] for c in insp.get_columns(t)} for t in nomes if insp.has_table(t)
        }

    from sqlalchemy import bindparam, text

    consulta = text(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name IN :tabelas"
    ).bindparams(bindparam("tabelas", expanding=True))
    existentes: dict[str, set[str]] = {}
    with engine.connect() as conn:
        for tabela, coluna in conn.execute(consulta, {"tabelas": nomes}):
            existentes.setdefault(tabela, set()).add(coluna)
    return existentes


# Colunas acrescentadas depois da criação inicial das tabelas. O create_all
# não altera tabelas que já existem (ex.: a do Neon), então elas entram aqui.
_COLUNAS_NOVAS = {
    "xml_personalizado": [
        ("excluido", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("excluido_em", "TIMESTAMP"),
    ],
}


def criar_tabelas():
    """
    Garante tabelas e colunas -- seguro rodar toda vez, nunca apaga dado.
    Roda no início a frio da função: com o schema já em dia, custa só
    uma consulta ao banco.
    """
    from sqlalchemy import text

    from . import models  # noqa: F401 -- garante que os modelos foram importados antes de criar

    existentes = _colunas_existentes()
    if any(t not in existentes for t in Base.metadata.tables):
        Base.metadata.create_all(bind=engine)
        existentes = _colunas_existentes()

    for tabela, colunas in _COLUNAS_NOVAS.items():
        for nome, ddl in colunas:
            if nome not in existentes.get(tabela, {nome}):
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {nome} {ddl}"))
