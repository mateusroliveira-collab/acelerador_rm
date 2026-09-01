"""
Schemas Pydantic para validação estrutural de JSONs de Registro Online de Boletos.
Garante que o TOTVS RM gerou todas as chaves obrigatórias exigidas pelas APIs dos bancos.
"""

from pydantic import BaseModel, Field
from typing import Optional

# ==========================================
# CAIXA ECONÔMICA FEDERAL
# ==========================================
class EnderecoCaixa(BaseModel):
    logradouro: str = Field(..., max_length=40, description="Rua, avenida, etc.")
    bairro: str = Field(..., max_length=15)
    cidade: str = Field(..., max_length=15)
    uf: str = Field(..., max_length=2)
    cep: str = Field(..., max_length=8, description="CEP sem máscara (apenas números)")

class PagadorCaixa(BaseModel):
    cpfCnpj: str = Field(..., max_length=14, description="CPF ou CNPJ apenas com números")
    nome: str = Field(..., max_length=40)
    endereco: EnderecoCaixa

class TituloCaixa(BaseModel):
    nossoNumero: str = Field(..., max_length=17, description="Nosso Número gerado pelo RM (sem DV)")
    numeroDocumento: str = Field(..., max_length=11, description="Seu Número / Identificação no RM")
    dataVencimento: str = Field(..., description="Formato exigido: AAAA-MM-DD")
    valor: float = Field(..., gt=0, description="Valor nominal do título (maior que zero)")
    tipoEspecie: int = Field(..., description="Código da espécie do título (ex: 2 para Duplicata Mercantil)")
    flagAceite: str = Field(..., max_length=1, description="S para Sim, N para Não")
    pagador: PagadorCaixa

class SchemaBoletoCaixa(BaseModel):
    """Gabarito estrutural completo para o POST de Registro na Caixa."""
    codigoBeneficiario: int = Field(..., description="Código do convênio/cedente")
    titulo: TituloCaixa


# ==========================================
# BANCO DO BRASIL
# ==========================================
class PagadorBB(BaseModel):
    tipoInscricao: int = Field(..., description="1 para CPF, 2 para CNPJ")
    numeroInscricao: int = Field(..., description="Número do CPF/CNPJ (numérico)")
    nome: str = Field(..., max_length=30)
    endereco: str = Field(..., max_length=30)
    cep: int = Field(...)
    cidade: str = Field(..., max_length=15)
    bairro: str = Field(..., max_length=15)
    uf: str = Field(..., max_length=2)
    telefone: Optional[str] = Field(default=None, description="Opcional")

class SchemaBoletoBB(BaseModel):
    """Gabarito estrutural completo para o POST de Registro no Banco do Brasil."""
    numeroConvenio: int = Field(..., description="Convênio de cobrança ativo no BB")
    numeroCarteira: int = Field(...)
    numeroVariacaoCarteira: int = Field(...)
    codigoAceite: str = Field(..., max_length=1, description="A para Aceite, N para Não Aceite")
    tipoTitulo: int = Field(...)
    dataVencimento: str = Field(..., description="Formato exigido pelo BB: DD.MM.AAAA")
    valorOriginal: float = Field(..., gt=0)
    numeroTituloCliente: str = Field(..., description="Nosso Número completo (Convênio + Sequencial)")
    pagador: PagadorBB