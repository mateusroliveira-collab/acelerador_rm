"""
Acesso à configuração por cliente (tabela `cliente`). Somente leitura.

Se o banco falhar, devolve None: a configuração por cliente é um refinamento
(ex.: lista de códigos de acesso válidos) e nunca pode derrubar a geração.
"""

import json
import logging

from .db import SessionLocal
from .models import Cliente

logger = logging.getLogger(__name__)


def config_do_cliente(codigo: str | None, modulo: str) -> dict | None:
    """Config do módulo para o cliente, ou None (sem cliente, inativo, sem config ou erro)."""
    if not codigo:
        return None
    try:
        db = SessionLocal()
        try:
            linha = db.query(Cliente).filter(Cliente.codigo == codigo, Cliente.ativo.is_(True)).first()
            if not linha or not linha.config:
                return None
            dados = json.loads(linha.config)
            cfg = dados.get(modulo) if isinstance(dados, dict) else None
            return cfg if isinstance(cfg, dict) else None
        finally:
            db.close()
    except Exception:
        logger.exception("Falha ao ler config do cliente (ignorado)")
        return None
