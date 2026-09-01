"""
Layout padrão FEBRABAN do CNAB 240 -- só os registros que são idênticos
independente do banco: Header de Arquivo, Header de Lote (parte fixa),
Trailer de Lote, Trailer de Arquivo.

Os registros de Segmento (detalhe -- A, B, J, O, P, Q, R etc.) variam de
acordo com o tipo de serviço/operação e AINDA NÃO estão aqui. É o próximo
incremento natural, depois que esse esqueleto estiver validado.

Fonte: Layout Padrão FEBRABAN CNAB 240 (documento público,
cmsarquivos.febraban.org.br). A FEBRABAN revisa esse layout periodicamente
(ex: V10.9, V10.11...) -- confira contra a versão vigente antes de usar em
produção de verdade.
"""

from dataclasses import dataclass


@dataclass
class CampoLayout:
    nome: str
    inicio: int  # posição inicial, base 1 (igual ao manual FEBRABAN)
    fim: int  # posição final, inclusiva
    tipo: str  # "num" ou "alfa"
    obrigatorio: bool = True
    valor_fixo: str | None = None  # ex: '0' no tipo de registro do header

    @property
    def tamanho(self) -> int:
        return self.fim - self.inicio + 1


TAMANHO_LINHA = 240

HEADER_ARQUIVO: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num", valor_fixo="0000"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="0"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 9, 17, "alfa", obrigatorio=False),
    CampoLayout("Tipo de Inscrição da Empresa", 18, 18, "num"),
    CampoLayout("Número de Inscrição da Empresa", 19, 32, "num"),
    CampoLayout("Código do Convênio no Banco", 33, 52, "alfa", obrigatorio=False),
    CampoLayout("Agência Mantenedora da Conta", 53, 57, "num"),
    CampoLayout("Dígito Verificador da Agência", 58, 58, "alfa", obrigatorio=False),
    CampoLayout("Número da Conta Corrente", 59, 70, "num"),
    CampoLayout("Dígito Verificador da Conta", 71, 71, "alfa", obrigatorio=False),
    CampoLayout("Dígito Verificador da Ag/Conta", 72, 72, "alfa", obrigatorio=False),
    CampoLayout("Nome da Empresa", 73, 102, "alfa"),
    CampoLayout("Nome do Banco", 103, 132, "alfa"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 133, 142, "alfa", obrigatorio=False),
    CampoLayout("Código Remessa / Retorno", 143, 143, "num"),
    CampoLayout("Data de Geração do Arquivo", 144, 151, "num"),
    CampoLayout("Hora de Geração do Arquivo", 152, 157, "num"),
    CampoLayout("Número Sequencial do Arquivo", 158, 163, "num"),
    CampoLayout("Número da Versão do Layout do Arquivo", 164, 166, "num"),
    CampoLayout("Densidade de Gravação do Arquivo", 167, 171, "num", obrigatorio=False),
    CampoLayout("Para Uso Reservado do Banco", 172, 191, "alfa", obrigatorio=False),
    CampoLayout("Para Uso Reservado da Empresa", 192, 211, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 212, 240, "alfa", obrigatorio=False),
]

# Header de Lote: só a parte inicial fixa (posições 1-11), que é comum a
# qualquer tipo de serviço. O restante do header de lote varia bastante
# conforme o serviço/versão -- fica pro próximo incremento.
HEADER_LOTE: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="1"),
    CampoLayout("Tipo da Operação", 9, 9, "alfa"),
    CampoLayout("Tipo do Serviço", 10, 11, "num"),
]

TRAILER_LOTE: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="5"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 9, 17, "alfa", obrigatorio=False),
    CampoLayout("Quantidade de Registros do Lote", 18, 23, "num"),
]

TRAILER_ARQUIVO: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num", valor_fixo="9999"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="9"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 9, 17, "alfa", obrigatorio=False),
    CampoLayout("Quantidade de Lotes do Arquivo", 18, 23, "num"),
    CampoLayout("Quantidade de Registros do Arquivo", 24, 29, "num"),
]

