"""
Validador de regras de negócio de um boleto pra registro online.

Duas categorias de regra aqui, que valem a pena distinguir:

1. REGRAS UNIVERSAIS -- valem pra qualquer banco, não dependem de manual
   nenhum: matemática (desconto não pode ser maior que o valor), lógica
   de data (vencimento não pode ser antes da emissão), e LEI (limite de
   multa de 2%, Código de Defesa do Consumidor art. 52 §1º).
2. REGRAS ESPECÍFICAS DE BANCO -- ex: valor mínimo aceito, schema exato
   de campo -- essas ainda NÃO estão aqui, porque variam de banco pra
   banco e dependem da documentação da API de cada um. Só o BB e a Caixa
   estão no escopo do projeto; nenhum dos dois foi documentado ainda
   nesse validador -- ver CONTEXTO_PROJETO.md.
"""

from dataclasses import dataclass, field
from datetime import date

from .documentos import validar_documento

# Limite legal de multa por atraso -- Código de Defesa do Consumidor,
# art. 52 §1º. Isso é LEI, não regra de banco -- vale pra qualquer um.
MULTA_MAXIMA_PERCENTUAL = 2.0


@dataclass
class ErroBoleto:
    campo: str
    mensagem: str
    valor_encontrado: str | None = None
    sugestao_rm: str | None = None


@dataclass
class ResultadoValidacaoBoleto:
    valido: bool
    erros: list[ErroBoleto] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "valido": self.valido,
            "erros": [
                {
                    "campo": e.campo,
                    "mensagem": e.mensagem,
                    "valor_encontrado": e.valor_encontrado,
                    "sugestao_rm": e.sugestao_rm,
                }
                for e in self.erros
            ],
            "avisos": self.avisos,
        }


def _parse_data(valor) -> date | None:
    """Aceita string 'AAAA-MM-DD' ou objeto date já pronto."""
    if valor is None:
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        return None


def validar_boleto(dados: dict) -> ResultadoValidacaoBoleto:
    """
    Valida as regras de negócio universais de um boleto. Espera um dict
    com formato aproximado:

    {
      "pagador": {"documento": "...", "nome": "...", "endereco": {
          "cep": "...", "logradouro": "...", "bairro": "...",
          "cidade": "...", "uf": "..."
      }},
      "titulo": {"valor": 150.00, "data_emissao": "2026-01-01",
                 "data_vencimento": "2026-01-15"},
      "desconto": {"valor": 10.00, "data_limite": "2026-01-10"},  # opcional
      "multa": {"percentual": 2.0}  # opcional
    }

    Chaves ausentes são toleradas -- só valida o que está presente
    (schema exato de campo obrigatório varia por banco, ainda não
    documentado aqui).
    """
    erros: list[ErroBoleto] = []

    pagador = dados.get("pagador", {}) or {}
    titulo = dados.get("titulo", {}) or {}
    desconto = dados.get("desconto") or {}
    multa = dados.get("multa") or {}

    # --- Documento do pagador (CPF/CNPJ) ---
    documento = pagador.get("documento")
    if documento:
        valido, tipo = validar_documento(documento)
        if not valido:
            erros.append(
                ErroBoleto(
                    campo="pagador.documento",
                    mensagem=f"Documento do pagador não é um {tipo} válido (dígito verificador não confere).",
                    valor_encontrado=documento,
                    sugestao_rm="Confira o CPF/CNPJ cadastrado do pagador no RM -- pode ter erro de digitação.",
                )
            )

    # --- Datas ---
    data_emissao = _parse_data(titulo.get("data_emissao"))
    data_vencimento = _parse_data(titulo.get("data_vencimento"))
    if data_emissao and data_vencimento and data_vencimento < data_emissao:
        erros.append(
            ErroBoleto(
                campo="titulo.data_vencimento",
                mensagem="Data de vencimento não pode ser anterior à data de emissão.",
                valor_encontrado=str(data_vencimento),
                sugestao_rm="Confira as datas cadastradas no título -- vencimento deve ser igual ou posterior à emissão.",
            )
        )

    # --- Valor do título ---
    valor_titulo = titulo.get("valor")
    if valor_titulo is not None and valor_titulo <= 0:
        erros.append(
            ErroBoleto(
                campo="titulo.valor",
                mensagem="Valor do título deve ser maior que zero.",
                valor_encontrado=str(valor_titulo),
            )
        )

    # --- Desconto ---
    valor_desconto = desconto.get("valor")
    if valor_desconto is not None:
        if valor_titulo is not None and valor_desconto >= valor_titulo:
            erros.append(
                ErroBoleto(
                    campo="desconto.valor",
                    mensagem="Valor do desconto não pode ser maior ou igual ao valor do título.",
                    valor_encontrado=str(valor_desconto),
                )
            )
        data_limite_desconto = _parse_data(desconto.get("data_limite"))
        if (
            data_limite_desconto
            and data_vencimento
            and data_limite_desconto > data_vencimento
        ):
            erros.append(
                ErroBoleto(
                    campo="desconto.data_limite",
                    mensagem="Data limite do desconto deve ser igual ou anterior à data de vencimento.",
                    valor_encontrado=str(data_limite_desconto),
                )
            )

    # --- Multa (limite legal, não é regra de banco -- é lei) ---
    percentual_multa = multa.get("percentual")
    if percentual_multa is not None and percentual_multa > MULTA_MAXIMA_PERCENTUAL:
        erros.append(
            ErroBoleto(
                campo="multa.percentual",
                mensagem=(
                    f"Percentual de multa ({percentual_multa}%) excede o limite "
                    f"legal de {MULTA_MAXIMA_PERCENTUAL}% (Código de Defesa do "
                    "Consumidor, art. 52 §1º)."
                ),
                valor_encontrado=str(percentual_multa),
                sugestao_rm="Ajuste a configuração de multa no cadastro do título/contrato no RM.",
            )
        )

    # --- Endereço (exigido pra registro na CIP -- Câmara Interbancária de Pagamentos) ---
    endereco = pagador.get("endereco", {}) or {}
    campos_endereco_obrigatorios = ["cep", "logradouro", "bairro", "cidade", "uf"]
    for campo in campos_endereco_obrigatorios:
        if not endereco.get(campo):
            erros.append(
                ErroBoleto(
                    campo=f"pagador.endereco.{campo}",
                    mensagem=f"Campo de endereço '{campo}' está ausente -- exigido pra registro na CIP.",
                    sugestao_rm="Complete o cadastro de endereço do pagador no RM antes de enviar pro registro online.",
                )
            )

    return ResultadoValidacaoBoleto(valido=len(erros) == 0, erros=erros)
