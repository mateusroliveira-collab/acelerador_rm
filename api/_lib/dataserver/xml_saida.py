"""
Saída em XML (DataSet do RM) a partir dos mesmos payloads do JSON.

ATENÇÃO: o formato foi INFERIDO do padrão de DataSet do RM (elemento raiz = nome
do DataServer sem o sufixo "Data"; um elemento por linha da tabela, com um
elemento filho por campo). Não foi confirmado contra um SaveRecord real: valide
em homologação antes de usar em volume.
"""

from xml.sax.saxutils import escape

from .base import Modulo


def gerar_xml(modulo: Modulo, payloads: list[dict]) -> str | None:
    if not modulo.tabela_xml or not payloads:
        return None
    raiz = modulo.dataserver.removesuffix("Data")
    saida = ['<?xml version="1.0" encoding="utf-8"?>', f"<{raiz}>"]
    for p in payloads:
        saida.append(f"  <{modulo.tabela_xml}>")
        for campo, valor in p.items():
            saida.append(f"    <{campo}>{escape(str(valor))}</{campo}>")
        saida.append(f"  </{modulo.tabela_xml}>")
    saida.append(f"</{raiz}>")
    return "\n".join(saida) + "\n"
