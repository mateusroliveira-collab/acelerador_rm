"""
Link da planilha-modelo (Google Sheets) de cada módulo.

A planilha fica no Google Drive de quem administra o projeto; o link vem de
uma variável de ambiente (trocável no console da Vercel, sem mexer em código):

  PLANILHA_MODELO_GLB_USUARIO = https://docs.google.com/spreadsheets/d/<ID>/edit...

O app devolve o link no formato ".../copy", que abre direto a tela
"Fazer uma cópia" do Google. Não há credencial: é só um endereço, e o próprio
Google decide quem pode abrir (a planilha precisa estar compartilhada como
"qualquer pessoa com o link pode ver").
"""

import os
import re

_RE_PLANILHA = re.compile(r"^https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{20,})")


def _nome_variavel(chave_modulo: str) -> str:
    return "PLANILHA_MODELO_" + chave_modulo.upper().replace("-", "_")


def url_copia_planilha_modelo(chave_modulo: str) -> str | None:
    """Link "fazer uma cópia" da planilha do módulo, ou None se não configurada/inválida."""
    bruto = os.environ.get(_nome_variavel(chave_modulo), "").strip()
    m = _RE_PLANILHA.match(bruto)
    if not m:
        return None  # só aceita endereços de planilha do Google
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/copy"
