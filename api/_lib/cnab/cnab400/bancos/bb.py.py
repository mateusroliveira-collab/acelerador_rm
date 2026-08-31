"""
Layout do CNAB 400 específico do Banco do Brasil (Cobrança).

Fonte:
- Remessa: Manual CBR641 (Convênios acima de 1.000.000) - Julho/2026.
- Retorno: Manual CBR643 (Convênios acima de 1.000.000) - Julho/2023.

Assim como a Caixa, Remessa e Retorno têm layouts diferentes no registro de
detalhe. Focamos na validação base estrutural obrigatória (0, 7, 9).
"""

from ..layout import CampoLayout400

# --------------------------------------------------------------------
# REMESSA (CBR641)
# --------------------------------------------------------------------
HEADER_REMESSA: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="0"),
    CampoLayout400("Tipo de Operação", 2, 2, "num", valor_fixo="1"),
    CampoLayout400("Identificação por Extenso", 3, 9, "alfa", valor_fixo="REMESSA"),
    CampoLayout400("Tipo de Serviço", 10, 11, "num", valor_fixo="01"),
    CampoLayout400("Identificação por Extenso", 12, 19, "alfa", valor_fixo="COBRANCA"),
    CampoLayout400("Complemento", 20, 26, "alfa", obrigatorio=False),
    CampoLayout400("Prefixo da Agência", 27, 30, "num"),
    CampoLayout400("DV do Prefixo", 31, 31, "alfa"),
    CampoLayout400("Número da Conta Corrente", 32, 39, "num"),
    CampoLayout400("DV da Conta Corrente", 40, 40, "alfa"),
    CampoLayout400("Complemento (Zeros)", 41, 46, "num", valor_fixo="000000"),
    CampoLayout400("Nome do Beneficiário", 47, 76, "alfa"),
    CampoLayout400("Nome do Banco", 77, 94, "alfa", valor_fixo="001BANCODOBRASIL"),
    CampoLayout400("Data da Gravação", 95, 100, "num"),
    CampoLayout400("Sequencial da Remessa", 101, 107, "num"),
    CampoLayout400("Complemento", 108, 129, "alfa", obrigatorio=False),
    CampoLayout400("Número do Convênio", 130, 136, "num"),
    CampoLayout400("Complemento", 137, 394, "alfa", obrigatorio=False),
    CampoLayout400("Sequencial do Registro", 395, 400, "num", valor_fixo="000001"),
]

