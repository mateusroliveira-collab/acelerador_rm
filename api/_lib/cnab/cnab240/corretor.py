"""
Corretor automático do CNAB 240 -- escopo deliberadamente estreito: só
corrige campos cujo valor é uma CONSTANTE fixa definida pelo padrão
FEBRABAN (ex: "Tipo de Registro" tem que ser exatamente "9" no trailer,
"Lote de Serviço" tem que ser "9999" no trailer de arquivo).

NÃO tenta corrigir dado de negócio (conta, valor, data, nosso número,
etc.) -- esses erros continuam só sendo apontados, nunca "adivinhados",
porque a ferramenta não tem como saber qual é o valor certo sem acesso ao
dado de origem no RM. Corrigir esse tipo de campo às cegas seria mais
perigoso do que deixar o erro visível pro analista resolver.

Todo campo corrigido fica registrado (linha, posição, valor antigo, valor
novo) -- nunca uma correção "silenciosa".
"""

from dataclasses import dataclass, field

from ..erros import ErroValidacao
from ..linhas import detectar_quebra_de_linha, ler_linhas
from .validador import validar_cnab240


@dataclass
class Correcao:
    linha: int
    posicao_inicio: int
    posicao_fim: int
    campo: str
    valor_antigo: str
    valor_novo: str

    def to_dict(self) -> dict:
        return {
            "linha": self.linha,
            "posicao_inicio": self.posicao_inicio,
            "posicao_fim": self.posicao_fim,
            "campo": self.campo,
            "valor_antigo": self.valor_antigo,
            "valor_novo": self.valor_novo,
        }


@dataclass
class ResultadoCorrecao:
    conteudo_corrigido: str
    correcoes_aplicadas: list[Correcao] = field(default_factory=list)
    erros_restantes: list[ErroValidacao] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "conteudo_corrigido": self.conteudo_corrigido,
            "correcoes_aplicadas": [c.to_dict() for c in self.correcoes_aplicadas],
            "erros_restantes": [e.to_dict() for e in self.erros_restantes],
            "total_corrigido": len(self.correcoes_aplicadas),
            "total_pendente": len(self.erros_restantes),
        }


def corrigir_cnab240(conteudo: str) -> ResultadoCorrecao:
    """
    Valida o arquivo e aplica só as correções seguras (valor fixo/constante).
    Tudo que não for corrigível automaticamente volta em erros_restantes,
    exatamente como a validação normal apontaria.
    """
    resultado = validar_cnab240(conteudo)
    linhas = ler_linhas(conteudo)
    quebra = detectar_quebra_de_linha(conteudo)

    correcoes: list[Correcao] = []
    erros_restantes: list[ErroValidacao] = []

    # Agrupa os erros corrigíveis por linha, pra editar cada linha uma vez só
    corrigiveis_por_linha: dict[int, list[ErroValidacao]] = {}
    for erro in resultado.erros:
        if erro.corrigivel_automaticamente and erro.linha is not None:
            corrigiveis_por_linha.setdefault(erro.linha, []).append(erro)
        else:
            erros_restantes.append(erro)

    for num_linha, erros_da_linha in corrigiveis_por_linha.items():
        caracteres = list(linhas[num_linha - 1])

        for erro in erros_da_linha:
            largura = erro.posicao_fim - erro.posicao_inicio + 1
            valor_antigo = "".join(
                caracteres[erro.posicao_inicio - 1 : erro.posicao_fim]
            )
            valor_novo = erro.valor_corrigido.ljust(largura)
            caracteres[erro.posicao_inicio - 1 : erro.posicao_fim] = list(valor_novo)

            correcoes.append(
                Correcao(
                    linha=num_linha,
                    posicao_inicio=erro.posicao_inicio,
                    posicao_fim=erro.posicao_fim,
                    campo=erro.campo,
                    valor_antigo=valor_antigo,
                    valor_novo=erro.valor_corrigido,
                )
            )

        linhas[num_linha - 1] = "".join(caracteres)

    # Preserva a quebra de linha original (banco costuma rejeitar arquivo
    # CNAB que veio em CRLF e voltou só com LF) e a quebra final.
    conteudo_corrigido = quebra.join(linhas)
    if linhas and conteudo.endswith(("\n", "\r")):
        conteudo_corrigido += quebra

    return ResultadoCorrecao(
        conteudo_corrigido=conteudo_corrigido,
        correcoes_aplicadas=correcoes,
        erros_restantes=erros_restantes,
    )
