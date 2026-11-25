"""
Modo lote do gerador de DataServer: uma tabela (colada do Excel ou CSV)
vira vários registros, validados linha a linha.

Genérico: serve a qualquer módulo (GlbUsuarioData agora; Educacional e os
demais depois). Tudo em memória -- nada do que vem na planilha (que pode
ter dados pessoais) é gravado em banco ou log.
"""

import csv
import io
import json
import re
import unicodedata
from typing import Callable

from .base import DATA, Modulo, envelope_get, normalizar_e_validar, registro_completo
from .xml_saida import gerar_xml

MAX_LINHAS = 500
MAX_CARACTERES = 1_000_000

_RE_DATA_BR = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$")


class LoteInvalido(ValueError):
    """Entrada do lote inutilizável como um todo (vazia, grande demais, sem cabeçalho)."""


def _chave(texto: str) -> str:
    """'E-Mail' / 'EMAIL' / 'e mail' -> 'email' (sem acento, só letras e dígitos)."""
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def parsear_tabela(texto: str) -> tuple[list[str], list[list[str]]]:
    """Detecta o separador (tab, ; ou ,) e devolve (cabeçalhos, linhas não vazias)."""
    texto = (texto or "").lstrip("﻿")
    if len(texto) > MAX_CARACTERES:
        raise LoteInvalido("Arquivo muito grande (limite de ~1 MB de texto).")
    if not texto.strip():
        raise LoteInvalido("Nenhum dado informado.")

    primeira = texto.splitlines()[0]
    sep = max(("\t", ";", ","), key=primeira.count)
    if primeira.count(sep) == 0:
        sep = ";"  # tabela de uma coluna só
    linhas = [
        [c.strip() for c in linha]
        for linha in csv.reader(io.StringIO(texto), delimiter=sep)
        if any(c.strip() for c in linha)
    ]
    if len(linhas) < 2:
        raise LoteInvalido("Informe o cabeçalho e pelo menos uma linha de dados.")
    if len(linhas) - 1 > MAX_LINHAS:
        raise LoteInvalido(f"Máximo de {MAX_LINHAS} linhas por lote (recebi {len(linhas) - 1}).")
    return linhas[0], linhas[1:]


def mapear_colunas(modulo: Modulo, cabecalhos: list[str]) -> tuple[dict[int, str], list[str]]:
    """Casa cada coluna com um campo (pelo nome técnico ou pelo rótulo). Devolve (mapa, ignoradas)."""
    por_chave = {}
    for c in modulo.campos:
        por_chave[_chave(c.nome)] = c.nome
        por_chave[_chave(c.rotulo)] = c.nome
    mapa: dict[int, str] = {}
    ignoradas: list[str] = []
    usados: set[str] = set()
    for i, cab in enumerate(cabecalhos):
        nome = por_chave.get(_chave(cab))
        if nome and nome not in usados:
            mapa[i] = nome
            usados.add(nome)
        elif cab:
            ignoradas.append(cab)
    return mapa, ignoradas


def processar_lote(
    modulo: Modulo,
    texto: str,
    operacao: str,
    gerar_payload: Callable[[dict], dict],
    config: dict | None = None,
) -> dict:
    cabecalhos, linhas = parsear_tabela(texto)
    mapa, ignoradas = mapear_colunas(modulo, cabecalhos)
    if not mapa:
        raise LoteInvalido(
            "Não reconheci nenhuma coluna. Use o modelo de CSV: o cabeçalho precisa "
            "ter os nomes dos campos (ex.: CODUSUARIO) ou os rótulos da tela."
        )
    tipo_campo = {c.nome: c.tipo for c in modulo.campos}
    avisos_gerais = []
    if ignoradas:
        avisos_gerais.append("Colunas ignoradas (não fazem parte do módulo): " + ", ".join(ignoradas) + ".")
    ausentes = [c.rotulo for c in modulo.campos if c.obrigatorio and c.padrao is None and c.nome not in mapa.values()]
    if ausentes:
        avisos_gerais.append("Faltam colunas obrigatórias: " + ", ".join(ausentes) + ".")

    resultado_linhas = []
    payloads: list[dict] = []
    vistos: dict[str, int] = {}
    for n, celulas in enumerate(linhas, start=2):  # 1 = cabeçalho; número da linha como na planilha
        valores: dict = {}
        for idx, nome in mapa.items():
            v = celulas[idx] if idx < len(celulas) else ""
            if tipo_campo[nome] == DATA:
                m = _RE_DATA_BR.match(v)
                if m:  # Excel brasileiro: 18/11/2026 -> 2026-11-18
                    v = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
            if v != "":  # célula vazia deixa valer o padrão do campo
                valores[nome] = v
        normalizados, erros = normalizar_e_validar(modulo, valores, operacao, config)

        chave_reg = None
        if modulo.campo_chave and normalizados.get(modulo.campo_chave):
            chave_reg = str(normalizados[modulo.campo_chave])
            anterior = vistos.get(chave_reg.lower())
            if anterior is not None:
                erros.append({
                    "campo": modulo.campo_chave,
                    "mensagem": f"Repetido no arquivo (já aparece na linha {anterior}).",
                })
            else:
                vistos[chave_reg.lower()] = n

        avisos = modulo.avisos(normalizados, operacao) if not erros else []
        if not erros:
            payloads.append(gerar_payload(normalizados))
        resultado_linhas.append({
            "linha": n, "chave": chave_reg, "valido": not erros, "erros": erros, "avisos": avisos,
        })

    validos = len(payloads)
    saida = {
        "versao_schema": modulo.versao_schema,
        "total": len(linhas),
        "validos": validos,
        "invalidos": len(linhas) - validos,
        "avisos_gerais": avisos_gerais,
        "linhas": resultado_linhas,
    }
    if payloads:
        nome_base = f"{modulo.dataserver}_{operacao}_lote"
        # Envio (conector e script): um registro por chamada, só o que foi preenchido.
        saida["registros"] = payloads
        saida["jsonl"] = "\n".join(json.dumps(p, ensure_ascii=False) for p in payloads) + "\n"
        # JSON para baixar: o mesmo formato do GET do RM (envelope + todas as chaves).
        completos = [registro_completo(modulo, p) for p in payloads]
        saida["json"] = json.dumps(envelope_get(completos), ensure_ascii=False, indent=2)
        saida["nome_arquivo"] = f"{nome_base}.jsonl"
        xml = gerar_xml(modulo, payloads)
        if xml:
            saida["xml"] = xml
            saida["nome_arquivo_xml"] = f"{nome_base}.xml"
        saida["instrucoes"] = modulo.entrega_lote(operacao, f"{nome_base}.jsonl", validos)
    return saida
