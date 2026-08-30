"""
Modelos de dados (tabelas) do banco.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text

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
