"""
Rotas do gerador de payload de DataServer.

SÓ gera e valida: não conecta ao RM e não guarda nada. Os valores digitados
(que podem ser dados pessoais) não vão pro banco nem pro log de uso -- o
log guarda apenas o módulo, a operação e o resultado.
"""

import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from pydantic import BaseModel

from ..dataserver.base import normalizar_e_validar
from ..dataserver.glb_usuario import gerar_payload as gerar_payload_glb_usuario
from ..dataserver.lote import LoteInvalido, processar_lote
from ..dataserver.registro import MODULOS
from ..registro_uso import registrar_uso

router = APIRouter(prefix="/api/dataserver", tags=["dataserver"])

# Gerador de payload de cada módulo: (valores normalizados) -> dict.
_GERADORES = {"glb-usuario": gerar_payload_glb_usuario}

# Linha fictícia do CSV de modelo, por módulo (valores como o analista digitaria no Excel).
_EXEMPLOS_LOTE = {
    "glb-usuario": {
        "CODUSUARIO": "usuario.exemplo", "NOME": "Usuário de Exemplo",
        "EMAIL": "usuario.exemplo@exemplo.com", "CODACESSO": "Acesso01",
        "STATUS": "sim", "OIDC_ENABLED": "não", "OBRIGAALTERARSENHA": "sim",
        "DATAINICIO": "01/01/2026", "IGNORARAUTENTICACAOLDAP": "não",
    },
}


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


class PedidoLote(BaseModel):
    operacao: str = "incluir"
    texto: str = ""  # tabela colada do Excel ou conteúdo do CSV


@router.get("/{chave}/modelo-csv")
def modelo_csv(chave: str):
    """CSV de modelo (cabeçalho + 1 linha fictícia), abre direto no Excel pt-BR."""
    modulo = _modulo(chave)
    exemplo = _EXEMPLOS_LOTE.get(chave, {})
    cabecalho = ";".join(c.nome for c in modulo.campos)
    linha = ";".join(exemplo.get(c.nome, "") for c in modulo.campos)
    conteudo = "﻿" + cabecalho + "\r\n" + linha + "\r\n"  # BOM: Excel lê os acentos
    return Response(
        content=conteudo.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{modulo.dataserver}_modelo.csv"'},
    )


@router.post("/{chave}/lote")
def gerar_lote(chave: str, pedido: PedidoLote, tarefas: BackgroundTasks):
    modulo = _modulo(chave)
    if pedido.operacao not in modulo.operacoes:
        raise HTTPException(status_code=422, detail=f"Operação inválida: {pedido.operacao!r}.")
    try:
        resultado = processar_lote(modulo, pedido.texto, pedido.operacao, _GERADORES[chave])
    except LoteInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Log só com contagens: a planilha pode ter dados pessoais.
    tarefas.add_task(
        registrar_uso, "dataserver", "gerar-lote",
        {"modulo": chave, "operacao": pedido.operacao, "total": resultado["total"],
         "validos": resultado["validos"], "invalidos": resultado["invalidos"]},
    )
    return resultado


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
