"""
Sugere qual(is) grupo(s) de movimento (1.1 a 4.1) correspondem aos campos
extraídos da saída do interpretador de MIT 41.

NÃO é machine learning nem IA -- é um conjunto de regras baseadas no que
cada grupo significa de negócio (ver api/_lib/config.py). Cada grupo
recebe uma pontuação, e o resultado mostra os SINAIS que levaram a essa
pontuação -- o analista vê o porquê, não uma caixa preta, e confirma
antes de usar.

Os termos, sinônimos e pesos ficam em sinonimos.py. A busca de termo usa
limite de palavra (\\b), tolera plural e erro de digitação.
"""

from .sinonimos import (
    CONCEITOS, DEVOLUCAO, DEVOLUCAO_DE_COMPRA, DEVOLUCAO_DE_VENDA, ROTULOS,
    achar_termo, normalizar_texto, tem_algum,
)

# Piso de confiança: 1 ponto é empate fraco (ex: só "sem campo fiscal"),
# não sinal de verdade. Documento real mostrou que abaixo disso o
# resultado é ruído (cadastros e gestão de contrato, que nem são "tipo
# de movimento" de verdade, ficavam com uma sugestão falsa por causa desse
# empate). NÃO baixar sem reavaliar os casos de tests/casos_mit41.
PISO_CONFIANCA = 2

# O nome do movimento é o sinal mais forte: termo achado nele ganha este bônus.
BONUS_NOME_MOVIMENTO = 1

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
    nome = normalizar_texto(campos.get("NOME_MOVIMENTO", ""))
    texto_processo = " ".join(
        normalizar_texto(campos.get(c, ""))
        for c in ("PROCESSO_ORIGEM", "PROCESSO_DESTINO", "NOME_MOVIMENTO")
    )

    local_origem = campos.get("LOCAL_ORIGEM", "").strip()
    local_destino = campos.get("LOCAL_DESTINO", "").strip()

    pontuacoes: dict[str, int] = {g: 0 for g in ("1.1", "1.2", "2.1", "2.2", "3.1", "4.1")}
    sinais: dict[str, list[str]] = {g: [] for g in pontuacoes}

    def pontuar(grupo: str, pontos: int, motivo: str):
        pontuacoes[grupo] += pontos
        sinais[grupo].append(motivo)

    def pontos_do_conceito(conceito: str) -> tuple[int, str] | None:
        """Melhor termo do conceito (peso + bônus se está no nome) -- sem somar termos repetidos."""
        melhor: tuple[int, str] | None = None
        for termo, peso in CONCEITOS[conceito].items():
            achado = achar_termo(termo, texto_processo)
            if not achado:
                continue
            tipo, trecho = achado
            pontos = peso + (BONUS_NOME_MOVIMENTO if achar_termo(termo, nome) else 0)
            if tipo == "aproximado":
                pontos -= 1  # menos certeza que uma correspondência exata
            motivo = f'Termo de {ROTULOS[conceito]}: "{trecho}"' + (
                " (aproximado)" if tipo == "aproximado" else ""
            )
            if pontos >= 1 and (melhor is None or pontos > melhor[0]):
                melhor = (pontos, motivo)
        return melhor

    # Sinal de "devolução" tem prioridade sobre o sinal genérico de
    # compra/venda, porque muda a direção: devolução DE COMPRA (pro
    # fornecedor) é uma SAÍDA (2.2); devolução DE VENDA (do cliente) é
    # uma ENTRADA (1.2). Documento real confirmou esse caso.
    eh_devolucao = tem_algum(DEVOLUCAO, texto_processo)
    direcao = None  # "entrada" | "saida" | None -- direciona o efeito fiscal
    if eh_devolucao and tem_algum(DEVOLUCAO_DE_COMPRA, texto_processo):
        pontuar("2.2", 3, "Devolução de compra/pra fornecedor -- é uma saída de mercadoria")
        direcao = "saida"
    elif eh_devolucao and tem_algum(DEVOLUCAO_DE_VENDA, texto_processo):
        pontuar("1.2", 3, "Devolução de venda/de cliente -- é uma entrada de mercadoria")
        direcao = "entrada"
    else:
        entrada = pontos_do_conceito("entrada")
        saida = pontos_do_conceito("saida")
        if entrada:
            pontuar("1.1", entrada[0], entrada[1])
            pontuar("1.2", entrada[0], entrada[1])
        if saida:
            pontuar("2.1", saida[0], saida[1])
            pontuar("2.2", saida[0], saida[1])
        if entrada and not saida:
            direcao = "entrada"
        elif saida and not entrada:
            direcao = "saida"

    transferencia = pontos_do_conceito("transferencia")
    if transferencia:
        pontuar("3.1", transferencia[0], transferencia[1])
    interno = pontos_do_conceito("interno")
    if interno:
        pontuar("4.1", interno[0], interno[1])

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
        motivo = f'Campo "{nome_campo}" preenchido ("{resumo}")'
        # Com direção clara (só entrada ou só saída), o efeito fiscal vai só
        # pro lado certo -- antes uma entrada com nota fiscal ganhava ponto em 2.2.
        if direcao != "saida":
            pontuar("1.2", 2, motivo)
        if direcao != "entrada":
            pontuar("2.2", 2, motivo)
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
        if p >= PISO_CONFIANCA
    ]
    resultado.sort(key=lambda x: x["pontuacao"], reverse=True)
    return resultado
