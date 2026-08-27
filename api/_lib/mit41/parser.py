"""
Parser da saída do Interpretador de MIT 41 (o Gem do Gemini).

O analista usa o Gem no app do Gemini (fora desse sistema, de propósito
-- ver CONTEXTO_PROJETO.md seção 4) e cola aqui um trecho da resposta.
Essa resposta é estruturada em blocos tipo:

    [INICIO_MOVIMENTO]
    PROCESSO_ORIGEM=Requisição de Compra
    PROCESSO_DESTINO=Nota Fiscal de Entrada
    [ESTOQUE] EFEITO_ESTOQUE=Aumenta, LOCAL_ORIGEM=Fornecedor, ...
    [FIM_MOVIMENTO]

Esse parser não presume um layout rígido de linha -- aceita campo por
linha OU vários campos separados por vírgula na mesma linha, porque o
Gem pode variar isso um pouco entre respostas.
"""

import re

# Acha qualquer "CAMPO=valor", parando no próximo CAMPO=, numa vírgula
# antes dele, numa tag [ALGO], ou no fim do texto.
_PADRAO_CAMPO = re.compile(
    r"([A-Z][A-Z0-9_]*)\s*=\s*(.*?)(?=(?:,\s*)?[A-Z][A-Z0-9_]*\s*=|\[|\Z)",
    re.DOTALL,
)


def parsear_mit41(texto: str) -> dict[str, str]:
    """
    Extrai os campos "CAMPO=valor" de um trecho da saída do interpretador.
    Devolve só os campos que têm valor de verdade (ignora campo vazio,
    que é como o Gem sinaliza "não informado no documento").
    """
    campos: dict[str, str] = {}
    for match in _PADRAO_CAMPO.finditer(texto):
        chave = match.group(1).strip()
        valor = match.group(2).strip().rstrip(",").strip()
        if valor:
            campos[chave] = valor
    return campos
