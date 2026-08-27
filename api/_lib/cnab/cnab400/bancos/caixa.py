"""
Layout do CNAB 400 específico da Caixa Econômica Federal (Cobrança
Bancária -- SIGCB).

Fonte: manual oficial "Leiaute de Arquivo Eletrônico Padrão CNAB 400 --
Cobrança Bancária CAIXA - SIGCB" (documento 67.126 v003 micro), fornecido
pelo usuário. Cobre os Anexos I, II, IV (arquivo de Remessa) e V, VI, VII
(arquivo de Retorno).

IMPORTANTE: Remessa e Retorno têm layouts DIFERENTES no registro de
detalhe (tipo 1) -- por isso são listas separadas, não uma só.
"""

from ..layout import CampoLayout400

# --------------------------------------------------------------------
# REMESSA
# --------------------------------------------------------------------

HEADER_REMESSA: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="0"),
    CampoLayout400("Código da Remessa", 2, 2, "num", valor_fixo="1"),
    CampoLayout400("Literal da Remessa", 3, 9, "alfa"),
    CampoLayout400("Código do Serviço", 10, 11, "num", valor_fixo="01"),
    CampoLayout400("Literal de Serviço", 12, 26, "alfa", obrigatorio=False),
    CampoLayout400("Código da Agência", 27, 30, "num"),
    CampoLayout400("Código do Beneficiário", 31, 36, "num"),
    CampoLayout400("Uso Exclusivo CAIXA", 37, 46, "alfa", obrigatorio=False),
    CampoLayout400("Nome da Empresa", 47, 76, "alfa"),
    CampoLayout400("Código do Banco", 77, 79, "num", valor_fixo="104"),
    CampoLayout400("Nome do Banco", 80, 94, "alfa", obrigatorio=False),
    CampoLayout400("Data de Geração", 95, 100, "num"),
    CampoLayout400("Uso Exclusivo CAIXA", 101, 389, "alfa", obrigatorio=False),
    CampoLayout400("Número Sequencial do Arquivo", 390, 394, "num", obrigatorio=False),
    CampoLayout400("Número Sequencial do Registro", 395, 400, "num", valor_fixo="000001"),
]

