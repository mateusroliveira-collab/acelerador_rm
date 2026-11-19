"""
Modelos de dados (tabelas) do banco.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import false as sa_false, true as sa_true

from .db import Base


class RegistroUso(Base):
    """
    Um registro por ação relevante em qualquer uma das ferramentas --
    pra ter visibilidade de uso real (o que é mais usado, com que
    frequência, taxa de sucesso), sem guardar dado sensível do
    conteúdo em si (nunca salva XML/CNAB/MIT41 inteiro, só metadados).
    """

    __tablename__ = "registro_uso"

    id = Column(Integer, primary_key=True, index=True)
    criado_em = Column(DateTime, default=datetime.utcnow, index=True)
    ferramenta = Column(String(50), index=True)  # "xml", "cnab", "mit41", "registro_online"
    acao = Column(String(100))  # "buscar", "validar-240", "sugerir-grupo", etc.
    detalhes = Column(Text, nullable=True)  # contexto livre, em JSON (string)
    sucesso = Column(Boolean, default=True)


class XmlPersonalizado(Base):
    """
    Um XML enviado pelo próprio usuário pra usar como referência, fora
    da base padrão (data/xml_base/, que só muda via commit no Git).

    Guarda o conteúdo ORIGINAL e o já HIGIENIZADO (calculado uma vez, no
    momento do envio) -- assim o download fica instantâneo depois, sem
    reprocessar. Isso é o "banco de XMLs" de verdade nesse projeto: como
    a Vercel não tem sistema de arquivos persistente, aqui é onde um XML
    enviado pelo usuário sobrevive de fato entre deploys.
    """

    __tablename__ = "xml_personalizado"

    id = Column(Integer, primary_key=True, index=True)
    criado_em = Column(DateTime, default=datetime.utcnow, index=True)
    grupo = Column(String(10), index=True)
    nome_arquivo = Column(String(255))
    conteudo_original = Column(Text)
    conteudo_limpo = Column(Text)
    campos_zerados = Column(Integer, default=0)
    # Exclusão reversível: a linha nunca é apagada, só marcada e escondida das buscas.
    excluido = Column(Boolean, default=False, nullable=False, server_default=sa_false())
    excluido_em = Column(DateTime, nullable=True)


class Cliente(Base):
    """
    Configuração por cliente (preparação pra multi-cliente / produto).

    `config` é um JSON por módulo do gerador de DataServer, ex.:
      {"glb-usuario": {"codigos_acesso": ["Acesso01", "Acesso02"], "versao_rm": "12.1.2310"}}
    Guarda só configuração -- NUNCA dado pessoal nem credencial. Não há rota
    de escrita aberta: a manutenção é feita por scripts/cliente_config.py.
    """

    __tablename__ = "cliente"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True, nullable=False)
    nome = Column(String(200), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False, server_default=sa_true())
    config = Column(Text, nullable=True)  # JSON
    criado_em = Column(DateTime, default=datetime.utcnow)