# ---------------------------------------------------------------------------
# Segmentos de detalhe -- carregam o dado de negócio de verdade.
# Fonte: Manual FEBRABAN CNAB 240 V10.11, seções 3.1.2 (Pagamentos,
# segmentos A/B) e 3.2.2 (Cobrança, segmentos P/Q/R).
# ---------------------------------------------------------------------------

# Segmento A -- pagamento (crédito em conta, cheque, OP, DOC, TED)
SEGMENTO_A: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="A"),
    CampoLayout("Tipo de Movimento", 15, 15, "num"),
    CampoLayout("Código da Instrução para Movimento", 16, 17, "num"),
    CampoLayout("Código da Câmara Centralizadora", 18, 20, "num", obrigatorio=False),
    CampoLayout("Código do Banco do Favorecido", 21, 23, "num"),
    CampoLayout("Agência Mantenedora da Conta do Favorecido", 24, 28, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Agência", 29, 29, "alfa", obrigatorio=False),
    CampoLayout("Número da Conta Corrente do Favorecido", 30, 41, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Conta", 42, 42, "alfa", obrigatorio=False),
    CampoLayout("Dígito Verificador da Ag/Conta", 43, 43, "alfa", obrigatorio=False),
    CampoLayout("Nome do Favorecido", 44, 73, "alfa"),
    CampoLayout("Seu Número (documento atribuído pela empresa)", 74, 93, "alfa", obrigatorio=False),
    CampoLayout("Data do Pagamento", 94, 101, "num"),
    CampoLayout("Tipo da Moeda", 102, 104, "alfa", obrigatorio=False),
    CampoLayout("Quantidade da Moeda", 105, 119, "num", obrigatorio=False),
    CampoLayout("Valor do Pagamento", 120, 134, "num"),
    CampoLayout("Nosso Número (documento atribuído pelo banco)", 135, 154, "alfa", obrigatorio=False),
    CampoLayout("Data Real da Efetivação do Pagamento", 155, 162, "num", obrigatorio=False),
    CampoLayout("Valor Real da Efetivação do Pagamento", 163, 177, "num", obrigatorio=False),
    CampoLayout("Informação 2", 178, 217, "alfa", obrigatorio=False),
    CampoLayout("Código Finalidade do Documento", 218, 219, "alfa", obrigatorio=False),
    CampoLayout("Código Finalidade da TED", 220, 224, "alfa", obrigatorio=False),
    CampoLayout("Código Finalidade Complementar", 225, 226, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 227, 229, "alfa", obrigatorio=False),
    CampoLayout("Aviso ao Favorecido", 230, 230, "num", obrigatorio=False),
    CampoLayout("Códigos das Ocorrências para Retorno", 231, 240, "alfa", obrigatorio=False),
]

# Segmento B -- complementar ao A (dados adicionais do favorecido)
SEGMENTO_B: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="B"),
    CampoLayout("Forma de Iniciação", 15, 17, "alfa", obrigatorio=False),
    CampoLayout("Tipo de Inscrição do Favorecido", 18, 18, "num"),
    CampoLayout("Número de Inscrição do Favorecido", 19, 32, "num"),
    CampoLayout("Dados Complementares -- Informação 10", 33, 67, "alfa", obrigatorio=False),
    CampoLayout("Dados Complementares -- Informação 11", 68, 127, "alfa", obrigatorio=False),
    CampoLayout("Dados Complementares -- Informação 12", 128, 226, "alfa", obrigatorio=False),
    CampoLayout("Código UG Centralizadora (uso SIAPE)", 227, 232, "num", obrigatorio=False),
    CampoLayout("Identificação do Banco no SPB (ISPB)", 233, 240, "num", obrigatorio=False),
]