DETALHE_REMESSA: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="7"),
    CampoLayout400("Tipo de Inscrição Beneficiário", 2, 3, "num"),
    CampoLayout400("CPF/CNPJ Beneficiário", 4, 17, "num"),
    CampoLayout400("Prefixo da Agência", 18, 21, "num"),
    CampoLayout400("DV do Prefixo", 22, 22, "alfa"),
    CampoLayout400("Número da Conta", 23, 30, "num"),
    CampoLayout400("DV da Conta", 31, 31, "alfa"),
    CampoLayout400("Número do Convênio", 32, 38, "num"),
    CampoLayout400("Código de Controle da Empresa", 39, 63, "alfa", obrigatorio=False),
    CampoLayout400("Nosso Número", 64, 80, "num"),
    CampoLayout400("Número da Prestação", 81, 82, "num", valor_fixo="00"),
    CampoLayout400("Grupo de Valor", 83, 84, "num", valor_fixo="00"),
    CampoLayout400("Tipo de Moeda", 85, 86, "alfa", obrigatorio=False),
    CampoLayout400("Complemento", 87, 87, "alfa", obrigatorio=False),
    CampoLayout400("Indicativo Mensagem/Avalista", 88, 88, "alfa", obrigatorio=False),
    CampoLayout400("Prefixo do Título", 89, 91, "alfa", obrigatorio=False),
    CampoLayout400("Variação da Carteira", 92, 94, "num"),
    CampoLayout400("Conta Caução", 95, 95, "num", valor_fixo="0"),
    CampoLayout400("Número do Borderô", 96, 101, "num", valor_fixo="000000"),
    CampoLayout400("Tipo de Cobrança", 102, 106, "alfa", obrigatorio=False),
    CampoLayout400("Carteira de Cobrança", 107, 108, "num"),
    CampoLayout400("Comando", 109, 110, "num"),
    CampoLayout400("Seu Número", 111, 120, "alfa", obrigatorio=False),
    CampoLayout400("Data de Vencimento", 121, 126, "num"),
    CampoLayout400("Valor do Título", 127, 139, "num"),
    CampoLayout400("Número do Banco", 140, 142, "num", valor_fixo="001"),
    CampoLayout400("Agência Cobradora", 143, 146, "num", obrigatorio=False),
    CampoLayout400("DV Agência Cobradora", 147, 147, "alfa", obrigatorio=False),
    CampoLayout400("Espécie de Título", 148, 149, "num"),
    CampoLayout400("Aceite do Título", 150, 150, "alfa"),
    CampoLayout400("Data de Emissão", 151, 156, "num"),
    CampoLayout400("Instrução Codificada 1", 157, 158, "num", obrigatorio=False),
    CampoLayout400("Instrução Codificada 2", 159, 160, "num", obrigatorio=False),
    CampoLayout400("Juros de Mora", 161, 173, "num", obrigatorio=False),
    CampoLayout400("Data Limite Desconto", 174, 179, "num", obrigatorio=False),
    CampoLayout400("Valor do Desconto", 180, 192, "num", obrigatorio=False),
    CampoLayout400("Valor do IOF", 193, 205, "num", obrigatorio=False),
    CampoLayout400("Valor do Abatimento", 206, 218, "num", obrigatorio=False),
    CampoLayout400("Tipo Inscrição Pagador", 219, 220, "num"),
    CampoLayout400("CPF/CNPJ Pagador", 221, 234, "num"),
    CampoLayout400("Nome do Pagador", 235, 271, "alfa"),
    CampoLayout400("Complemento", 272, 274, "alfa", obrigatorio=False),
    CampoLayout400("Endereço do Pagador", 275, 314, "alfa", obrigatorio=False),
    CampoLayout400("Bairro do Pagador", 315, 326, "alfa", obrigatorio=False),
    CampoLayout400("CEP do Pagador", 327, 334, "num", obrigatorio=False),
    CampoLayout400("Cidade do Pagador", 335, 349, "alfa", obrigatorio=False),
    CampoLayout400("UF do Pagador", 350, 351, "alfa", obrigatorio=False),
    CampoLayout400("Observações / Avalista", 352, 391, "alfa", obrigatorio=False),
    CampoLayout400("Dias para Protesto", 392, 393, "num", obrigatorio=False),
    CampoLayout400("Indicador Recebimento Parcial", 394, 394, "alfa", obrigatorio=False),
    CampoLayout400("Sequencial do Registro", 395, 400, "num"),
]

TRAILER_REMESSA: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="9"),
    CampoLayout400("Complemento", 2, 394, "alfa", obrigatorio=False),
    CampoLayout400("Sequencial do Registro", 395, 400, "num"),
]

# --------------------------------------------------------------------
# RETORNO (CBR643)
# --------------------------------------------------------------------
HEADER_RETORNO: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="0"),
    CampoLayout400("Tipo de Operação", 2, 2, "num", valor_fixo="2"),
    CampoLayout400("Identificação por Extenso", 3, 9, "alfa", valor_fixo="RETORNO"),
    CampoLayout400("Tipo de Serviço", 10, 11, "num", valor_fixo="01"),
    CampoLayout400("Identificação por Extenso", 12, 19, "alfa", valor_fixo="COBRANCA"),
    CampoLayout400("Complemento", 20, 26, "alfa", obrigatorio=False),
    CampoLayout400("Prefixo da Agência", 27, 30, "num"),
    CampoLayout400("DV do Prefixo", 31, 31, "alfa"),
    CampoLayout400("Número da Conta Corrente", 32, 39, "num"),
    CampoLayout400("DV da Conta Corrente", 40, 40, "alfa"),
    CampoLayout400("Complemento (Zeros)", 41, 46, "num", valor_fixo="000000"),
    CampoLayout400("Nome do Cedente", 47, 76, "alfa"),
    CampoLayout400("Nome do Banco", 77, 94, "alfa", valor_fixo="001BANCODOBRASIL"),
    CampoLayout400("Data da Gravação", 95, 100, "num"),
    CampoLayout400("Sequencial do Retorno", 101, 107, "num"),
    CampoLayout400("Complemento", 108, 149, "alfa", obrigatorio=False),
    CampoLayout400("Número do Convênio", 150, 156, "num"),
    CampoLayout400("Complemento", 157, 394, "alfa", obrigatorio=False),
    CampoLayout400("Sequencial do Registro", 395, 400, "num"),
]

