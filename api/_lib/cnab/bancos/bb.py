"""
Base de conhecimento de erros específicos do Banco do Brasil -- tanto de
retorno de CNAB quanto de resposta da API de registro online.

Cresce incrementalmente: cada vez que um erro real aparecer no dia a dia,
adiciona uma entrada aqui. Não tenta cobrir tudo de uma vez -- só o que já
foi visto de verdade, pra não inventar causa/sugestão sem confirmação.
"""

# Mapa: código do erro (como o banco devolve) -> dica pronta pro RM
ERROS_CONHECIDOS: dict[str, dict[str, str]] = {
    "4874915": {
        "mensagem_banco": "Nosso Número já incluído anteriormente.",
        "causa_provavel": (
            "O sistema tentou registrar um boleto com um Nosso Número que "
            "já foi enviado ao BB antes -- geralmente acontece quando o "
            "título é reenviado sem gerar um número novo."
        ),
        "sugestao_rm": (
            "No RM, verifique a rotina de geração de Nosso Número do título "
            "em questão -- confira se ele não está sendo reprocessado/"
            "reenviado a partir de um título já registrado."
        ),
    },
}


def buscar_erro_bb(codigo: str) -> dict[str, str] | None:
    """Procura um código de erro do BB na base de conhecimento."""
    return ERROS_CONHECIDOS.get(codigo)


# --- CNAB 240, Segmento T (retorno) ------------------------------------
#
# Fonte: manual oficial "Particularidades BB - Leiaute CNAB 240" (campo
# 07.3T, Código de Movimento Retorno). Diferente de ERROS_CONHECIDOS
# acima, isso NÃO é uma lista de erro -- é o significado de cada código
# de movimento que pode aparecer no retorno (alguns são sucesso, tipo
# "06 - Liquidação"; outros são rejeição, tipo "03 - Entrada Rejeitada").
CODIGOS_MOVIMENTO_RETORNO_BB: dict[str, str] = {
    "02": "Entrada confirmada",
    "03": "Entrada rejeitada",
    "04": "Transferência de Carteira/Entrada",
    "05": "Transferência de Carteira/Baixa",
    "06": "Liquidação",
    "09": "Baixa",
    "11": "Títulos em Carteira (em ser)",
    "12": "Confirmação recebimento instrução de abatimento",
    "13": "Confirmação recebimento instrução de cancelamento de abatimento",
    "14": "Confirmação recebimento instrução alteração de vencimento",
    "15": "Franco de pagamento",
    "17": "Liquidação após baixa ou liquidação título não registrado",
    "19": "Confirmação recebimento instrução de protesto",
    "20": "Confirmação recebimento instrução de sustação/cancelamento de protesto",
    "23": "Remessa a cartório (aponte em cartório)",
    "24": "Retirada de cartório e manutenção em carteira",
    "25": "Protestado e baixado (baixa por ter sido protestado)",
    "26": "Instrução rejeitada",
    "27": "Confirmação do pedido de alteração de outros dados",
    "28": "Débito de tarifas/custas",
    "29": "Ocorrências do sacado",
    "30": "Alteração de dados rejeitada",
    "44": "Título pago com cheque devolvido",
    "50": "Título pago com cheque pendente de compensação",
    "85": "Inclusão de negativação",
    "86": "Exclusão de negativação",
}

# Códigos de movimento retorno que representam REJEIÇÃO -- útil pro
# validador sinalizar "isso é um problema" vs. "isso é status normal".
CODIGOS_MOVIMENTO_RETORNO_BB_SAO_REJEICAO = {"03", "26", "30"}

# Exceção específica do BB: o código de rejeição "52" (campo 28.3T)
# significa algo DIFERENTE do padrão FEBRABAN -- o manual do BB avisa
# explicitamente pra desconsiderar o significado FEBRABAN nesse caso.
CODIGO_REJEICAO_52_SIGNIFICADO_FEBRABAN = "Unidade da Federação Inválida"
CODIGO_REJEICAO_52_SIGNIFICADO_BB = "Registro de Título já liquidado Cart. 17"

# Anexo 01 do manual: quando o código de movimento (campo 07.3T) é 85
# (inclusão de negativação) ou 86 (exclusão), o campo de motivo (28.3T)
# usa uma tabela própria, diferente da tabela geral de rejeição.
CODIGOS_NEGATIVACAO_INCLUSAO_BB: dict[str, str] = {
    "01": "Negativação aceita no BB",
    "02": "Negativação aceita no agente negativador",
    "03": "Inclusão cancelada",
    "04": "Negativação recusada -- pagador menor de idade",
    "05": "Negativação recusada -- espécie do boleto não permitida",
    "06": "Negativação recusada -- beneficiário não é PJ",
    "07": "Negativação recusada -- moeda do boleto não é Real",
    "08": "Negativação recusada -- endereço do pagador inválido",
    "09": "Negativação recusada pelo agente negativador",
    "10": "Negativação recusada -- situação do boleto não permite negativação",
    "11": "Negativação recusada -- cadastro do beneficiário desatualizado",
    "12": "Negativação recusada -- boleto inexistente",
    "13": "Negativação recusada -- pagador não identificado",
    "14": "Recusa de tarifação de negativação",
    "15": "Negativação recusada -- motivos diversos",
}

CODIGOS_NEGATIVACAO_EXCLUSAO_BB: dict[str, str] = {
    "01": "Exclusão cancelada",
    "02": "Negativação excluída no agente negativador",
    "03": "Negativação excluída -- devolução pelos correios",
    "04": "Negativação excluída -- data de ocorrência decorrida",
    "05": "Negativação excluída -- determinação judicial",
    "06": "Negativação excluída -- contestação do interessado",
    "07": "Negativação excluída -- carta não retornou do correio",
    "08": "Exclusão de negativação recusada -- registro inexistente",
    "09": "Exclusão de negativação aceita no BB",
    "15": "Exclusão de negativação recusada -- motivos diversos",
}


def significado_movimento_retorno_bb(codigo: str) -> str | None:
    """Devolve o significado de um código de movimento de retorno do BB (Segmento T)."""
    return CODIGOS_MOVIMENTO_RETORNO_BB.get(codigo)


def movimento_eh_rejeicao_bb(codigo: str) -> bool:
    """True se o código de movimento retorno indica rejeição (não status normal)."""
    return codigo in CODIGOS_MOVIMENTO_RETORNO_BB_SAO_REJEICAO


def significado_negativacao_bb(codigo_movimento: str, codigo_motivo: str) -> str | None:
    """
    Devolve o significado do código de motivo (28.3T) quando o movimento
    (07.3T) é 85 (inclusão de negativação) ou 86 (exclusão) -- tabela
    própria do Anexo 01, diferente da tabela geral de rejeição.
    """
    if codigo_movimento == "85":
        return CODIGOS_NEGATIVACAO_INCLUSAO_BB.get(codigo_motivo)
    if codigo_movimento == "86":
        return CODIGOS_NEGATIVACAO_EXCLUSAO_BB.get(codigo_motivo)
    return None