# Segmento P -- cobrança/boleto: dados principais do título
SEGMENTO_P: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="P"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 15, 15, "alfa", obrigatorio=False),
    CampoLayout("Código de Movimento Remessa", 16, 17, "num"),
    CampoLayout("Agência Mantenedora da Conta", 18, 22, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Agência", 23, 23, "alfa", obrigatorio=False),
    CampoLayout("Número da Conta Corrente", 24, 35, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Conta", 36, 36, "alfa", obrigatorio=False),
    CampoLayout("Dígito Verificador da Ag/Conta", 37, 37, "alfa", obrigatorio=False),
    CampoLayout("Nosso Número (identificação do título no banco)", 38, 57, "alfa"),
    CampoLayout("Código da Carteira", 58, 58, "num"),
    CampoLayout("Forma de Cadastramento do Título no Banco", 59, 59, "num", obrigatorio=False),
    CampoLayout("Tipo de Documento", 60, 60, "alfa", obrigatorio=False),
    CampoLayout("Identificação da Emissão do Boleto", 61, 61, "num", obrigatorio=False),
    CampoLayout("Identificação da Distribuição", 62, 62, "alfa", obrigatorio=False),
    CampoLayout("Número do Documento de Cobrança", 63, 77, "alfa", obrigatorio=False),
    CampoLayout("Data de Vencimento do Título", 78, 85, "num"),
    CampoLayout("Valor Nominal do Título", 86, 100, "num"),
    CampoLayout("Agência Encarregada da Cobrança", 101, 105, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Agência Cobradora", 106, 106, "alfa", obrigatorio=False),
    CampoLayout("Espécie do Título", 107, 108, "num", obrigatorio=False),
    CampoLayout("Identificação de Título Aceito/Não Aceito", 109, 109, "alfa", obrigatorio=False),
    CampoLayout("Data da Emissão do Título", 110, 117, "num", obrigatorio=False),
    CampoLayout("Código do Juros de Mora", 118, 118, "num", obrigatorio=False),
    CampoLayout("Data do Juros de Mora", 119, 126, "num", obrigatorio=False),
    CampoLayout("Juros de Mora por Dia/Taxa", 127, 141, "num", obrigatorio=False),
    CampoLayout("Código do Desconto 1", 142, 142, "num", obrigatorio=False),
    CampoLayout("Data do Desconto 1", 143, 150, "num", obrigatorio=False),
    CampoLayout("Valor/Percentual do Desconto 1", 151, 165, "num", obrigatorio=False),
    CampoLayout("Valor do IOF a Recolher", 166, 180, "num", obrigatorio=False),
    CampoLayout("Valor do Abatimento", 181, 195, "num", obrigatorio=False),
    CampoLayout("Identificação do Título na Empresa", 196, 220, "alfa", obrigatorio=False),
    CampoLayout("Código para Protesto", 221, 221, "num", obrigatorio=False),
    CampoLayout("Número de Dias para Protesto", 222, 223, "num", obrigatorio=False),
    CampoLayout("Código para Baixa/Devolução", 224, 224, "num", obrigatorio=False),
    CampoLayout("Número de Dias para Baixa/Devolução", 225, 227, "alfa", obrigatorio=False),
    CampoLayout("Código da Moeda", 228, 229, "num", obrigatorio=False),
    CampoLayout("Número do Contrato da Operação de Crédito", 230, 239, "num", obrigatorio=False),
    CampoLayout("Uso Livre Banco/Empresa", 240, 240, "alfa", obrigatorio=False),
]

# Segmento Q -- complementar ao P: dados do pagador (e sacador/avalista)
SEGMENTO_Q: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="Q"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 15, 15, "alfa", obrigatorio=False),
    CampoLayout("Código de Movimento Remessa", 16, 17, "num"),
    CampoLayout("Tipo de Inscrição do Pagador", 18, 18, "num"),
    CampoLayout("Número de Inscrição do Pagador", 19, 33, "num"),
    CampoLayout("Nome do Pagador", 34, 73, "alfa"),
    CampoLayout("Endereço do Pagador", 74, 113, "alfa", obrigatorio=False),
    CampoLayout("Bairro", 114, 128, "alfa", obrigatorio=False),
    CampoLayout("CEP", 129, 133, "num", obrigatorio=False),
    CampoLayout("Sufixo do CEP", 134, 136, "num", obrigatorio=False),
    CampoLayout("Cidade", 137, 151, "alfa", obrigatorio=False),
    CampoLayout("UF", 152, 153, "alfa", obrigatorio=False),
    CampoLayout("Tipo de Inscrição do Sacador/Avalista", 154, 154, "num", obrigatorio=False),
    CampoLayout("Número de Inscrição do Sacador/Avalista", 155, 169, "num", obrigatorio=False),
    CampoLayout("Nome do Sacador/Avalista", 170, 209, "alfa", obrigatorio=False),
    CampoLayout("Código do Banco Correspondente", 210, 212, "num", obrigatorio=False),
    CampoLayout("Nosso Número no Banco Correspondente", 213, 232, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 233, 240, "alfa", obrigatorio=False),
]

