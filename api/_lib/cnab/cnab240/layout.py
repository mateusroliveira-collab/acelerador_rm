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
