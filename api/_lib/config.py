"""
Configuração central do módulo de XML.

Mantém num só lugar: onde a base de XMLs "originais" fica no projeto,
e quais grupos de movimento existem. Se amanhã os nomes das pastas
mudarem ou entrar um grupo novo, é só mexer aqui -- o resto do código
não precisa saber desses detalhes.
"""

from pathlib import Path

# Raiz do projeto = 3 níveis acima deste arquivo
# (api/_lib/config.py -> api/_lib -> api -> raiz)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Onde os XMLs "originais" (antes da limpeza) ficam, versionados no Git.
XML_BASE_DIR = BASE_DIR / "data" / "xml_base"

# Cada grupo tem: o nome exato da pasta em disco (igual ao que já existia
# no Drive) e um "label" com o nome de negócio -- preencha assim que
# definirmos o que cada grupo significa (ex: "Entrada de compra").
GRUPOS: dict[str, dict[str, str | None]] = {
    "1.1": {"pasta": "Movimentos do tipo 1.1", "label": None},
    "1.2": {"pasta": "Movimentos do tipo 1.2", "label": None},
    "2.1": {"pasta": "Movimentos do tipo 2.1", "label": None},
    "2.2": {"pasta": "Movimento do tipo 2.2", "label": None},
    "3.1": {"pasta": "Movimento do tipo 3.1", "label": None},
    "4.1": {"pasta": "Movimento do tipo 4.1", "label": None},
}


def pasta_do_grupo(grupo: str) -> Path:
    """Caminho da pasta de um grupo específico dentro da base de XMLs."""
    info = GRUPOS.get(grupo)
    if info is None:
        raise ValueError(f"Grupo desconhecido: {grupo}")
    return XML_BASE_DIR / info["pasta"]


def grupo_existe(grupo: str) -> bool:
    """Confere se o código do grupo é um dos conhecidos."""
    return grupo in GRUPOS