# Segmento R -- complementar/opcional: descontos extras, multa, débito automático
SEGMENTO_R: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="R"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 15, 15, "alfa", obrigatorio=False),
    CampoLayout("Código de Movimento Remessa", 16, 17, "num"),
    CampoLayout("Código do Desconto 2", 18, 18, "num", obrigatorio=False),
    CampoLayout("Data do Desconto 2", 19, 26, "num", obrigatorio=False),
    CampoLayout("Valor/Percentual do Desconto 2", 27, 41, "num", obrigatorio=False),
    CampoLayout("Código do Desconto 3", 42, 42, "num", obrigatorio=False),
    CampoLayout("Data do Desconto 3", 43, 50, "num", obrigatorio=False),
    CampoLayout("Valor/Percentual do Desconto 3", 51, 65, "num", obrigatorio=False),
    CampoLayout("Código da Multa", 66, 66, "alfa", obrigatorio=False),
    CampoLayout("Data da Multa", 67, 74, "num", obrigatorio=False),
    CampoLayout("Valor/Percentual da Multa", 75, 89, "num", obrigatorio=False),
    CampoLayout("Informação ao Pagador", 90, 99, "alfa", obrigatorio=False),
    CampoLayout("Mensagem 3", 100, 139, "alfa", obrigatorio=False),
    CampoLayout("Mensagem 4", 140, 179, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 180, 199, "alfa", obrigatorio=False),
    CampoLayout("Código de Ocorrência do Pagador", 200, 207, "num", obrigatorio=False),
    CampoLayout("Código do Banco na Conta de Débito", 208, 210, "num", obrigatorio=False),
    CampoLayout("Código da Agência do Débito", 211, 215, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Agência", 216, 216, "alfa", obrigatorio=False),
    CampoLayout("Conta Corrente para Débito", 217, 228, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Conta", 229, 229, "alfa", obrigatorio=False),
    CampoLayout("Dígito Verificador da Ag/Conta", 230, 230, "alfa", obrigatorio=False),
    CampoLayout("Aviso para Débito Automático", 231, 231, "num", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 232, 240, "alfa", obrigatorio=False),
]
# Segmento J -- Pagamento de Títulos / Boletos
SEGMENTO_J: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="J"),
    CampoLayout("Tipo de Movimento", 15, 15, "num"),
    CampoLayout("Código da Instrução para Movimento", 16, 17, "num"),
    CampoLayout("Código de Barras", 18, 61, "alfa"),
    CampoLayout("Nome do Beneficiário", 62, 91, "alfa", obrigatorio=False),
    CampoLayout("Data de Vencimento", 92, 99, "num"),
    CampoLayout("Valor Nominal do Título", 100, 114, "num"),
    CampoLayout("Valor do Desconto + Abatimento", 115, 129, "num", obrigatorio=False),
    CampoLayout("Valor da Mora + Multa", 130, 144, "num", obrigatorio=False),
    CampoLayout("Data do Pagamento", 145, 152, "num"),
    CampoLayout("Valor do Pagamento", 153, 167, "num"),
    CampoLayout("Quantidade da Moeda", 168, 182, "num", obrigatorio=False),
    CampoLayout("Referência Pagador (Seu Número)", 183, 202, "alfa", obrigatorio=False),
    CampoLayout("Nosso Número atribuído pelo Banco", 203, 222, "alfa", obrigatorio=False),
    CampoLayout("Código da Moeda", 223, 224, "num", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 225, 230, "alfa", obrigatorio=False),
    CampoLayout("Códigos das Ocorrências para Retorno", 231, 240, "alfa", obrigatorio=False),
]

