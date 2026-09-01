from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

from ..registro_online_boleto.validador import validar_boleto
from ..registro_uso import registrar_uso

router = APIRouter(prefix="/api/registro-online", tags=["registro-online"])


class DadosBoleto(BaseModel):
    dados: dict[str, Any]


@router.post("/validar-boleto")
def validar_boleto_route(corpo: DadosBoleto):
    """
    Valida os dados de um boleto antes do envio pro registro online do
    banco. Cobre regras UNIVERSAIS (matemática, lógica de data, limite
    legal de multa) -- não específicas de um banco.
    """
    resultado = validar_boleto(corpo.dados)
    try:
        registrar_uso(
            "registro_online",
            "validar-boleto",
            {"valido": resultado.valido, "total_erros": len(resultado.erros)},
        )
    except Exception:
        pass
    return resultado.to_dict()