"""
Validador estrutural do CNAB 400 -- nível genérico, válido pra qualquer
banco: confere tamanho de linha (400) e a sequência básica de registros
(primeira linha é header '0', última é trailer '9', meio são detalhe '1').

Validação campo a campo do registro de detalhe (Nosso Número, código de
ocorrência etc.) fica pro módulo específico de cada banco, dentro de
bancos_400/ -- ainda não implementado, ver README/CONTEXTO_PROJETO.md.
"""

from ..erros import ErroValidacao, ResultadoValidacao
from .layout import TAMANHO_LINHA, TIPO_HEADER, TIPO_DETALHE, TIPO_TRAILER


def validar_cnab400(conteudo: str) -> ResultadoValidacao:
    """
    Valida a estrutura genérica de um arquivo CNAB 400 (remessa ou
    retorno), independente do banco.
    """
    linhas = conteudo.splitlines()
    erros: list[ErroValidacao] = []

    if not linhas:
        return ResultadoValidacao(
            valido=False, erros=[ErroValidacao(mensagem="Arquivo vazio.")]
        )

    for i, texto_linha in enumerate(linhas, start=1):
        if len(texto_linha) != TAMANHO_LINHA:
            erros.append(
                ErroValidacao(
                    mensagem=(
                        f"Linha tem {len(texto_linha)} caracteres, "
                        f"deveria ter exatamente {TAMANHO_LINHA}."
                    ),
                    linha=i,
                    sugestao_rm="Arquivo pode estar truncado ou com quebra de linha errada -- confira a geração do arquivo.",
                )
            )
            continue

        tipo_registro = texto_linha[0]
        eh_primeira = i == 1
        eh_ultima = i == len(linhas)

        if eh_primeira and tipo_registro != TIPO_HEADER:
            erros.append(
                ErroValidacao(
                    mensagem=f'Primeira linha deveria começar com "{TIPO_HEADER}" (header), mas veio "{tipo_registro}".',
                    linha=i,
                    posicao_inicio=1,
                    posicao_fim=1,
                    campo="Código do Registro",
                    valor_encontrado=tipo_registro,
                    corrigivel_automaticamente=True,
                    valor_corrigido=TIPO_HEADER,
                    sugestao_rm="O arquivo de remessa sempre começa com um registro header.",
                )
            )
        elif eh_ultima and tipo_registro != TIPO_TRAILER:
            erros.append(
                ErroValidacao(
                    mensagem=f'Última linha deveria começar com "{TIPO_TRAILER}" (trailer), mas veio "{tipo_registro}".',
                    linha=i,
                    posicao_inicio=1,
                    posicao_fim=1,
                    campo="Código do Registro",
                    valor_encontrado=tipo_registro,
                    corrigivel_automaticamente=True,
                    valor_corrigido=TIPO_TRAILER,
                    sugestao_rm="O arquivo de remessa sempre termina com um registro trailer.",
                )
            )
        elif not eh_primeira and not eh_ultima and tipo_registro not in (
            TIPO_DETALHE,
        ):
            # Alguns bancos usam tipos extras opcionais (2, 3, 5, 7) --
            # por enquanto só sinaliza, sem tratar como erro definitivo,
            # já que isso é legítimo em vários layouts bancários.
            erros.append(
                ErroValidacao(
                    mensagem=(
                        f'Linha do meio com tipo de registro "{tipo_registro}" '
                        '(esperado "1" na maioria dos casos -- alguns bancos usam '
                        "tipos extras opcionais, confira o manual do banco específico)."
                    ),
                    linha=i,
                    posicao_inicio=1,
                    posicao_fim=1,
                    campo="Código do Registro",
                    valor_encontrado=tipo_registro,
                )
            )

    return ResultadoValidacao(valido=len(erros) == 0, erros=erros)