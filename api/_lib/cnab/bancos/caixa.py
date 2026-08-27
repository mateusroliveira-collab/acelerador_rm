"""
Base de conhecimento de erros da Caixa Econômica Federal.

Três tabelas SEPARADAS de propósito -- são contextos diferentes, com
códigos que podem colidir entre si (ex: código "01" significa coisas
diferentes em cada tabela):

  - ERROS_REJEICAO_RETORNO_400: motivo de rejeição no arquivo de RETORNO
    do CNAB 400 (Nota Explicativa NE032, posições 80-82 do registro
    detalhe). É a mais parecida com o cenário do BB -- um erro que volta
    depois que a Caixa processou.
  - ERROS_CRITICA_REMESSA_400: erro de formatação encontrado ANTES de
    processar, no arquivo de Pré-Crítica do CNAB 400 (NE038). Ajuda a
    pegar problema de formatação do próprio arquivo de remessa.
  - ERROS_REJEICAO_ENTRADA_240: motivos de rejeição de entrada no CNAB
    240 (fonte: artigo de suporte TOTVS, lista parcial).

`buscar_erro()` usa ERROS_REJEICAO_RETORNO_400 como padrão (é o cenário
mais comum de "traduzir erro do banco"). As outras duas ficam disponíveis
pra quando o front-end tiver um seletor de contexto.

Fonte NE032/NE038: manual oficial "Leiaute de Arquivo Eletrônico Padrão
CNAB 400 -- Cobrança Bancária CAIXA - SIGCB", documento 67.126 v003 micro.
"sugestao_rm" fica como PENDENTE até alguém confirmar, na prática, onde
cada erro corresponde no RM.
"""

_PENDENTE = "PENDENTE -- preencher quando confirmado na prática."