# Segmento J52 -- Complemento do J (Dados do Pagador/Beneficiário e FGTS Digital)
SEGMENTO_J52: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="J"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 15, 15, "alfa", obrigatorio=False),
    CampoLayout("Código de Movimento Remessa", 16, 17, "num"),
    CampoLayout("Identificação Registro Opcional", 18, 19, "num", valor_fixo="52"),
    CampoLayout("Tipo de Inscrição do Pagador", 20, 20, "num"),
    CampoLayout("Número de Inscrição do Pagador", 21, 35, "num"),
    CampoLayout("Nome do Pagador", 36, 75, "alfa"),
    CampoLayout("Tipo de Inscrição do Beneficiário", 76, 76, "num"),
    CampoLayout("Número de Inscrição do Beneficiário", 77, 91, "num"),
    CampoLayout("Nome do Beneficiário", 92, 131, "alfa"),
    CampoLayout("Tipo Inscrição Avalista / URL FGTS Digital", 132, 132, "alfa", obrigatorio=False),
    CampoLayout("Num Inscrição Avalista / URL FGTS Digital", 133, 147, "alfa", obrigatorio=False),
    CampoLayout("Nome Avalista / URL FGTS Digital", 148, 187, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 188, 240, "alfa", obrigatorio=False),
]

# Segmento N -- Pagamento de Tributos S/ Código de Barras (GPS, DARF, GARE)
SEGMENTO_N: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="N"),
    CampoLayout("Tipo de Movimento", 15, 15, "num"),
    CampoLayout("Código da Instrução para Movimento", 16, 17, "num"),
    CampoLayout("Seu Número", 18, 37, "alfa", obrigatorio=False),
    CampoLayout("Nosso Número", 38, 57, "alfa", obrigatorio=False),
    CampoLayout("Nome do Contribuinte", 58, 87, "alfa"),
    CampoLayout("Data do Pagamento", 88, 95, "num"),
    CampoLayout("Valor do Pagamento", 96, 110, "num"),
    CampoLayout("Informações Complementares do Tributo", 111, 230, "alfa", obrigatorio=False),
    CampoLayout("Códigos das Ocorrências para Retorno", 231, 240, "alfa", obrigatorio=False),
]

# Segmento O -- Pagamento de Tributos/Concessionárias C/ Código de Barras
SEGMENTO_O: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="O"),
    CampoLayout("Tipo de Movimento", 15, 15, "num"),
    CampoLayout("Código da Instrução para Movimento", 16, 17, "num"),
    CampoLayout("Código de Barras", 18, 61, "alfa"),
    CampoLayout("Nome da Concessionária/Órgão Público", 62, 91, "alfa", obrigatorio=False),
    CampoLayout("Data de Vencimento", 92, 99, "num"),
    CampoLayout("Data do Pagamento", 100, 107, "num"),
    CampoLayout("Valor do Pagamento", 108, 122, "num"),
    CampoLayout("Seu Número", 123, 142, "alfa", obrigatorio=False),
    CampoLayout("Nosso Número", 143, 162, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 163, 230, "alfa", obrigatorio=False),
    CampoLayout("Códigos das Ocorrências para Retorno", 231, 240, "alfa", obrigatorio=False),
]

# Segmento W -- Informações Complementares (ex: Rateio, FGTS)
SEGMENTO_W: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="W"),
    CampoLayout("Número Sequencial do Registro Complementar", 15, 15, "num"),
    CampoLayout("Identifica Uso da Informação", 16, 16, "alfa", obrigatorio=False),
    CampoLayout("Informação Complementar 1", 17, 96, "alfa", obrigatorio=False),
    CampoLayout("Informação Complementar 2", 97, 176, "alfa", obrigatorio=False),
    CampoLayout("Identificador do Tributo", 177, 178, "alfa", obrigatorio=False),
    CampoLayout("Informação Complementar do Tributo", 179, 228, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 229, 230, "alfa", obrigatorio=False),
    CampoLayout("Códigos das Ocorrências para Retorno", 231, 240, "alfa", obrigatorio=False),
]

