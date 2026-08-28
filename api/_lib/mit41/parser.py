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

# Campos da seção [FISCAL] que indicam efeito fiscal de verdade quando
# preenchidos. Documento real mostrou que "DOCUMENTO_FISCAL" sozinho não
# basta -- muitos movimentos descrevem o efeito fiscal só em TRIBUTACAO,
# OPERACAO_FISCAL, RETENCOES ou ESCRITURACAO. "OBSERVACAO_FISCAL" fica de
# fora de propósito: no documento real, é usado com frequência pra dizer
# exatamente o contrário ("Movimento não gera integração fiscal").
CAMPOS_INDICAM_FISCAL = ["DOCUMENTO_FISCAL", "OPERACAO_FISCAL", "TRIBUTACAO", "RETENCOES", "ESCRITURACAO"]

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
        [campos.get("PROCESSO_ORIGEM", ""), campos.get("PROCESSO_DESTINO", ""),
         campos.get("NOME_MOVIMENTO", "")]
    ).lower()

    local_origem = campos.get("LOCAL_ORIGEM", "").strip()
    local_destino = campos.get("LOCAL_DESTINO", "").strip()

    pontuacoes: dict[str, int] = {g: 0 for g in ("1.1", "1.2", "2.1", "2.2", "3.1", "4.1")}
    sinais: dict[str, list[str]] = {g: [] for g in pontuacoes}

    def pontuar(grupo: str, pontos: int, motivo: str):
        pontuacoes[grupo] += pontos
        sinais[grupo].append(motivo)

    # Sinal de "devolução" tem prioridade sobre o sinal genérico de
    # compra/venda, porque muda a direção: devolução DE COMPRA (pro
    # fornecedor) é uma SAÍDA (2.2); devolução DE VENDA (do cliente) é
    # uma ENTRADA (1.2). Documento real confirmou esse caso.
    eh_devolucao = "devolução" in texto_processo or "devolucao" in texto_processo
    if eh_devolucao and any(p in texto_processo for p in ["compra", "fornecedor"]):
        pontuar("2.2", 3, "Devolução de compra/pra fornecedor -- é uma saída de mercadoria")
    elif eh_devolucao and any(p in texto_processo for p in ["venda", "cliente"]):
        pontuar("1.2", 3, "Devolução de venda/de cliente -- é uma entrada de mercadoria")
    else:
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
    # -- checa vários campos da seção FISCAL, não só DOCUMENTO_FISCAL (ver CAMPOS_INDICAM_FISCAL)
    campo_fiscal_encontrado = None
    for campo in CAMPOS_INDICAM_FISCAL:
        valor = campos.get(campo, "").strip().lower()
        if valor and valor not in _VALORES_SEM_DOC_FISCAL:
            campo_fiscal_encontrado = (campo, campos.get(campo))
            break

    if campo_fiscal_encontrado:
        nome_campo, valor_campo = campo_fiscal_encontrado
        resumo = valor_campo if len(valor_campo) <= 40 else valor_campo[:37] + "..."
        pontuar("1.2", 2, f'Campo "{nome_campo}" preenchido ("{resumo}")')
        pontuar("2.2", 2, f'Campo "{nome_campo}" preenchido ("{resumo}")')
    else:
        pontuar("1.1", 1, "Nenhum campo fiscal preenchido")
        pontuar("2.1", 1, "Nenhum campo fiscal preenchido")

    # Dois locais diferentes preenchidos -- indício de transferência
    if local_origem and local_destino and local_origem.lower() != local_destino.lower():
        pontuar(
            "3.1", 2,
            f'Origem ("{local_origem}") e destino ("{local_destino}") são locais diferentes',
        )

    resultado = [
        {"grupo": g, "pontuacao": p, "sinais": sinais[g]}
        for g, p in pontuacoes.items()
        if p >= 2  # piso de confiança -- 1 ponto é empate fraco (ex: só
                   # "sem campo fiscal"), não sinal de verdade. Documento
                   # real mostrou que abaixo disso o resultado é ruído
                   # (cadastros e gestão de contrato, que nem são "tipo
                   # de movimento" de verdade, ficavam com uma sugestão
                   # falsa por causa desse empate.)
    ]
    resultado.sort(key=lambda x: x["pontuacao"], reverse=True)
    return resultado