# --------------------------------------------------------------------
# NE032 -- Código de Motivo de Ocorrência (rejeição no RETORNO, CNAB 400)
# --------------------------------------------------------------------
ERROS_REJEICAO_RETORNO_400: dict[str, dict[str, str]] = {
    "01": {"mensagem_banco": "Movimento sem Beneficiário Correspondente", "causa_provavel": "O código do beneficiário informado não corresponde a nenhum cadastro na CAIXA.", "sugestao_rm": _PENDENTE},
    "02": {"mensagem_banco": "Movimento sem Título Correspondente", "causa_provavel": "O movimento se refere a um título que a CAIXA não tem registrado.", "sugestao_rm": _PENDENTE},
    "08": {"mensagem_banco": "Movimento para Título já com Movimentação no Dia", "causa_provavel": "Já foi enviado outro movimento para esse mesmo título no mesmo dia.", "sugestao_rm": _PENDENTE},
    "09": {"mensagem_banco": "Nosso Número não Pertence ao Beneficiário", "causa_provavel": "O Nosso Número informado está associado a outro beneficiário, não a este.", "sugestao_rm": _PENDENTE},
    "10": {"mensagem_banco": "Inclusão de Título já Existente na Base", "causa_provavel": "Mesma família de erro do exemplo do BB -- o título/Nosso Número já foi registrado antes.", "sugestao_rm": _PENDENTE},
    "12": {"mensagem_banco": "Movimento Duplicado", "causa_provavel": "O mesmo movimento foi enviado mais de uma vez.", "sugestao_rm": _PENDENTE},
    "13": {"mensagem_banco": "Entrada Inválida para Cobrança Caucionada", "causa_provavel": "O beneficiário não possui conta caução, mas o título foi enviado como caucionado.", "sugestao_rm": _PENDENTE},
    "20": {"mensagem_banco": "CEP do Pagador Não Encontrado", "causa_provavel": "Não foi possível determinar a agência cobradora a partir do CEP informado.", "sugestao_rm": _PENDENTE},
    "21": {"mensagem_banco": "Agência Cobradora Não Encontrada", "causa_provavel": "A agência designada para cobrança não está cadastrada no sistema da CAIXA.", "sugestao_rm": _PENDENTE},
    "22": {"mensagem_banco": "Agência do Beneficiário Não Encontrada", "causa_provavel": "A agência do beneficiário não está cadastrada no sistema da CAIXA.", "sugestao_rm": _PENDENTE},
    "45": {"mensagem_banco": "Data de Vencimento com Prazo Superior ao Limite", "causa_provavel": "A data de vencimento informada está além do prazo máximo aceito pela CAIXA.", "sugestao_rm": _PENDENTE},
    "49": {"mensagem_banco": "Movimento Inválido para Título Baixado/Liquidado", "causa_provavel": "Foi enviado um movimento para um título que já foi baixado ou liquidado.", "sugestao_rm": _PENDENTE},
    "50": {"mensagem_banco": "Movimento Inválido para Título Enviado a Cartório", "causa_provavel": "Foi enviado um movimento incompatível com um título que já está em processo de protesto.", "sugestao_rm": _PENDENTE},
    "54": {"mensagem_banco": "Faixa de CEP da Agência Cobradora Não Abrange CEP do Pagador", "causa_provavel": "A agência cobradora escolhida não atende a região do CEP do pagador.", "sugestao_rm": _PENDENTE},
    "55": {"mensagem_banco": "Título já com Opção de Devolução", "causa_provavel": "O título já está configurado para devolução, não pode receber esse movimento.", "sugestao_rm": _PENDENTE},
    "56": {"mensagem_banco": "Processo de Protesto em Andamento", "causa_provavel": "Não é possível aplicar esse movimento enquanto o protesto está em andamento.", "sugestao_rm": _PENDENTE},
    "57": {"mensagem_banco": "Título já com Opção de Protesto", "causa_provavel": "O título já está configurado para protesto, não pode receber esse movimento.", "sugestao_rm": _PENDENTE},
    "58": {"mensagem_banco": "Processo de Devolução em Andamento", "causa_provavel": "Não é possível aplicar esse movimento enquanto a devolução está em andamento.", "sugestao_rm": _PENDENTE},
    "59": {"mensagem_banco": "Novo Prazo para Protesto/Devolução Inválido", "causa_provavel": "O novo prazo informado para protesto ou devolução está fora do intervalo aceito.", "sugestao_rm": _PENDENTE},
    "76": {"mensagem_banco": "Alteração do Prazo de Protesto Inválida", "causa_provavel": "A alteração solicitada no prazo de protesto não é permitida nesse contexto.", "sugestao_rm": _PENDENTE},
    "77": {"mensagem_banco": "Alteração do Prazo de Devolução Inválida", "causa_provavel": "A alteração solicitada no prazo de devolução não é permitida nesse contexto.", "sugestao_rm": _PENDENTE},
    "81": {"mensagem_banco": "CEP do Pagador Inválido", "causa_provavel": "O CEP informado para o pagador não é um CEP válido.", "sugestao_rm": _PENDENTE},
    "82": {"mensagem_banco": "CNPJ/CPF do Pagador Inválido (dígito não confere)", "causa_provavel": "O documento do pagador tem o dígito verificador incorreto.", "sugestao_rm": _PENDENTE},
    "83": {"mensagem_banco": "Número do Documento (Seu Número) Inválido", "causa_provavel": "O campo 'Seu Número' enviado não está num formato aceito.", "sugestao_rm": _PENDENTE},
    "84": {"mensagem_banco": "Protesto Inválido para Título sem Número do Documento", "causa_provavel": "Foi solicitado protesto para um título sem o 'Seu Número' preenchido, que é obrigatório nesse caso.", "sugestao_rm": _PENDENTE},
}