# Segmento Z -- Autenticação Bancária (Retorno de Pagamento)
SEGMENTO_Z: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="Z"),
    CampoLayout("Autenticação para Atender Legislação", 15, 78, "alfa", obrigatorio=False),
    CampoLayout("Autenticação Bancária/Protocolo", 79, 103, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 104, 230, "alfa", obrigatorio=False),
    CampoLayout("Códigos das Ocorrências para Retorno", 231, 240, "alfa", obrigatorio=False),
]

# Segmento E -- Extrato de Conta Corrente (Conciliação Bancária)
SEGMENTO_E: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="E"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 15, 15, "alfa", obrigatorio=False),
    CampoLayout("Tipo de Inscrição da Empresa", 16, 16, "num", obrigatorio=False),
    CampoLayout("Número de Inscrição da Empresa", 17, 30, "num", obrigatorio=False),
    CampoLayout("Código do Convênio no Banco", 31, 50, "alfa", obrigatorio=False),
    CampoLayout("Agência Mantenedora da Conta", 51, 55, "num"),
    CampoLayout("Dígito Verificador da Agência", 56, 56, "alfa", obrigatorio=False),
    CampoLayout("Número da Conta Corrente", 57, 68, "num"),
    CampoLayout("Dígito Verificador da Conta", 69, 69, "alfa", obrigatorio=False),
    CampoLayout("Dígito Verificador da Ag/Conta", 70, 70, "alfa", obrigatorio=False),
    CampoLayout("Nome da Empresa", 71, 104, "alfa", obrigatorio=False),
    CampoLayout("Uso Reservado do Banco", 105, 110, "alfa", obrigatorio=False),
    CampoLayout("Data do Lançamento", 111, 118, "num"),
    CampoLayout("Valor do Lançamento", 119, 133, "num"),
    CampoLayout("Tipo do Lançamento (D/C)", 134, 134, "alfa"),
    CampoLayout("Categoria do Lançamento", 135, 137, "num", obrigatorio=False),
    CampoLayout("Código do Histórico no Banco", 138, 141, "alfa", obrigatorio=False),
    CampoLayout("Histórico do Lançamento", 142, 166, "alfa", obrigatorio=False),
    CampoLayout("Número do Documento / NSU", 167, 205, "alfa", obrigatorio=False),
    CampoLayout("Informação Complementar", 206, 240, "alfa", obrigatorio=False),
]

