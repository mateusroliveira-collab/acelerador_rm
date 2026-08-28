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

# Cada grupo tem: o nome exato da pasta em disco, um "label" curto (nome
# de negócio, usado nas abas do front) e uma "descricao" mais completa
# (usada como dica/tooltip). Fonte: classificação oficial TOTVS de tipos
# de movimento do RM (Gestão de Compras, Estoque e Faturamento).
GRUPOS: dict[str, dict[str, str | None]] = {
    "1.1": {
        "pasta": "Movimentos do tipo 1.1",
        "label": "Pedido/Solicitação de Compra",
        "descricao": (
            "Movimentos de pedidos ou solicitações de compra, sem efeito "
            "fiscal -- fase inicial do processo de suprimentos (cotação, "
            "solicitação, pedido de compra). Não emite nota fiscal."
        ),
    },
    "1.2": {
        "pasta": "Movimentos do tipo 1.2",
        "label": "Nota Fiscal de Entrada",
        "descricao": (
            "Recebimento fiscal de mercadoria ou serviço -- notas fiscais "
            "de fornecedores, importação, devolução de vendas. Alimenta o "
            "estoque e gera contas a pagar."
        ),
    },
    "2.1": {
        "pasta": "Movimentos do tipo 2.1",
        "label": "Pedido de Venda/Orçamento",
        "descricao": (
            "Pedidos de venda, orçamentos, bonificações ou ordens de "
            "produção, sem efeito fiscal -- reserva estoque ou inicia "
            "processo comercial. Não emite nota fiscal."
        ),
    },
    "2.2": {
        "pasta": "Movimento do tipo 2.2",
        "label": "Nota Fiscal de Saída",
        "descricao": (
            "Faturamento efetivo -- notas fiscais de venda, prestação de "
            "serviço, remessa para conserto, devolução a fornecedor. Gera "
            "impostos (SEFAZ) e contas a receber."
        ),
    },
    "3.1": {
        "pasta": "Movimento do tipo 3.1",
        "label": "Transferência entre Filiais/Locais",
        "descricao": (
            "Movimentação física de mercadoria entre locais de estoque ou "
            "filiais da mesma coligada, mantendo o controle patrimonial "
            "interno. Pode ou não emitir nota fiscal, dependendo da "
            "configuração jurídica exigida."
        ),
    },
    "4.1": {
        "pasta": "Movimento do tipo 4.1",
        "label": "Movimento Interno de Estoque",
        "descricao": (
            "Movimentações internas, sem cliente ou fornecedor externo -- "
            "requisição de material para consumo, baixa por perda/avaria, "
            "inventário (acerto de saldo) ou consumo de matéria-prima na "
            "produção."
        ),
    },
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