# --------------------------------------------------------------------
# NE038 -- Crítica do Arquivo Remessa (Pré-Crítica, CNAB 400)
# --------------------------------------------------------------------
ERROS_CRITICA_REMESSA_400: dict[str, dict[str, str]] = {
    "01": {"mensagem_banco": "Remessa sem Registro Tipo 0", "causa_provavel": "O arquivo não tem o registro header (tipo 0).", "sugestao_rm": _PENDENTE},
    "02": {"mensagem_banco": "Identificação Inválida da Empresa na CAIXA", "causa_provavel": "O código do beneficiário informado não é válido.", "sugestao_rm": _PENDENTE},
    "03": {"mensagem_banco": "Número Inválido da Remessa", "causa_provavel": "O número sequencial da remessa está fora do esperado.", "sugestao_rm": _PENDENTE},
    "04": {"mensagem_banco": "Beneficiário Não Pertence à Cobrança Eletrônica", "causa_provavel": "O beneficiário não está habilitado para esse serviço.", "sugestao_rm": _PENDENTE},
    "05": {"mensagem_banco": "Código da Remessa Inválido", "causa_provavel": "O campo 'Código da Remessa' (posição 2) não é '1'.", "sugestao_rm": _PENDENTE},
    "06": {"mensagem_banco": "Literal da Remessa Inválido", "causa_provavel": "O texto esperado ('REMESSA' ou 'REM.TST') não bateu.", "sugestao_rm": _PENDENTE},
    "07": {"mensagem_banco": "Código de Serviço Inválido", "causa_provavel": "O código de serviço informado não é '01'.", "sugestao_rm": _PENDENTE},
    "08": {"mensagem_banco": "Literal de Serviço Inválido", "causa_provavel": "O texto esperado ('COBRANCA') não bateu.", "sugestao_rm": _PENDENTE},
    "09": {"mensagem_banco": "Código do Banco Inválido", "causa_provavel": "O código do banco informado não é '104' (Caixa).", "sugestao_rm": _PENDENTE},
    "10": {"mensagem_banco": "Nome do Banco Inválido", "causa_provavel": "O nome do banco não bateu com o esperado.", "sugestao_rm": _PENDENTE},
    "11": {"mensagem_banco": "Data de Gravação Inválida", "causa_provavel": "A data de geração do arquivo não é uma data válida.", "sugestao_rm": _PENDENTE},
    "12": {"mensagem_banco": "Número de Remessa já Processada", "causa_provavel": "Esse número de remessa já foi processado anteriormente -- possível reenvio duplicado.", "sugestao_rm": _PENDENTE},
    "13": {"mensagem_banco": "Tipo de Registro Esperado Inválido", "causa_provavel": "A sequência de tipos de registro no arquivo não é a esperada.", "sugestao_rm": _PENDENTE},
    "14": {"mensagem_banco": "Tipo de Ocorrência Inválido", "causa_provavel": "O código de ocorrência informado no registro detalhe não é reconhecido.", "sugestao_rm": _PENDENTE},
    "15": {"mensagem_banco": "Literal Remessa Inválida para Fase de Testes", "causa_provavel": "O beneficiário ainda está em fase de testes, mas o arquivo não usou o literal de teste.", "sugestao_rm": _PENDENTE},
    "16": {"mensagem_banco": "Identificação da Empresa Diverge entre Registro 0 e Registro 1", "causa_provavel": "O código do beneficiário no header não bate com o do registro de detalhe.", "sugestao_rm": _PENDENTE},
    "17": {"mensagem_banco": "Identificação na CAIXA Inválida (Nosso Número)", "causa_provavel": "O Nosso Número informado não está num formato válido.", "sugestao_rm": _PENDENTE},
    "18": {"mensagem_banco": "Código da Carteira Inválido", "causa_provavel": "O código de carteira informado não é '01' ou '02'.", "sugestao_rm": _PENDENTE},
    "19": {"mensagem_banco": "Número Sequencial do Registro Inválido", "causa_provavel": "A numeração sequencial dos registros no arquivo está fora de ordem.", "sugestao_rm": _PENDENTE},
    "20": {"mensagem_banco": "Tipo de Inscrição da Empresa Inválido", "causa_provavel": "O tipo de inscrição não é '01' (CPF) nem '02' (CNPJ).", "sugestao_rm": _PENDENTE},
    "21": {"mensagem_banco": "Número de Inscrição da Empresa Inválido", "causa_provavel": "O CPF/CNPJ da empresa não é válido.", "sugestao_rm": _PENDENTE},
    "22": {"mensagem_banco": "Literal REM.TST Válida Somente para Fase de Testes", "causa_provavel": "O beneficiário já está em produção, mas o arquivo ainda usa o literal de teste.", "sugestao_rm": _PENDENTE},
    "23": {"mensagem_banco": "Taxa de Comissão de Permanência Inválida", "causa_provavel": "O código de taxa de permanência informado não é reconhecido.", "sugestao_rm": _PENDENTE},
    "24": {"mensagem_banco": "Nosso Número Inválido para Cobrança Registrada (Emissão Beneficiário)", "causa_provavel": "O prefixo do Nosso Número não corresponde ao esperado (deveria começar com '14').", "sugestao_rm": _PENDENTE},
    "25": {"mensagem_banco": "Dígito do Nosso Número Não Confere", "causa_provavel": "O dígito verificador do Nosso Número está incorreto.", "sugestao_rm": _PENDENTE},
    "26": {"mensagem_banco": "Data de Vencimento Inválida", "causa_provavel": "A data de vencimento informada não é uma data válida.", "sugestao_rm": _PENDENTE},
    "27": {"mensagem_banco": "Valor do Título Inválido", "causa_provavel": "O valor do título está zerado ou num formato inválido.", "sugestao_rm": _PENDENTE},
    "28": {"mensagem_banco": "Espécie de Título Inválida", "causa_provavel": "O código da espécie do título não é reconhecido pela FEBRABAN.", "sugestao_rm": _PENDENTE},
    "29": {"mensagem_banco": "Código de Aceite Inválido", "causa_provavel": "O campo Aceite não é 'A' nem 'N'.", "sugestao_rm": _PENDENTE},
    "30": {"mensagem_banco": "Data de Emissão do Título Inválida", "causa_provavel": "A data de emissão informada não é uma data válida.", "sugestao_rm": _PENDENTE},
    "31": {"mensagem_banco": "Instrução de Cobrança 1 Inválida", "causa_provavel": "O código de protesto/devolução informado não é reconhecido.", "sugestao_rm": _PENDENTE},
    "32": {"mensagem_banco": "Instrução de Cobrança 2 Inválida", "causa_provavel": "O código da segunda instrução não é reconhecido.", "sugestao_rm": _PENDENTE},
    "33": {"mensagem_banco": "Instrução de Cobrança 3 Inválida", "causa_provavel": "O código da terceira instrução (mensagem no verso) não é reconhecido.", "sugestao_rm": _PENDENTE},
    "34": {"mensagem_banco": "Valor de Juros Inválido", "causa_provavel": "O valor de juros de mora informado está num formato inválido.", "sugestao_rm": _PENDENTE},
    "35": {"mensagem_banco": "Data do Desconto Inválida", "causa_provavel": "A data limite para desconto informada não é uma data válida.", "sugestao_rm": _PENDENTE},
    "36": {"mensagem_banco": "Valor do Desconto Inválido", "causa_provavel": "O valor de desconto informado está num formato inválido.", "sugestao_rm": _PENDENTE},
    "37": {"mensagem_banco": "Valor do IOF Inválido", "causa_provavel": "O valor de IOF informado está num formato inválido.", "sugestao_rm": _PENDENTE},
    "38": {"mensagem_banco": "Valor do Abatimento Inválido", "causa_provavel": "O valor de abatimento informado está num formato inválido.", "sugestao_rm": _PENDENTE},
    "39": {"mensagem_banco": "Tipo de Inscrição do Pagador Inválido", "causa_provavel": "O tipo de inscrição do pagador não é '01' (CPF) nem '02' (CNPJ).", "sugestao_rm": _PENDENTE},
    "40": {"mensagem_banco": "Número de Inscrição do Pagador Inválido", "causa_provavel": "O CPF/CNPJ do pagador não é válido (dígito não confere).", "sugestao_rm": _PENDENTE},
    "41": {"mensagem_banco": "Número de Inscrição do Pagador Obrigatório", "causa_provavel": "O CPF/CNPJ do pagador está em branco.", "sugestao_rm": _PENDENTE},
    "42": {"mensagem_banco": "Nome do Pagador Obrigatório", "causa_provavel": "O nome do pagador está em branco.", "sugestao_rm": _PENDENTE},
    "43": {"mensagem_banco": "Endereço do Pagador Obrigatório", "causa_provavel": "O endereço do pagador está em branco.", "sugestao_rm": _PENDENTE},
    "44": {"mensagem_banco": "CEP do Pagador Inválido", "causa_provavel": "O CEP do pagador não é válido ou está em branco.", "sugestao_rm": _PENDENTE},
    "45": {"mensagem_banco": "Cidade do Pagador Obrigatória", "causa_provavel": "A cidade do pagador está em branco.", "sugestao_rm": _PENDENTE},
    "46": {"mensagem_banco": "Estado do Pagador Obrigatório", "causa_provavel": "A UF do pagador está em branco.", "sugestao_rm": _PENDENTE},
    "47": {"mensagem_banco": "Data da Multa Inválida", "causa_provavel": "A data informada para aplicação da multa não é uma data válida.", "sugestao_rm": _PENDENTE},
    "48": {"mensagem_banco": "Valor da Multa Inválido", "causa_provavel": "O valor da multa informado está num formato inválido.", "sugestao_rm": _PENDENTE},
    "49": {"mensagem_banco": "Prazo de Protesto/Devolução Inválido", "causa_provavel": "O prazo informado está fora do intervalo aceito pela CAIXA.", "sugestao_rm": _PENDENTE},
    "50": {"mensagem_banco": "Prazo do Protesto Inválido", "causa_provavel": "O prazo específico de protesto está fora do intervalo aceito (2 a 90 dias).", "sugestao_rm": _PENDENTE},
    "51": {"mensagem_banco": "Prazo de Devolução Inválido", "causa_provavel": "O prazo específico de devolução está fora do intervalo aceito (15 a 99 dias).", "sugestao_rm": _PENDENTE},
    "52": {"mensagem_banco": "Moeda Inválida", "causa_provavel": "O código da moeda informado não é '1' (Real).", "sugestao_rm": _PENDENTE},
    "53": {"mensagem_banco": "'Uso da Empresa' Obrigatório", "causa_provavel": "O campo de identificação interna do título (Seu Número) está em branco quando era necessário.", "sugestao_rm": _PENDENTE},
    "54": {"mensagem_banco": "Remessa sem Registro Tipo 9", "causa_provavel": "O arquivo não tem o registro trailer (tipo 9).", "sugestao_rm": _PENDENTE},
    "55": {"mensagem_banco": "Solicitação Não Permitida para Título Incluído Somente para Protesto", "causa_provavel": "Foi enviado um movimento incompatível com um título que só foi cadastrado para fins de protesto.", "sugestao_rm": _PENDENTE},
    "60": {"mensagem_banco": "Identificação da Emissão do Bloqueto Inválida", "causa_provavel": "O código informado não é '1' (banco emite) nem '2' (cliente emite).", "sugestao_rm": _PENDENTE},
    "61": {"mensagem_banco": "Tipo de Entrega Inválido", "causa_provavel": "O código de distribuição do bloqueto não é reconhecido.", "sugestao_rm": _PENDENTE},
    "62": {"mensagem_banco": "Modalidade do Título Inválida", "causa_provavel": "O código de modalidade (parte do Nosso Número) não é reconhecido.", "sugestao_rm": _PENDENTE},
    "63": {"mensagem_banco": "Forma de Entrega de Bloqueto Inválida para Emissão Banco", "causa_provavel": "A combinação de emissor='banco' com a forma de entrega escolhida não é permitida.", "sugestao_rm": _PENDENTE},
    "64": {"mensagem_banco": "Forma de Entrega de Bloqueto Inválida para Emissão Cedente", "causa_provavel": "A combinação de emissor='cliente' com a forma de entrega escolhida não é permitida.", "sugestao_rm": _PENDENTE},
    "65": {"mensagem_banco": "Forma de Emissão de Bloqueto Inválida", "causa_provavel": "O código de emissão do bloqueto não é reconhecido.", "sugestao_rm": _PENDENTE},
    "66": {"mensagem_banco": "E-mail Inválido", "causa_provavel": "O e-mail informado (para envio do bloqueto) não está num formato válido.", "sugestao_rm": _PENDENTE},
    "67": {"mensagem_banco": "Número do DDD do Celular do Sacado Inválido", "causa_provavel": "O DDD informado para SMS não é válido.", "sugestao_rm": _PENDENTE},
    "68": {"mensagem_banco": "Número do Celular do Sacado Inválido", "causa_provavel": "O número de celular informado para SMS não é válido.", "sugestao_rm": _PENDENTE},
    "69": {"mensagem_banco": "Tipo de Mensagem de Envio SMS Inválido", "causa_provavel": "O código do tipo de mensagem SMS não é reconhecido.", "sugestao_rm": _PENDENTE},
    "70": {"mensagem_banco": "Envio de SMS do Cedente Inválido", "causa_provavel": "A configuração de envio de SMS pelo cedente está incorreta.", "sugestao_rm": _PENDENTE},
    "71": {"mensagem_banco": "Reenvio de SMS Diferente de SMS ou SMS e Postagem Inválido", "causa_provavel": "A combinação de opções de reenvio de SMS não é uma combinação válida.", "sugestao_rm": _PENDENTE},
}

