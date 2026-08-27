"""
Layout do CNAB 400 -- diferente do 240, aqui NÃO existe um documento único
da FEBRABAN que padronize os campos entre bancos. Cada banco publica seu
próprio manual, e a área de detalhe (Nosso Número, códigos de ocorrência,
etc.) varia de posição conforme o banco.

O que É universal (confirmado comparando manuais de vários bancos --
Banco do Brasil, Unicred, BMP, entre outros) é só:
  - Toda linha tem exatamente 400 caracteres.
  - Posição 1 identifica o tipo de registro: '0' = header, '1' = detalhe
    (transação), '9' = trailer. Isso se repete em praticamente todo banco.

Os campos de detalhe (posições 2 em diante do registro tipo '1') ficam
para cada banco definir separadamente -- ver bancos_400/ -- igual já
fazemos com a base de erros conhecidos.
"""

from dataclasses import dataclass

TAMANHO_LINHA = 400

TIPO_HEADER = "0"
TIPO_DETALHE = "1"
TIPO_TRAILER = "9"


@dataclass
class CampoLayout400:
    nome: str
    inicio: int
    fim: int
    tipo: str  # "num" ou "alfa"
    obrigatorio: bool = True
    valor_fixo: str | None = None

    @property
    def tamanho(self) -> int:
        return self.fim - self.inicio + 1


# Único campo que vale pra qualquer banco: o identificador do tipo de
# registro, sempre na posição 1.
CAMPO_TIPO_REGISTRO = CampoLayout400("Código do Registro", 1, 1, "num")