# Segmento T -- Retorno de Cobrança (Status e Dados Básicos do Título)
SEGMENTO_T: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="T"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 15, 15, "alfa", obrigatorio=False),
    CampoLayout("Código de Movimento Retorno", 16, 17, "num"),
    CampoLayout("Agência Mantenedora da Conta", 18, 22, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Agência", 23, 23, "alfa", obrigatorio=False),
    CampoLayout("Número da Conta Corrente", 24, 35, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Conta", 36, 36, "alfa", obrigatorio=False),
    CampoLayout("Dígito Verificador da Ag/Conta", 37, 37, "alfa", obrigatorio=False),
    CampoLayout("Nosso Número (identificação no banco)", 38, 57, "alfa"),
    CampoLayout("Código da Carteira", 58, 58, "num"),
    CampoLayout("Número do Documento de Cobrança", 59, 73, "alfa", obrigatorio=False),
    CampoLayout("Data de Vencimento do Título", 74, 81, "num"),
    CampoLayout("Valor Nominal do Título", 82, 96, "num"),
    CampoLayout("Número do Banco Cobrador", 97, 99, "num", obrigatorio=False),
    CampoLayout("Agência Cobradora", 100, 104, "num", obrigatorio=False),
    CampoLayout("Dígito Verificador da Agência Cobradora", 105, 105, "alfa", obrigatorio=False),
    CampoLayout("Identificação do Título na Empresa", 106, 130, "alfa", obrigatorio=False),
    CampoLayout("Código da Moeda", 131, 132, "num", obrigatorio=False),
    CampoLayout("Tipo de Inscrição do Pagador", 133, 133, "num", obrigatorio=False),
    CampoLayout("Número de Inscrição do Pagador", 134, 148, "num", obrigatorio=False),
    CampoLayout("Nome do Pagador", 149, 188, "alfa", obrigatorio=False),
    CampoLayout("Número do Contrato / Conta Cobrança", 189, 198, "num", obrigatorio=False),
    CampoLayout("Valor da Tarifa / Custas", 199, 206, "num", obrigatorio=False),
    CampoLayout("Motivo da Ocorrência", 207, 221, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 222, 240, "alfa", obrigatorio=False),
]

# Segmento U -- Retorno de Cobrança (Valores Financeiros Pagos)
SEGMENTO_U: list[CampoLayout] = [
    CampoLayout("Código do Banco na Compensação", 1, 3, "num"),
    CampoLayout("Lote de Serviço", 4, 7, "num"),
    CampoLayout("Tipo de Registro", 8, 8, "num", valor_fixo="3"),
    CampoLayout("Número Sequencial do Registro no Lote", 9, 13, "num"),
    CampoLayout("Código de Segmento do Registro Detalhe", 14, 14, "alfa", valor_fixo="U"),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 15, 15, "alfa", obrigatorio=False),
    CampoLayout("Código de Movimento Retorno", 16, 17, "num"),
    CampoLayout("Juros / Multa / Encargos", 18, 32, "num", obrigatorio=False),
    CampoLayout("Valor do Desconto Concedido", 33, 47, "num", obrigatorio=False),
    CampoLayout("Valor do Abatimento Concedido", 48, 62, "num", obrigatorio=False),
    CampoLayout("Valor Principal Pago", 63, 77, "num", obrigatorio=False),
    CampoLayout("Valor Líquido Creditado", 78, 92, "num", obrigatorio=False),
    CampoLayout("Valor de Outras Despesas", 93, 107, "num", obrigatorio=False),
    CampoLayout("Valor de Outros Créditos", 108, 122, "num", obrigatorio=False),
    CampoLayout("Data da Ocorrência", 123, 130, "num"),
    CampoLayout("Data da Efetivação do Crédito", 131, 138, "num", obrigatorio=False),
    CampoLayout("Código da Ocorrência do Pagador", 139, 142, "alfa", obrigatorio=False),
    CampoLayout("Data da Ocorrência do Pagador", 143, 150, "num", obrigatorio=False),
    CampoLayout("Valor da Ocorrência do Pagador", 151, 165, "num", obrigatorio=False),
    CampoLayout("Complemento da Ocorrência", 166, 195, "alfa", obrigatorio=False),
    CampoLayout("Cód Banco Correspondente Compensação", 196, 198, "num", obrigatorio=False),
    CampoLayout("Nosso Número no Banco Correspondente", 199, 218, "alfa", obrigatorio=False),
    CampoLayout("Uso Exclusivo FEBRABAN/CNAB", 219, 240, "alfa", obrigatorio=False),
]
# Dicionário de despacho: código do segmento (posição 14) -> layout
SEGMENTOS: dict[str, list[CampoLayout]] = {
    "A": SEGMENTO_A,
    "B": SEGMENTO_B,
    "E": SEGMENTO_E,
    "J": SEGMENTO_J,
    "J52": SEGMENTO_J52,
    "N": SEGMENTO_N,
    "O": SEGMENTO_O,
    "P": SEGMENTO_P,
    "Q": SEGMENTO_Q,
    "R": SEGMENTO_R,
    "T": SEGMENTO_T,
    "U": SEGMENTO_U,
    "W": SEGMENTO_W,
    "Z": SEGMENTO_Z,
}