"""
Links da planilha-modelo (Google Sheets) de cada módulo.

A planilha fica no Google Drive de quem administra o projeto; o link vem de
uma variável de ambiente (trocável no console da Vercel, sem mexer em código):

  PLANILHA_MODELO_GLB_USUARIO = https://docs.google.com/spreadsheets/d/<ID>/edit...

A partir dele o app monta:
  - "copiar": abre a tela "Fazer uma cópia" do Google (cada clique gera uma
    planilha separada, na conta de quem clicou -- exige conta Google);
  - "baixar_xlsx": baixa o modelo como Excel, sem precisar de conta Google.

Não há credencial: são só endereços, e o próprio Google decide quem pode abrir
(a planilha precisa estar compartilhada como "qualquer pessoa com o link pode ver").
"""

import os
import re

_RE_PLANILHA = re.compile(r"^https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{20,})")


def _nome_variavel(chave_modulo: str) -> str:
    return "PLANILHA_MODELO_" + chave_modulo.upper().replace("-", "_")


def _id_planilha(chave_modulo: str) -> str | None:
    bruto = os.environ.get(_nome_variavel(chave_modulo), "").strip()
    m = _RE_PLANILHA.match(bruto)  # só aceita endereços de planilha do Google
    return m.group(1) if m else None


def links_planilha_modelo(chave_modulo: str) -> dict | None:
    """{"copiar": url, "baixar_xlsx": url} ou None se não configurada/inválida."""
    id_ = _id_planilha(chave_modulo)
    if not id_:
        return None
    base = f"https://docs.google.com/spreadsheets/d/{id_}"
    return {"copiar": f"{base}/copy", "baixar_xlsx": f"{base}/export?format=xlsx"}


def url_copia_planilha_modelo(chave_modulo: str) -> str | None:
    """Compatibilidade: link "fazer uma cópia" ou None."""
    links = links_planilha_modelo(chave_modulo)
    return links["copiar"] if links else None
