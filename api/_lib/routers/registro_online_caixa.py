from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..registro_online_boleto.caixa_xml import validar_boleto_xml_caixa
from ..registro_uso import registrar_uso

router = APIRouter(prefix="/api/registro-online", tags=["registro-online"])


class XmlCaixa(BaseModel):
    xml: str


@router.post("/validar-caixa-xml")
def validar_caixa_xml_route(corpo: XmlCaixa):
    """
    Valida o XML de Registro Online da Caixa (sistema SIGCB, operação
    INCLUI_BOLETO). Aceita colar um FRAGMENTO do XML (sem o envelope
    completo) -- não precisa ter a declaração de namespace.
    """
    try:
        resultado = validar_boleto_xml_caixa(corpo.xml)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    registrar_uso(
        "registro_online",
        "validar-caixa-xml",
        {"valido": resultado.valido, "total_erros": len(resultado.erros)},
    )
    return resultado.to_dict()
