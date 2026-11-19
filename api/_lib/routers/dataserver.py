"""
Rotas do gerador de payload de DataServer.

SÓ gera e valida: não conecta ao RM e não guarda nada. Os valores digitados
(que podem ser dados pessoais) não vão pro banco nem pro log de uso -- o
log guarda apenas módulo, operação, cliente, versão do schema e contagens.

Montado em dois prefixos (ver api/index.py):
  /api/v1/dataserver/...  -> versão canônica (a tela e o Google Sheets usam)
  /api/dataserver/...     -> alias de compatibilidade (fora da documentação)
"""

import json
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel

from .. import config
from ..clientes import config_do_cliente
from ..dataserver.base import normalizar_e_validar
from ..dataserver.glb_usuario import gerar_payload as gerar_payload_glb_usuario
from ..dataserver.lote import LoteInvalido, processar_lote
from ..dataserver.registro import MODULOS
from ..registro_uso import registrar_uso
from ..seguranca import CLIENTE_INTERNO, identificar_cliente

router = APIRouter(prefix="/dataserver", tags=["dataserver"])

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

PASTA_GOOGLE_SHEETS = config.BASE_DIR / "google-sheets"
_RE_BASE_URL = re.compile(r"^https?://[A-Za-z0-9.\-]+(:\d+)?$")


class PedidoGerar(BaseModel):
    operacao: str = "incluir"
    valores: dict = {}
    cliente: str | None = None  # código do cliente (config); ignorado se a chave de API já define um


class PedidoLote(BaseModel):
    operacao: str = "incluir"
    texto: str = ""  # tabela colada do Excel/Sheets ou conteúdo do CSV
    cliente: str | None = None


def _modulo(chave: str):
    modulo = MODULOS.get(chave)
    if modulo is None:
        raise HTTPException(status_code=404, detail=f"Módulo '{chave}' não encontrado.")
    return modulo


def _cliente_efetivo(autenticado: str, informado: str | None) -> str | None:
    """
    Com chave de API válida, o cliente é o da chave (um cliente não consegue
    ler a configuração de outro). Sem chave (uso interno), vale o informado.
    """
    if autenticado != CLIENTE_INTERNO:
        return autenticado
    return (informado or "").strip()[:50] or None


@router.get("/modulos")
def listar_modulos(cliente: str | None = None, autenticado: str = Depends(identificar_cliente)):
    """Módulos e seus campos -- a tela e o Google Sheets se montam a partir disso."""
    codigo = _cliente_efetivo(autenticado, cliente)
    return [m.para_dict(config_do_cliente(codigo, m.chave)) for m in MODULOS.values()]


@router.get("/google-sheets/script")
def script_google_sheets(base: str, autenticado: str = Depends(identificar_cliente)):
    """Código do Apps Script (Codigo.gs) já apontando pro endereço desta API."""
    if not _RE_BASE_URL.match(base):
        raise HTTPException(status_code=400, detail="Parâmetro 'base' inválido (use https://dominio).")
    arquivo = PASTA_GOOGLE_SHEETS / "Codigo.gs"
    if not arquivo.is_file():
        raise HTTPException(status_code=404, detail="Script do Google Sheets não encontrado no servidor.")
    conteudo = arquivo.read_text(encoding="utf-8").replace("__API_BASE__", base)
    return Response(content=conteudo, media_type="text/plain; charset=utf-8")


@router.get("/google-sheets/manifesto")
def manifesto_google_sheets(autenticado: str = Depends(identificar_cliente)):
    """appsscript.json (permissões mínimas do script)."""
    arquivo = PASTA_GOOGLE_SHEETS / "appsscript.json"
    if not arquivo.is_file():
        raise HTTPException(status_code=404, detail="Manifesto não encontrado no servidor.")
    return Response(content=arquivo.read_text(encoding="utf-8"), media_type="application/json; charset=utf-8")


@router.get("/{chave}/modelo-csv")
def modelo_csv(chave: str, autenticado: str = Depends(identificar_cliente)):
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
def gerar_lote(
    chave: str, pedido: PedidoLote, tarefas: BackgroundTasks,
    autenticado: str = Depends(identificar_cliente),
):
    modulo = _modulo(chave)
    if pedido.operacao not in modulo.operacoes:
        raise HTTPException(status_code=422, detail=f"Operação inválida: {pedido.operacao!r}.")
    cliente = _cliente_efetivo(autenticado, pedido.cliente)
    try:
        resultado = processar_lote(
            modulo, pedido.texto, pedido.operacao, _GERADORES[chave], config_do_cliente(cliente, chave)
        )
    except LoteInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Log só com contagens: a planilha pode ter dados pessoais.
    tarefas.add_task(
        registrar_uso, "dataserver", "gerar-lote",
        {"modulo": chave, "operacao": pedido.operacao, "cliente": cliente or autenticado,
         "versao_schema": modulo.versao_schema, "total": resultado["total"],
         "validos": resultado["validos"], "invalidos": resultado["invalidos"]},
    )
    return resultado


@router.post("/{chave}/validar")
def validar(chave: str, pedido: PedidoGerar, autenticado: str = Depends(identificar_cliente)):
    modulo = _modulo(chave)
    cfg = config_do_cliente(_cliente_efetivo(autenticado, pedido.cliente), chave)
    normalizados, erros = normalizar_e_validar(modulo, pedido.valores, pedido.operacao, cfg)
    avisos = modulo.avisos(normalizados, pedido.operacao) if not erros else []
    return {"valido": not erros, "erros": erros, "avisos": avisos, "versao_schema": modulo.versao_schema}


@router.post("/{chave}/gerar")
def gerar(
    chave: str, pedido: PedidoGerar, tarefas: BackgroundTasks,
    autenticado: str = Depends(identificar_cliente),
):
    modulo = _modulo(chave)
    cliente = _cliente_efetivo(autenticado, pedido.cliente)
    normalizados, erros = normalizar_e_validar(
        modulo, pedido.valores, pedido.operacao, config_do_cliente(cliente, chave)
    )
    detalhes = {"modulo": chave, "operacao": pedido.operacao, "cliente": cliente or autenticado,
                "versao_schema": modulo.versao_schema}
    if erros:
        tarefas.add_task(registrar_uso, "dataserver", "gerar", {**detalhes, "erros": len(erros)}, False)
        raise HTTPException(status_code=422, detail={"erros": erros})

    payload = _GERADORES[chave](normalizados)
    entrega = modulo.entrega(payload, pedido.operacao)
    tarefas.add_task(registrar_uso, "dataserver", "gerar", detalhes)
    return {
        "versao_schema": modulo.versao_schema,
        "payload": payload,
        "json": json.dumps(payload, ensure_ascii=False, indent=2),
        "avisos": modulo.avisos(normalizados, pedido.operacao),
        "nome_arquivo": entrega.get("nome_arquivo", f"{modulo.dataserver}.json"),
        "instrucoes": entrega.get("instrucoes", []),
    }