DETALHE_RETORNO: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="7"),
    CampoLayout400("Zeros", 2, 17, "num", obrigatorio=False),
    CampoLayout400("Prefixo da Agência", 18, 21, "num"),
    CampoLayout400("DV do Prefixo", 22, 22, "alfa"),
    CampoLayout400("Número da Conta", 23, 30, "num"),
    CampoLayout400("DV da Conta", 31, 31, "alfa"),
    CampoLayout400("Número do Convênio", 32, 38, "num"),
    CampoLayout400("Controle do Participante", 39, 63, "alfa", obrigatorio=False),
    CampoLayout400("Nosso Número", 64, 80, "num"),
    CampoLayout400("Tipo de Cobrança", 81, 81, "num"),
    CampoLayout400("Tipo de Cobrança (Cmd 72)", 82, 82, "num", obrigatorio=False),
    CampoLayout400("Dias para Cálculo", 83, 86, "num", obrigatorio=False),
    CampoLayout400("Natureza Recebimento", 87, 88, "num", obrigatorio=False),
    CampoLayout400("Prefixo do Boleto", 89, 91, "alfa", obrigatorio=False),
    CampoLayout400("Variação da Carteira", 92, 94, "num"),
    CampoLayout400("Conta Caução", 95, 95, "num", obrigatorio=False),
    CampoLayout400("Taxa para Desconto", 96, 100, "num", obrigatorio=False),
    CampoLayout400("Taxa IOF", 101, 105, "num", obrigatorio=False),
    CampoLayout400("Carteira", 107, 108, "num"),
    CampoLayout400("Comando (Ocorrência)", 109, 110, "num"),
    CampoLayout400("Data Liquidação", 111, 116, "num", obrigatorio=False),
    CampoLayout400("Número do Boleto Cedente", 117, 126, "alfa", obrigatorio=False),
    CampoLayout400("Data Vencimento", 147, 152, "num", obrigatorio=False),
    CampoLayout400("Valor do Boleto", 153, 165, "num", obrigatorio=False),
    CampoLayout400("Banco Recebedor", 166, 168, "num", obrigatorio=False),
    CampoLayout400("Agência Recebedora", 169, 172, "num", obrigatorio=False),
    CampoLayout400("DV Agência Recebedora", 173, 173, "alfa", obrigatorio=False),
    CampoLayout400("Espécie", 174, 175, "num", obrigatorio=False),
    CampoLayout400("Data do Crédito", 176, 181, "num", obrigatorio=False),
    CampoLayout400("Valor Tarifa", 182, 188, "num", obrigatorio=False),
    CampoLayout400("Outras Despesas", 189, 201, "num", obrigatorio=False),
    CampoLayout400("Juros do Desconto", 202, 214, "num", obrigatorio=False),
    CampoLayout400("IOF Desconto", 215, 227, "num", obrigatorio=False),
    CampoLayout400("Valor Abatimento", 228, 240, "num", obrigatorio=False),
    CampoLayout400("Desconto Concedido", 241, 253, "num", obrigatorio=False),
    CampoLayout400("Valor Recebido", 254, 266, "num", obrigatorio=False),
    CampoLayout400("Juros de Mora", 267, 279, "num", obrigatorio=False),
    CampoLayout400("Outros Recebimentos", 280, 292, "num", obrigatorio=False),
    CampoLayout400("Abatimento Não Aproveitado", 293, 305, "num", obrigatorio=False),
    CampoLayout400("Valor Lançamento", 306, 318, "num", obrigatorio=False),
    CampoLayout400("Indicativo Débito/Crédito", 319, 319, "num", obrigatorio=False),
    CampoLayout400("Indicador Valor", 320, 320, "num", obrigatorio=False),
    CampoLayout400("Valor Ajuste", 321, 332, "num", obrigatorio=False),
    CampoLayout400("Canal de Pagamento", 393, 394, "num", obrigatorio=False),
    CampoLayout400("Sequencial do Registro", 395, 400, "num"),
]

TRAILER_RETORNO: list[CampoLayout400] = [
    CampoLayout400("Código do Registro", 1, 1, "num", valor_fixo="9"),
    CampoLayout400("Tipo de Operação", 2, 2, "num", valor_fixo="2"),
    CampoLayout400("Tipo de Serviço", 3, 4, "num", valor_fixo="01"),
    CampoLayout400("Código do Banco", 5, 7, "num", valor_fixo="001"),
    CampoLayout400("Complemento", 8, 394, "alfa", obrigatorio=False),
    CampoLayout400("Sequencial do Registro", 395, 400, "num"),
]