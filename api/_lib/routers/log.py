from fastapi import APIRouter, Query

from ..db import SessionLocal
from ..models import RegistroUso

router = APIRouter(prefix="/api/log", tags=["log"])


@router.get("/recentes")
def listar_registros_recentes(
    ferramenta: str | None = Query(default=None, description="Filtra por ferramenta: xml, cnab, mit41, registro_online"),
    limite: int = Query(default=50, le=500),
):
    """Devolve os registros de uso mais recentes, opcionalmente filtrados por ferramenta."""
    db = SessionLocal()
    try:
        consulta = db.query(RegistroUso)
        if ferramenta:
            consulta = consulta.filter(RegistroUso.ferramenta == ferramenta)
        registros = (
            consulta.order_by(RegistroUso.criado_em.desc()).limit(limite).all()
        )
        return [
            {
                "id": r.id,
                "criado_em": r.criado_em.isoformat() if r.criado_em else None,
                "ferramenta": r.ferramenta,
                "acao": r.acao,
                "detalhes": r.detalhes,
                "sucesso": r.sucesso,
            }
            for r in registros
        ]
    finally:
        db.close()


@router.get("/resumo")
def resumo_de_uso():
    """Contagem de uso por ferramenta+ação -- visão rápida do que é mais usado."""
    db = SessionLocal()
    try:
        from sqlalchemy import func

        resultado = (
            db.query(
                RegistroUso.ferramenta,
                RegistroUso.acao,
                func.count(RegistroUso.id).label("total"),
            )
            .group_by(RegistroUso.ferramenta, RegistroUso.acao)
            .order_by(func.count(RegistroUso.id).desc())
            .all()
        )
        return [
            {"ferramenta": r.ferramenta, "acao": r.acao, "total": r.total}
            for r in resultado
        ]
    finally:
        db.close()
