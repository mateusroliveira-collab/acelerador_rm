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


# --- CNAB 240, Pagamentos (Segmentos A, B, C, J, N, O, W, Z) -----------
#
# Fonte: manual oficial "Particularidades BB - Arquivo de Pagamentos".
# Tabela "Código Ocorrências de Retorno" -- vale pra QUALQUER segmento
# de pagamento (todos apontam pra essa mesma tabela na posição 231-240).
# Podem vir até 5 códigos simultâneos nessa posição, 2 dígitos cada.
CODIGOS_OCORRENCIA_PAGAMENTO_BB: dict[str, str] = {
    "00": "Pagamento confirmado",
    "01": "Insuficiência de Fundos -- Débito não efetuado",
    "02": "Crédito ou Débito Cancelado pelo Pagador/Credor",
    "03": "Débito Autorizado pela Agência -- Efetuado",
    "AA": "Controle Inválido",
    "AB": "Tipo de Operação Inválido",
    "AC": "Tipo de Serviço Inválido",
    "AD": "Forma de Lançamento Inválida",
    "AE": "Tipo/Número de Inscrição Inválido",
    "AF": "Código de Convênio Inválido",
    "AG": "Agência/Conta Corrente/DV Inválido",
    "AH": "Nº Sequencial do Registro no Lote Inválido",
    "AI": "Código de Segmento de Detalhe Inválido",
    "AJ": "Tipo de Movimento Inválido",
    "AK": "Código da Câmara de Compensação do Banco Favorecido/Depositário Inválido",
    "AL": "Código do Banco Favorecido ou Depositário Inválido",
    "AM": "Agência Mantenedora da Conta Corrente do Favorecido Inválida",
    "AN": "Conta Corrente/DV do Favorecido Inválido",
    "AO": "Nome do Favorecido Não Informado",
    "AP": "Data Lançamento Inválido",
    "AQ": "Tipo/Quantidade da Moeda Inválido",
    "AR": "Valor do Lançamento Inválido",
    "AS": "Aviso ao Favorecido -- Identificação Inválida",
    "AT": "Tipo/Número de Inscrição do Favorecido Inválido",
    "AU": "Logradouro do Favorecido Não Informado",
    "AV": "Nº do Local do Favorecido Não Informado",
    "AW": "Cidade do Favorecido Não Informada",
    "AX": "CEP/Complemento do Favorecido Inválido",
    "AY": "Sigla do Estado do Favorecido Inválida",
    "AZ": "Código/Nome do Banco Depositário Inválido",
    "BA": "Código/Nome da Agência Depositária Não Informado",
    "BB": "Seu Número Inválido",
    "BC": "Nosso Número Inválido",
    "BD": "Inclusão Efetuada com Sucesso",
    "BE": "Alteração Efetuada com Sucesso",
    "BF": "Exclusão Efetuada com Sucesso",
    "BG": "Agência/Conta Impedida Legalmente",
    "BH": "Empresa não pagou salário",
    "BI": "Falecimento do mutuário",
    "BJ": "Empresa não enviou remessa do mutuário",
    "BK": "Empresa não enviou remessa no vencimento",
    "BL": "Valor da parcela inválida",
    "BM": "Identificação do contrato inválida",
    "BN": "Operação de Consignação Incluída com Sucesso",
    "BO": "Operação de Consignação Alterada com Sucesso",
    "BP": "Operação de Consignação Excluída com Sucesso",
    "BQ": "Operação de Consignação Liquidada com Sucesso",
    "BR": "Reativação Efetuada com Sucesso",
    "BS": "Suspensão Efetuada com Sucesso",
    "CA": "Código de Barras -- Código do Banco Inválido",
    "CB": "Código de Barras -- Código da Moeda Inválido",
    "CC": "Código de Barras -- Dígito Verificador Geral Inválido",
    "CD": "Código de Barras -- Valor do Título Inválido",
    "CE": "Código de Barras -- Campo Livre Inválido",
    "CF": "Valor do Documento Inválido",
    "CG": "Valor do Abatimento Inválido",
    "CH": "Valor do Desconto Inválido",
    "CI": "Valor de Mora Inválido",
    "CJ": "Valor da Multa Inválido",
    "CK": "Valor do IR Inválido",
    "CL": "Valor do ISS Inválido",
    "CM": "Valor do IOF Inválido",
    "CN": "Valor de Outras Deduções Inválido",
    "CO": "Valor de Outros Acréscimos Inválido",
    "CP": "Valor do INSS Inválido",
    "HA": "Lote Não Aceito",
    "HB": "Inscrição da Empresa Inválida para o Contrato",
    "HC": "Convênio com a Empresa Inexistente/Inválido para o Contrato",
    "HD": "Agência/Conta Corrente da Empresa Inexistente/Inválido para o Contrato",
    "HE": "Tipo de Serviço Inválido para o Contrato",
    "HF": "Conta Corrente da Empresa com Saldo Insuficiente",
    "HG": "Lote de Serviço Fora de Sequência",
    "HH": "Lote de Serviço Inválido",
    "HI": "Arquivo não aceito",
    "HJ": "Tipo de Registro Inválido",
    "HK": "Código Remessa / Retorno Inválido",
    "HL": "Versão de layout inválida",
    "HM": "Mutuário não identificado",
    "HN": "Tipo do benefício não permite empréstimo",
    "HO": "Benefício cessado/suspenso",
    "HP": "Benefício possui representante legal",
    "HQ": "Benefício é do tipo PA (Pensão alimentícia)",
    "HR": "Quantidade de contratos permitida excedida",
    "HS": "Benefício não pertence ao Banco informado",
    "HT": "Início do desconto informado já ultrapassado",
    "HU": "Número da parcela inválida",
    "HV": "Quantidade de parcela inválida",
    "HW": "Margem consignável excedida para o mutuário dentro do prazo do contrato",
    "HX": "Empréstimo já cadastrado",
    "HY": "Empréstimo inexistente",
    "HZ": "Empréstimo já encerrado",
    "H1": "Arquivo sem trailer",
    "H2": "Mutuário sem crédito na competência",
    "H3": "Não descontado -- outros motivos",
    "H4": "Retorno de Crédito não pago",
    "H5": "Cancelamento de empréstimo retroativo",
    "H6": "Outros Motivos de Glosa",
    "H7": "Margem consignável excedida para o mutuário acima do prazo do contrato",
    "H8": "Mutuário desligado do empregador",
    "H9": "Mutuário afastado por licença",
    "IA": "Primeiro nome do mutuário diferente do primeiro nome do movimento do censo ou da base de Titular do Benefício",
    "IB": "Benefício suspenso/cessado pela APS ou Sisobi",
    "IC": "Benefício suspenso por dependência de cálculo",
    "ID": "Benefício suspenso/cessado pela inspetoria/auditoria",
    "IE": "Benefício bloqueado para empréstimo pelo beneficiário",
    "IF": "Benefício bloqueado para empréstimo por TBM",
    "IG": "Benefício está em fase de concessão de PA ou desdobramento",
    "IH": "Benefício cessado por óbito",
    "II": "Benefício cessado por fraude",
    "IJ": "Benefício cessado por concessão de outro benefício",
    "IK": "Benefício cessado: estatutário transferido para órgão de origem",
    "IL": "Empréstimo suspenso pela APS",
    "IM": "Empréstimo cancelado pelo banco",
    "IN": "Crédito transformado em PAB",
    "IO": "Término da consignação foi alterado",
    "IP": "Fim do empréstimo ocorreu durante período de suspensão ou concessão",
    "IQ": "Empréstimo suspenso pelo banco",
    "IR": "Não averbação de contrato -- quantidade de parcelas/competências ultrapassou a data limite de extinção de cota do dependente titular",
    "TA": "Lote Não Aceito -- Totais do Lote com Diferença",
    "YA": "Título Não Encontrado",
    "YB": "Identificador Registro Opcional Inválido",
    "YC": "Código Padrão Inválido",
    "YD": "Código de Ocorrência Inválido",
    "YE": "Complemento de Ocorrência Inválido",
    "YF": "Alegação já Informada",
    "ZA": "Agência / Conta do Favorecido Substituída (caráter informativo)",
    "ZB": "Divergência entre nome do beneficiário e nome na Receita Federal",
    "ZC": "Confirmação de Antecipação de Valor",
    "ZD": "Antecipação parcial de valor",
    "ZE": "Título bloqueado na base",
    "ZF": "Sistema em contingência -- título valor maior que referência",
    "ZG": "Sistema em contingência -- título vencido",
    "ZH": "Sistema em contingência -- título indexado",
    "ZI": "Beneficiário divergente",
    "ZJ": "Limite de pagamentos parciais excedido",
    "ZK": "Boleto já liquidado",
    "PA": "Pix não efetivado",
    "PB": "Transação interrompida devido a erro no PSP do Recebedor",
    "PC": "Número da conta transacional encerrada no PSP do Recebedor",
    "PD": "Tipo incorreto para a conta transacional especificada",
    "PE": "Tipo de transação não é suportado/autorizado na conta transacional especificada",
    "PF": "CPF/CNPJ do usuário recebedor não é consistente com o titular da conta transacional",
    "PG": "CPF/CNPJ do usuário recebedor incorreto",
    "PH": "Ordem rejeitada pelo PSP do Recebedor",
    "PI": "ISPB do PSP do Pagador inválido ou inexistente",
    "PJ": "Chave não cadastrada no DICT",
    "PK": "QR Code inválido/vencido",
    "PL": "Forma de iniciação inválida",
    "PM": "Chave de pagamento inválida",
    "PN": "Chave de pagamento não informada",
}

