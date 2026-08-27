"""
Modelo comum de erro de validação, usado tanto pelo validador de CNAB
(arquivo de remessa/retorno) quanto pelo validador de registro online (JSON).

A ideia: não importa se o erro veio de uma linha de um arquivo de texto ou
de um campo de um JSON -- ele vira sempre o mesmo formato, já pronto pra
virar uma "dica" no sistema RM.
"""

from dataclasses import dataclass, field


@dataclass
class ErroValidacao:
    """Um erro encontrado, já pronto pra virar uma dica pro analista no RM."""

    mensagem: str
    linha: int | None = None  # número da linha no arquivo (None p/ JSON)
    posicao_inicio: int | None = None  # posição inicial do campo com problema
    posicao_fim: int | None = None
    campo: str | None = None  # nome do campo (ex: "Código do Banco")
    valor_encontrado: str | None = None
    sugestao_rm: str | None = None  # onde/o que corrigir no sistema RM
    corrigivel_automaticamente: bool = False
    valor_corrigido: str | None = None  # só preenchido quando é um valor fixo/constante conhecido

    def to_dict(self) -> dict:
        return {
            "mensagem": self.mensagem,
            "linha": self.linha,
            "posicao_inicio": self.posicao_inicio,
            "posicao_fim": self.posicao_fim,
            "campo": self.campo,
            "valor_encontrado": self.valor_encontrado,
            "sugestao_rm": self.sugestao_rm,
            "corrigivel_automaticamente": self.corrigivel_automaticamente,
            "valor_corrigido": self.valor_corrigido,
        }


@dataclass
class ResultadoValidacao:
    """Resultado completo de uma validação -- arquivo inteiro ou registro online."""

    valido: bool
    erros: list[ErroValidacao] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "valido": self.valido,
            "erros": [e.to_dict() for e in self.erros],
        }
