"""
Rotas do gerador de payload de DataServer.

SÓ gera e valida: não conecta ao RM e não guarda nada. Os valores digitados
(que podem ser dados pessoais) não vão pro banco nem pro log de uso -- o
log guarda apenas módulo, operação, cliente, versão do schema e contagens.

Montado em dois prefixos (ver api/index.py):
  /api/v1/dataserver/...  -> versão canônica (a tela usa)
  /api/dataserver/...     -> alias de compatibilidade (fora da documentação)
"""

import base64
import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from ..clientes import config_do_cliente
from ..dataserver.base import envelope_get, normalizar_e_validar, registro_completo
from ..dataserver.glb_usuario import gerar_payload as gerar_payload_glb_usuario
from ..dataserver.lote import LoteInvalido, processar_lote
from ..dataserver.planilha import links_planilha_modelo
from ..dataserver import xlsx as planilha_xlsx
from ..dataserver.registro import MODULOS
from ..registro_uso import registrar_uso
from ..seguranca import CLIENTE_INTERNO, identificar_cliente

router = APIRouter(prefix="/dataserver", tags=["dataserver"])

# Gerador de payload de cada módulo: (valores normalizados) -> dict.
_GERADORES = {"glb-usuario": gerar_payload_glb_usuario}

# Linha fictícia do CSV de modelo, por módulo (valores no formato do RM, como no GET).
_EXEMPLOS_LOTE = {
    "glb-usuario": {
        "CODUSUARIO": "usuario.exemplo", "NOME": "Usuário de Exemplo",
        "EMAIL": "usuario.exemplo@exemplo.com", "CODACESSO": "Acesso01",
        "STATUS": "1", "OIDC_ENABLED": "0", "OBRIGAALTERARSENHA": "1",
        "DATAINICIO": "01/01/2026", "IGNORARAUTENTICACAOLDAP": "F",
    },
}


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
    """Módulos e seus campos -- a tela se monta a partir disso."""
    codigo = _cliente_efetivo(autenticado, cliente)
    resposta = []
    for m in MODULOS.values():
        links = links_planilha_modelo(m.chave) or {}
        resposta.append({
            **m.para_dict(config_do_cliente(codigo, m.chave)),
            "planilha_modelo_url": links.get("copiar"),  # "fazer uma cópia" (conta Google)
            "planilha_modelo_xlsx_url": links.get("baixar_xlsx"),  # download em Excel
        })
    return resposta


@router.get("/{chave}/modelo-xlsx")
def modelo_xlsx(chave: str, cliente: str | None = None, autenticado: str = Depends(identificar_cliente)):
    """Modelo Excel (.xlsx) para o analista entregar ao cliente. Com `cliente`, já vem com os códigos de acesso dele."""
    modulo = _modulo(chave)
    cfg = config_do_cliente(_cliente_efetivo(autenticado, cliente), chave)
    conteudo = planilha_xlsx.gerar_modelo_xlsx(modulo, cfg)
    return Response(
        content=conteudo,
        media_type=planilha_xlsx.TIPO_MIME,
        headers={"Content-Disposition": f'attachment; filename="{modulo.dataserver}_modelo.xlsx"'},
    )


@router.post("/{chave}/lote-xlsx")
async def gerar_lote_xlsx(
    chave: str, tarefas: BackgroundTasks, arquivo: UploadFile = File(...),
    operacao: str = "incluir", cliente: str | None = None,
    autenticado: str = Depends(identificar_cliente),
):
    """Valida a planilha .xlsx preenchida. Se houver erros, devolve também a planilha marcada (base64)."""
    modulo = _modulo(chave)
    if operacao not in modulo.operacoes:
        raise HTTPException(status_code=422, detail=f"Operação inválida: {operacao!r}.")
    codigo = _cliente_efetivo(autenticado, cliente)
    conteudo = await arquivo.read(planilha_xlsx.MAX_BYTES + 1)
    try:
        resultado, _ = planilha_xlsx.processar_planilha(
            modulo, conteudo, operacao, _GERADORES[chave], config_do_cliente(codigo, chave)
        )
        if resultado["invalidos"] > 0:
            marcada = planilha_xlsx.anotar_planilha(conteudo, modulo, resultado)
            resultado["anotado_b64"] = base64.b64encode(marcada).decode("ascii")
            resultado["nome_arquivo_anotado"] = f"{modulo.dataserver}_com_erros.xlsx"
    except (planilha_xlsx.XlsxInvalido, LoteInvalido) as e:
        raise HTTPException(status_code=400, detail=str(e))
    tarefas.add_task(
        registrar_uso, "dataserver", "gerar-lote-xlsx",
        {"modulo": chave, "operacao": operacao, "cliente": codigo or autenticado,
         "versao_schema": modulo.versao_schema, "total": resultado["total"],
         "validos": resultado["validos"], "invalidos": resultado["invalidos"]},
    )
    return resultado


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
    nome_arquivo = entrega.get("nome_arquivo", f"{modulo.dataserver}.json")
    return {
        "versao_schema": modulo.versao_schema,
        "payload": payload,  # corpo do envio (POST/PUT): só o que foi preenchido
        "json_envio": json.dumps(payload, ensure_ascii=False, indent=2),
        "nome_arquivo_envio": entrega.get("nome_arquivo_envio", nome_arquivo.replace(".json", "_envio.json")),
        # JSON no mesmo formato do GET do RM (envelope + todas as chaves, na ordem)
        "json": json.dumps(envelope_get([registro_completo(modulo, payload)]), ensure_ascii=False, indent=2),
        "avisos": modulo.avisos(normalizados, pedido.operacao),
        "nome_arquivo": nome_arquivo,
        "instrucoes": entrega.get("instrucoes", []),
    }
