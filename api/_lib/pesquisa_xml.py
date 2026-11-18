"""
Pesquisa global de XMLs (todos os grupos) por código e descrição.

Lógica pura e determinística, sem acesso ao banco: o roteador injeta os
XMLs contribuídos. O "código" do movimento é o prefixo numérico do nome
do arquivo ("1.1.01-Requisição..." ou "1101-Solicitação...") e a
descrição é o resto do nome.
"""

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from . import config

LIMITE_RESULTADOS = 200

_RE_CODIGO_NO_NOME = re.compile(r"^\s*(\d[\d.]*)")
_RE_TOKEN_CODIGO = re.compile(r"^\d[\d.]*$")


def normalizar(texto: str | None) -> str:
    """Minúsculas e sem acentos: 'Requisição' -> 'requisicao'."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


def _so_digitos(texto: str) -> str:
    return "".join(c for c in texto if c.isdigit())


@dataclass(frozen=True)
class ItemXml:
    grupo: str
    nome: str  # nome do arquivo (como aparece na lista do grupo)
    personalizado: bool = False
    id: int | None = None

    @property
    def codigo(self) -> str:
        m = _RE_CODIGO_NO_NOME.match(self.nome)
        return m.group(1).rstrip(".") if m else ""


@lru_cache(maxsize=1)
def indice_base_fixa() -> tuple[ItemXml, ...]:
    """
    XMLs fixos de todos os grupos. Os arquivos são versionados no Git (só
    mudam com deploy), então a leitura das pastas é feita uma vez por
    processo em vez de a cada tecla digitada.
    """
    itens: list[ItemXml] = []
    for grupo in config.GRUPOS:
        pasta = config.pasta_do_grupo(grupo)
        if not pasta.exists():
            continue
        for f in sorted(pasta.iterdir(), key=lambda p: p.name):
            if f.is_file() and f.suffix.lower() == ".xml":
                itens.append(ItemXml(grupo=grupo, nome=f.name))
    return tuple(itens)


def _casa(item: ItemXml, tokens: list[str]) -> bool:
    nome_norm = normalizar(item.nome)
    digitos_codigo = _so_digitos(item.codigo)
    for tok in tokens:
        if tok in nome_norm:
            continue
        # Código com ou sem pontos: "1.1.01" também acha "1101-...".
        if _RE_TOKEN_CODIGO.match(tok) and digitos_codigo.startswith(_so_digitos(tok)):
            continue
        return False
    return True


def pesquisar(consulta: str, personalizados: list[ItemXml] | None = None) -> list[ItemXml]:
    """
    Todas as palavras da consulta precisam casar (AND, em qualquer
    ordem), ignorando acentos e maiúsculas. Palavras numéricas também
    casam por prefixo do código, ignorando os pontos.
    """
    tokens = normalizar(consulta).split()
    if not tokens:
        return []
    ordem = {g: i for i, g in enumerate(config.GRUPOS)}
    todos = list(indice_base_fixa()) + sorted(
        personalizados or [], key=lambda i: (ordem.get(i.grupo, 99), -(i.id or 0))
    )
    achados = [i for i in todos if _casa(i, tokens)]
    # Ordena por grupo mantendo a ordem original dentro de cada um
    # (fixos em ordem alfabética, depois os contribuídos).
    achados.sort(key=lambda i: ordem.get(i.grupo, 99))
    return achados
