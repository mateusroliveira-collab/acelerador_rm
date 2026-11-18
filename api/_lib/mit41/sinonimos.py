"""
Dicionário de sinônimos e busca de termos para o matcher de MIT 41.

Determinístico, sem IA: cada conceito de negócio (entrada, saída,
transferência, movimento interno) tem uma lista de termos com PESO --
termos específicos ("transferência entre filiais") valem mais que os
genéricos ("filial"). A busca é, nesta ordem:

 1. exata, com limite de palavra (\\b) e tolerância a plural
    ("requisição" casa "requisições", "material" casa "materiais");
 2. aproximada (difflib, da biblioteca padrão -- sem dependência nova),
    só pra termos com 6+ letras, mesma letra inicial e similaridade alta,
    pra pegar erro de digitação ("tranferencia") sem criar falso positivo.

Pra ajustar o matcher, o caminho é editar este arquivo (termos e pesos).
"""

import difflib
import re
import unicodedata
from functools import lru_cache

# Similaridade mínima (0 a 1) da busca aproximada.
LIMIAR_APROXIMADO = 0.86
# Tamanho mínimo (sem espaços) do termo pra tentar a busca aproximada.
TAMANHO_MIN_APROXIMADO = 6

# conceito -> {termo (sem acento, minúsculo, hífen vira espaço): peso}
CONCEITOS: dict[str, dict[str, int]] = {
    "entrada": {
        "compra": 2, "fornecedor": 2, "aquisicao": 2, "importacao": 2,
        "ordem de compra": 3, "pedido de compra": 3, "solicitacao de compra": 3,
        "nota fiscal de entrada": 3, "recebimento": 2,
    },
    "saida": {
        "venda": 2, "cliente": 2, "faturamento": 2, "expedicao": 2, "remessa": 2,
        "pedido de venda": 3, "nota fiscal de saida": 3,
    },
    "transferencia": {
        "transferencia": 3, "filial": 3, "outro local": 3, "outra filial": 3,
        "transferencia entre filiais": 4, "entre filiais": 4,
        "transferencia entre locais": 4,
    },
    "interno": {
        "requisicao de material": 3, "requisicao de consumo": 3, "requisicao interna": 3,
        "consumo": 3, "baixa": 3, "perda": 3, "avaria": 3,
        "baixa de estoque": 4, "ajuste de estoque": 4, "inventario": 3,
        "contagem fisica": 3, "producao": 3, "materia prima": 3,
    },
}

ROTULOS = {
    "entrada": "entrada/compra",
    "saida": "saída/venda",
    "transferencia": "transferência",
    "interno": "movimento interno",
}

DEVOLUCAO = ("devolucao",)
# Com devolução, o que importa é DE QUÊ é a devolução (muda a direção).
DEVOLUCAO_DE_COMPRA = ("compra", "fornecedor")
DEVOLUCAO_DE_VENDA = ("venda", "cliente")


def normalizar_texto(texto: str | None) -> str:
    """Minúsculas, sem acentos, pontuação vira espaço: 'Matéria-prima' -> 'materia prima'."""
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _padrao_palavra(palavra: str) -> str:
    """Palavra + variações de plural (requisicao->requisicoes, material->materiais)."""
    if palavra.endswith("ao"):
        return palavra[:-2] + "(?:ao|aos|oes)"
    if palavra.endswith(("al", "el", "ol")):
        return palavra[:-1] + "(?:l|is)"
    return palavra + "(?:s|es)?"


@lru_cache(maxsize=None)
def _regex_termo(termo: str) -> re.Pattern:
    corpo = r"\s+".join(_padrao_palavra(p) for p in termo.split())
    return re.compile(r"\b" + corpo + r"\b")


def achar_termo(termo: str, texto_normalizado: str) -> tuple[str, str] | None:
    """
    Procura o termo no texto (já normalizado). Devolve ("exato"|"aproximado",
    trecho encontrado) ou None.
    """
    m = _regex_termo(termo).search(texto_normalizado)
    if m:
        return "exato", m.group(0)

    if len(termo.replace(" ", "")) < TAMANHO_MIN_APROXIMADO:
        return None
    n = len(termo.split())
    tokens = texto_normalizado.split()
    melhor: tuple[float, str] | None = None
    for i in range(len(tokens) - n + 1):
        candidato = " ".join(tokens[i : i + n])
        if candidato[0] != termo[0] or abs(len(candidato) - len(termo)) > 3:
            continue
        razao = difflib.SequenceMatcher(None, termo, candidato).ratio()
        if razao >= LIMIAR_APROXIMADO and (melhor is None or razao > melhor[0]):
            melhor = (razao, candidato)
    return ("aproximado", melhor[1]) if melhor else None


def tem_algum(termos: tuple[str, ...], texto_normalizado: str) -> bool:
    return any(achar_termo(t, texto_normalizado) for t in termos)