DETALHE_REMESSA: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="1"),
    CampoLayout400("Tipo de Inscrição da Empresa", 2, 3, "num"),
    CampoLayout400("Número de Inscrição da Empresa", 4, 17, "num"),
    CampoLayout400("Código da Agência", 18, 21, "num"),
    CampoLayout400("Código do Beneficiário", 22, 27, "num"),
    CampoLayout400("Identificação da Emissão do Bloqueto", 28, 28, "num", obrigatorio=False),
    CampoLayout400("Identificação da Entrega do Bloqueto", 29, 29, "num", obrigatorio=False),
    CampoLayout400("Taxa de Permanência", 30, 31, "num", obrigatorio=False),
    CampoLayout400("Uso da Empresa (Seu Número interno)", 32, 56, "alfa", obrigatorio=False),
    CampoLayout400("Modalidade do Nosso Número", 57, 58, "num", obrigatorio=False),
    CampoLayout400("Nosso Número", 59, 73, "num"),
    CampoLayout400("Uso Exclusivo CAIXA", 74, 76, "alfa", obrigatorio=False),
    CampoLayout400("Mensagem", 77, 106, "alfa", obrigatorio=False),
    CampoLayout400("Carteira", 107, 108, "num"),
    CampoLayout400("Código de Ocorrência (movimento remessa)", 109, 110, "num"),
    CampoLayout400("Número do Documento de Cobrança (Seu Número)", 111, 120, "alfa", obrigatorio=False),
    CampoLayout400("Data de Vencimento do Título", 121, 126, "num"),
    CampoLayout400("Valor do Título", 127, 139, "num"),
    CampoLayout400("Código do Banco", 140, 142, "num", valor_fixo="104"),
    CampoLayout400("Agência Cobradora", 143, 147, "num", obrigatorio=False),
    CampoLayout400("Espécie do Título", 148, 149, "num", obrigatorio=False),
    CampoLayout400("Aceite", 150, 150, "alfa", obrigatorio=False),
    CampoLayout400("Data de Emissão do Título", 151, 156, "num", obrigatorio=False),
    CampoLayout400("Instrução 1 (protesto/devolução)", 157, 158, "num", obrigatorio=False),
    CampoLayout400("Instrução 2", 159, 160, "num", obrigatorio=False),
    CampoLayout400("Juros de Mora", 161, 173, "num", obrigatorio=False),
    CampoLayout400("Data do Desconto", 174, 179, "num", obrigatorio=False),
    CampoLayout400("Valor do Desconto", 180, 192, "num", obrigatorio=False),
    CampoLayout400("Valor do IOF", 193, 205, "num", obrigatorio=False),
    CampoLayout400("Valor do Abatimento", 206, 218, "num", obrigatorio=False),
    CampoLayout400("Tipo de Inscrição do Pagador", 219, 220, "num"),
    CampoLayout400("Número de Inscrição do Pagador", 221, 234, "num"),
    CampoLayout400("Nome do Pagador", 235, 274, "alfa"),
    CampoLayout400("Endereço do Pagador", 275, 314, "alfa", obrigatorio=False),
    CampoLayout400("Bairro do Pagador", 315, 326, "alfa", obrigatorio=False),
    CampoLayout400("CEP do Pagador", 327, 334, "num", obrigatorio=False),
    CampoLayout400("Cidade do Pagador", 335, 349, "alfa", obrigatorio=False),
    CampoLayout400("UF do Pagador", 350, 351, "alfa", obrigatorio=False),
    CampoLayout400("Data da Multa", 352, 357, "num", obrigatorio=False),
    CampoLayout400("Valor da Multa", 358, 367, "num", obrigatorio=False),
    CampoLayout400("Nome do Sacador/Avalista", 368, 389, "alfa", obrigatorio=False),
    CampoLayout400("Instrução 3 (mensagem no verso)", 390, 391, "num", obrigatorio=False),
    CampoLayout400("Prazo para Protesto/Devolução", 392, 393, "num", obrigatorio=False),
    CampoLayout400("Código da Moeda", 394, 394, "num", valor_fixo="1"),
    CampoLayout400("Número Sequencial do Registro", 395, 400, "num"),
]

TRAILER_REMESSA: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="9"),
    CampoLayout400("Uso Exclusivo CAIXA", 2, 394, "alfa", obrigatorio=False),
    CampoLayout400("Número Sequencial do Registro", 395, 400, "num"),
]

# --------------------------------------------------------------------
# RETORNO
# --------------------------------------------------------------------

HEADER_RETORNO: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="0"),
    CampoLayout400("Código do Retorno", 2, 2, "num", valor_fixo="2"),
    CampoLayout400("Literal do Retorno", 3, 9, "alfa"),
    CampoLayout400("Código do Serviço", 10, 11, "num", valor_fixo="01"),
    CampoLayout400("Literal de Serviço", 12, 26, "alfa", obrigatorio=False),
    CampoLayout400("Código da Agência", 27, 30, "num"),
    CampoLayout400("Código do Beneficiário", 31, 36, "num"),
    CampoLayout400("Uso Exclusivo CAIXA", 37, 46, "alfa", obrigatorio=False),
    CampoLayout400("Nome da Empresa", 47, 76, "alfa"),
    CampoLayout400("Código do Banco", 77, 79, "num", valor_fixo="104"),
    CampoLayout400("Nome do Banco", 80, 94, "alfa", obrigatorio=False),
    CampoLayout400("Data de Geração", 95, 100, "num"),
    CampoLayout400("Mensagem", 101, 158, "alfa", obrigatorio=False),
    CampoLayout400("Uso Exclusivo CAIXA", 159, 389, "alfa", obrigatorio=False),
    CampoLayout400("Número Sequencial do Arquivo", 390, 394, "num", obrigatorio=False),
    CampoLayout400("Número Sequencial do Registro", 395, 400, "num", valor_fixo="000001"),
]