# --------------------------------------------------------------------
# CNAB 240 -- rejeição de entrada (fonte: TOTVS, lista PARCIAL)
# --------------------------------------------------------------------
ERROS_REJEICAO_ENTRADA_240: dict[str, dict[str, str]] = {
    "AJ": {"mensagem_banco": "Código do Pagador Inválido", "causa_provavel": "O código de identificação do pagador enviado no título não é válido para a Caixa.", "sugestao_rm": _PENDENTE},
    "AK": {"mensagem_banco": "Número da Parcela Inválida ou Fora de Sequência", "causa_provavel": "Em cobrança parcelada, o número da parcela informado não bate com a sequência esperada.", "sugestao_rm": _PENDENTE},
    "AL": {"mensagem_banco": "Estorno de Envio Não Permitido", "causa_provavel": "Foi solicitado o estorno de um envio que não pode mais ser estornado.", "sugestao_rm": _PENDENTE},
    "AM": {"mensagem_banco": "Nosso Número Fora de Sequência", "causa_provavel": "O Nosso Número informado não segue a sequência esperada pela Caixa para esse convênio/carteira.", "sugestao_rm": _PENDENTE},
    "A4": {"mensagem_banco": "Pagador DDA", "causa_provavel": "O pagador está cadastrado no DDA -- é um aviso, não necessariamente um erro impeditivo.", "sugestao_rm": _PENDENTE},
    "B2": {"mensagem_banco": "Valor Nominal do Título Conflitante", "causa_provavel": "O valor do título enviado diverge de um valor já registrado anteriormente na Caixa.", "sugestao_rm": _PENDENTE},
    "CA": {"mensagem_banco": "Autorização de Pagamento Parcial Inválida", "causa_provavel": "O campo que autoriza pagamento parcial do boleto foi preenchido com um valor não aceito.", "sugestao_rm": _PENDENTE},
    "CB": {"mensagem_banco": "Identificação do Tipo de Pagamento Inválida", "causa_provavel": "O código que identifica o tipo de pagamento parcial não é reconhecido.", "sugestao_rm": _PENDENTE},
    "CC": {"mensagem_banco": "Quantidade de Pagamentos Possíveis Inválida", "causa_provavel": "O número de pagamentos parciais permitidos está fora do intervalo aceito.", "sugestao_rm": _PENDENTE},
    "CD": {"mensagem_banco": "Tipo de Valor Máximo Inválido", "causa_provavel": "O código que indica se o valor máximo é percentual ou fixo está errado.", "sugestao_rm": _PENDENTE},
    "CE": {"mensagem_banco": "Valor/Percentual Máximo Inválido", "causa_provavel": "O valor ou percentual máximo de pagamento parcial é inconsistente.", "sugestao_rm": _PENDENTE},
    "CF": {"mensagem_banco": "Tipo de Valor Mínimo Inválido", "causa_provavel": "O código que indica se o valor mínimo é percentual ou fixo está errado.", "sugestao_rm": _PENDENTE},
    "CG": {"mensagem_banco": "Valor/Percentual Mínimo Inválido", "causa_provavel": "O valor ou percentual mínimo de pagamento parcial é inconsistente.", "sugestao_rm": _PENDENTE},
    "CH": {"mensagem_banco": "Segmento Y-53 Não Informado", "causa_provavel": "A operação exige o registro opcional Y-53 e ele não foi enviado.", "sugestao_rm": _PENDENTE},
    "CI": {"mensagem_banco": "Alteração de Limite Inválida para o Tipo de Pagamento", "causa_provavel": "Tentativa de alterar limites de forma incompatível com o tipo de pagamento já cadastrado.", "sugestao_rm": _PENDENTE},
    "CJ": {"mensagem_banco": "Valor/Percentual Igual ao Cadastrado", "causa_provavel": "Foi enviada uma alteração com o mesmo valor já cadastrado -- não há mudança a aplicar.", "sugestao_rm": _PENDENTE},
    "CK": {"mensagem_banco": "Título Autorizado para Pagamento Parcial Não Pode Ser Desautorizado", "causa_provavel": "Tentativa de remover permissão já usada em pagamento parcial.", "sugestao_rm": _PENDENTE},
    "CL": {"mensagem_banco": "Quantidade de Pagamentos Menor que a Realizada", "causa_provavel": "Tentativa de reduzir parcelas permitidas para menos do que já foi pago.", "sugestao_rm": _PENDENTE},
    "VA": {"mensagem_banco": "Arquivo de Retorno Inexistente para Redisponibilização", "causa_provavel": "Foi pedida a redisponibilização de um retorno que não existe para a data/número informados.", "sugestao_rm": _PENDENTE},
    "VB": {"mensagem_banco": "Registro Duplicado", "causa_provavel": "O mesmo registro já foi enviado antes -- parecido com o erro de Nosso Número duplicado do BB.", "sugestao_rm": _PENDENTE},
    "VC": {"mensagem_banco": "Beneficiário Deve Ser Padrão CNAB 240", "causa_provavel": "A operação exige beneficiário configurado como CNAB 240, mas o cadastro está diferente.", "sugestao_rm": _PENDENTE},
}


def buscar_erro(codigo: str, tabela: str = "retorno_400") -> dict[str, str] | None:
    """
    Busca um código de erro numa das tabelas disponíveis.
    tabela: "retorno_400" (padrão), "critica_remessa_400" ou "entrada_240"
    """
    tabelas = {
        "retorno_400": ERROS_REJEICAO_RETORNO_400,
        "critica_remessa_400": ERROS_CRITICA_REMESSA_400,
        "entrada_240": ERROS_REJEICAO_ENTRADA_240,
    }
    return tabelas.get(tabela, ERROS_REJEICAO_RETORNO_400).get(codigo)
