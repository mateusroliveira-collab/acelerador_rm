"""
Função central de registro de uso -- chamada pelos routers de cada
ferramenta em pontos-chave (busca, validação, etc.).

REGRA IMPORTANTE: essa função NUNCA pode derrubar a ferramenta principal.
Se o banco estiver fora do ar, mal configurado, ou qualquer outro
problema, o erro é silenciado -- log de uso é acessório, não crítico.
Uma falha aqui não pode impedir o usuário de validar um CNAB ou buscar
um XML.
"""

import json
import logging

from .db import SessionLocal
from .models import RegistroUso

logger = logging.getLogger(__name__)


def registrar_uso(
    ferramenta: str,
    acao: str,
    detalhes: dict | None = None,
    sucesso: bool = True,
) -> None:
    """
    Grava um registro de uso. Nunca levanta exceção -- qualquer erro é
    logado (pro Vercel Runtime Logs, se quiser investigar depois) e
    ignorado, sem propagar.
    """
    try:
        db = SessionLocal()
        try:
            registro = RegistroUso(
                ferramenta=ferramenta,
                acao=acao,
                detalhes=json.dumps(detalhes, ensure_ascii=False) if detalhes else None,
                sucesso=sucesso,
            )
            db.add(registro)
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("Falha ao registrar uso (ignorado, não afeta a ferramenta principal)")