DETALHE_RETORNO: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="1"),
    CampoLayout400("Tipo de Inscrição da Empresa", 2, 3, "num"),
    CampoLayout400("Número de Inscrição da Empresa", 4, 17, "num"),
    CampoLayout400("Código da Agência", 18, 21, "num"),
    CampoLayout400("Código do Beneficiário", 22, 27, "num"),
    CampoLayout400("Identificação da Emissão do Bloqueto", 28, 28, "num", obrigatorio=False),
    CampoLayout400("Identificação da Entrega do Bloqueto", 29, 29, "num", obrigatorio=False),
    CampoLayout400("Uso Exclusivo CAIXA", 30, 31, "alfa", obrigatorio=False),
    CampoLayout400("Uso da Empresa", 32, 56, "alfa", obrigatorio=False),
    CampoLayout400("Modalidade do Nosso Número", 57, 58, "num", obrigatorio=False),
    CampoLayout400("Nosso Número", 59, 73, "num"),
    CampoLayout400("Uso Exclusivo CAIXA", 74, 79, "alfa", obrigatorio=False),
    CampoLayout400("Código do Motivo da Rejeição", 80, 82, "num", obrigatorio=False),
    CampoLayout400("Uso Exclusivo CAIXA", 83, 106, "alfa", obrigatorio=False),
    CampoLayout400("Carteira", 107, 108, "num"),
    CampoLayout400("Código de Ocorrência", 109, 110, "num"),
    CampoLayout400("Data da Ocorrência", 111, 116, "num", obrigatorio=False),
    CampoLayout400("Número do Documento de Cobrança", 117, 126, "alfa", obrigatorio=False),
    CampoLayout400("Uso Exclusivo CAIXA", 127, 146, "alfa", obrigatorio=False),
    CampoLayout400("Data de Vencimento do Título", 147, 152, "num", obrigatorio=False),
    CampoLayout400("Valor do Título", 153, 165, "num", obrigatorio=False),
    CampoLayout400("Código do Banco", 166, 168, "num", valor_fixo="104"),
    CampoLayout400("Agência Cobradora", 169, 173, "num", obrigatorio=False),
    CampoLayout400("Espécie do Título", 174, 175, "num", obrigatorio=False),
    CampoLayout400("Valor da Tarifa/Despesa de Cobrança", 176, 188, "num", obrigatorio=False),
    CampoLayout400("Código do Canal de Liquidação/Baixa", 189, 191, "num", obrigatorio=False),
    CampoLayout400("Código da Forma de Pagamento", 192, 192, "num", obrigatorio=False),
    CampoLayout400("Float Negociado", 193, 194, "num", obrigatorio=False),
    CampoLayout400("Data do Débito da Tarifa", 195, 200, "num", obrigatorio=False),
    CampoLayout400("Uso Exclusivo CAIXA", 201, 214, "alfa", obrigatorio=False),
    CampoLayout400("Valor do IOF", 215, 227, "num", obrigatorio=False),
    CampoLayout400("Valor do Abatimento", 228, 240, "num", obrigatorio=False),
    CampoLayout400("Valor do Desconto", 241, 253, "num", obrigatorio=False),
    CampoLayout400("Valor Principal Pago", 254, 266, "num", obrigatorio=False),
    CampoLayout400("Valor dos Juros Pagos", 267, 279, "num", obrigatorio=False),
    CampoLayout400("Valor da Multa Paga", 280, 292, "num", obrigatorio=False),
    CampoLayout400("Código da Moeda", 293, 293, "num", obrigatorio=False),
    CampoLayout400("Data do Crédito", 294, 299, "num", obrigatorio=False),
    CampoLayout400("Uso Exclusivo CAIXA", 300, 394, "alfa", obrigatorio=False),
    CampoLayout400("Número Sequencial do Registro", 395, 400, "num"),
]

TRAILER_RETORNO: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="9"),
    CampoLayout400("Código do Retorno", 2, 2, "num", valor_fixo="2"),
    CampoLayout400("Código do Serviço", 3, 4, "num", valor_fixo="01"),
    CampoLayout400("Código do Banco", 5, 7, "num", valor_fixo="104"),
    CampoLayout400("Uso Exclusivo CAIXA", 8, 394, "alfa", obrigatorio=False),
    CampoLayout400("Número Sequencial do Registro", 395, 400, "num"),
]
