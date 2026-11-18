"""
Rotas do gerador de payload de DataServer.

SÓ gera e valida: não conecta ao RM e não guarda nada. Os valores digitados
(que podem ser dados pessoais) não vão pro banco nem pro log de uso -- o
log guarda apenas o módulo, a operação e o resultado.
"""

import json

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..dataserver.base import normalizar_e_validar
from ..dataserver.glb_usuario import gerar_payload as gerar_payload_glb_usuario
from ..dataserver.registro import MODULOS
from ..registro_uso import registrar_uso

router = APIRouter(prefix="/api/dataserver", tags=["dataserver"])

# Gerador de payload de cada módulo: (valores normalizados) -> dict.
_GERADORES = {"glb-usuario": gerar_payload_glb_usuario}


class PedidoGerar(BaseModel):
    operacao: str = "incluir"
    valores: dict = {}


def _modulo(chave: str):
    modulo = MODULOS.get(chave)
    if modulo is None:
        raise HTTPException(status_code=404, detail=f"Módulo '{chave}' não encontrado.")
    return modulo


@router.get("/modulos")
def listar_modulos():
    """Módulos disponíveis e seus campos -- a tela se monta a partir disso."""
    return [m.para_dict() for m in MODULOS.values()]


@router.post("/{chave}/validar")
def validar(chave: str, pedido: PedidoGerar):
    modulo = _modulo(chave)
    normalizados, erros = normalizar_e_validar(modulo, pedido.valores, pedido.operacao)
    avisos = modulo.avisos(normalizados, pedido.operacao) if not erros else []
    return {"valido": not erros, "erros": erros, "avisos": avisos}


@router.post("/{chave}/gerar")
def gerar(chave: str, pedido: PedidoGerar, tarefas: BackgroundTasks):
    modulo = _modulo(chave)
    normalizados, erros = normalizar_e_validar(modulo, pedido.valores, pedido.operacao)
    if erros:
        tarefas.add_task(
            registrar_uso, "dataserver", "gerar",
            {"modulo": chave, "operacao": pedido.operacao, "erros": len(erros)}, False,
        )
        raise HTTPException(status_code=422, detail={"erros": erros})

    payload = _GERADORES[chave](normalizados)
    entrega = modulo.entrega(payload, pedido.operacao)
    tarefas.add_task(
        registrar_uso, "dataserver", "gerar", {"modulo": chave, "operacao": pedido.operacao}
    )
    return {
        "payload": payload,
        "json": json.dumps(payload, ensure_ascii=False, indent=2),
        "avisos": modulo.avisos(normalizados, pedido.operacao),
        "nome_arquivo": entrega.get("nome_arquivo", f"{modulo.dataserver}.json"),
        "instrucoes": entrega.get("instrucoes", []),
    }
