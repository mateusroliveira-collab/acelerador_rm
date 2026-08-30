from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

from ..registro_online_boleto.validador import validar_boleto

router = APIRouter(prefix="/api/registro-online", tags=["registro-online"])


class DadosBoleto(BaseModel):
    dados: dict[str, Any]


@router.post("/validar-boleto")
def validar_boleto_route(corpo: DadosBoleto):
    """
    Valida os dados de um boleto antes do envio pro registro online do
    banco. Cobre regras UNIVERSAIS (matemática, lógica de data, limite
    legal de multa) -- não específicas de um banco. Ver docstring de
    validador.py pra formato esperado do campo "dados".
    """
    resultado = validar_boleto(corpo.dados)
    return resultado.to_dict()
