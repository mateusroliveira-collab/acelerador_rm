"""
Sugere qual(is) grupo(s) de movimento (1.1 a 4.1) correspondem aos campos
extraídos da saída do interpretador de MIT 41.

NÃO é machine learning nem IA -- é um conjunto de regras baseadas no que
cada grupo significa de negócio (ver api/_lib/config.py). Cada grupo
recebe uma pontuação, e o resultado mostra os SINAIS que levaram a essa
pontuação -- o analista vê o porquê, não uma caixa preta, e confirma
antes de usar.
"""

PALAVRAS_ENTRADA = ["compra", "fornecedor", "aquisição", "importação"]
PALAVRAS_SAIDA = ["venda", "cliente", "faturamento", "expedição", "remessa"]
PALAVRAS_TRANSFERENCIA = ["transferência", "transferencia", "filial", "outro local", "outra filial"]
PALAVRAS_INTERNO = [
    "requisição de material", "requisição de consumo", "requisição interna",
    "consumo", "baixa", "perda", "avaria",
    "inventário", "inventario", "produção", "producao", "matéria-prima", "materia-prima",
]

# Valores que significam "não tem documento fiscal", pra não confundir
# com um valor de verdade preenchido.
_VALORES_SEM_DOC_FISCAL = {"", "não", "nao", "n/a", "na", "nenhum", "não informado", "nao informado"}


def sugerir_grupos(campos: dict[str, str]) -> list[dict]:
    """
    Recebe os campos já extraídos (ver parser.py) e devolve uma lista de
    sugestões, ordenada da mais provável pra menos provável, cada uma com
    os sinais que levaram àquela pontuação.
    """
    texto_processo = " ".join(
        [campos.get("PROCESSO_ORIGEM", ""), campos.get("PROCESSO_DESTINO", "")]
    ).lower()

    doc_fiscal = campos.get("DOCUMENTO_FISCAL", "").strip().lower()
    tem_doc_fiscal = doc_fiscal not in _VALORES_SEM_DOC_FISCAL

    local_origem = campos.get("LOCAL_ORIGEM", "").strip()
    local_destino = campos.get("LOCAL_DESTINO", "").strip()

    pontuacoes: dict[str, int] = {g: 0 for g in ("1.1", "1.2", "2.1", "2.2", "3.1", "4.1")}
    sinais: dict[str, list[str]] = {g: [] for g in pontuacoes}

    def pontuar(grupo: str, pontos: int, motivo: str):
        pontuacoes[grupo] += pontos
        sinais[grupo].append(motivo)

    # Direção: entrada (compra) ou saída (venda), via palavra-chave no processo
    if any(p in texto_processo for p in PALAVRAS_ENTRADA):
        pontuar("1.1", 2, "Processo menciona termo de entrada/compra")
        pontuar("1.2", 2, "Processo menciona termo de entrada/compra")
    if any(p in texto_processo for p in PALAVRAS_SAIDA):
        pontuar("2.1", 2, "Processo menciona termo de saída/venda")
        pontuar("2.2", 2, "Processo menciona termo de saída/venda")
    if any(p in texto_processo for p in PALAVRAS_TRANSFERENCIA):
        pontuar("3.1", 3, "Processo menciona termo de transferência")
    if any(p in texto_processo for p in PALAVRAS_INTERNO):
        pontuar("4.1", 3, "Processo menciona termo de movimento interno")

    # Documento fiscal separa "sem efeito fiscal" (1.1/2.1) de "com efeito fiscal" (1.2/2.2)
    if tem_doc_fiscal:
        pontuar("1.2", 2, f'Tem documento fiscal ("{campos.get("DOCUMENTO_FISCAL")}")')
        pontuar("2.2", 2, f'Tem documento fiscal ("{campos.get("DOCUMENTO_FISCAL")}")')
    else:
        pontuar("1.1", 1, "Sem documento fiscal informado")
        pontuar("2.1", 1, "Sem documento fiscal informado")

    # Dois locais diferentes preenchidos -- indício de transferência
    if local_origem and local_destino and local_origem.lower() != local_destino.lower():
        pontuar(
            "3.1", 2,
            f'Origem ("{local_origem}") e destino ("{local_destino}") são locais diferentes',
        )

    resultado = [
        {"grupo": g, "pontuacao": p, "sinais": sinais[g]}
        for g, p in pontuacoes.items()
        if p > 0
    ]
    resultado.sort(key=lambda x: x["pontuacao"], reverse=True)
    return resultado