# Códigos que indicam SUCESSO (não são problema) -- útil pro validador
# não tratar como erro algo que na verdade é confirmação.
CODIGOS_OCORRENCIA_PAGAMENTO_BB_SAO_SUCESSO = {
    "00", "03", "BD", "BE", "BF", "BN", "BO", "BP", "BQ", "BR", "BS", "ZC",
}


def significado_ocorrencia_pagamento_bb(codigo: str) -> str | None:
    """Devolve o significado de um código de ocorrência de retorno de pagamento do BB."""
    return CODIGOS_OCORRENCIA_PAGAMENTO_BB.get(codigo)


def ocorrencia_pagamento_eh_sucesso_bb(codigo: str) -> bool:
    """True se o código de ocorrência de pagamento indica sucesso, não erro."""
    return codigo in CODIGOS_OCORRENCIA_PAGAMENTO_BB_SAO_SUCESSO


def decompor_codigos_ocorrencia(campo_231_240: str) -> list[str]:
    """
    O campo de ocorrências (posição 231-240, 10 caracteres) pode trazer
    até 5 códigos de 2 dígitos cada, concatenados. Essa função separa em
    uma lista, ignorando blocos de '00' zerados no fim (sem ocorrência).
    """
    codigos = [campo_231_240[i:i+2] for i in range(0, len(campo_231_240), 2)]
    # Remove pares "00" à direita quando sobra espaço sem ocorrência real,
    # mas mantém um "00" isolado (que tem significado próprio: confirmado).
    while len(codigos) > 1 and codigos[-1] == "00":
        codigos.pop()
    return [c for c in codigos if c]
