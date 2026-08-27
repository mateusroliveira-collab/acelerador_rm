"""
Validador estrutural do CNAB 240 -- confere, linha a linha, se o arquivo
bate com o layout padrão FEBRABAN (por enquanto: Header de Arquivo, Header
de Lote, Trailer de Lote, Trailer de Arquivo -- ver layout.py).

Retorna uma lista de ErroValidacao, cada um já apontando linha + posição +
campo + o que está errado -- pronto pra virar uma dica no RM.
"""

from ..erros import ErroValidacao, ResultadoValidacao
from .layout import (
    CampoLayout,
    HEADER_ARQUIVO,
    HEADER_LOTE,
    TRAILER_LOTE,
    TRAILER_ARQUIVO,
    TAMANHO_LINHA,
)


def _validar_campo(
    linha_num: int, texto_linha: str, campo: CampoLayout
) -> ErroValidacao | None:
    valor = texto_linha[campo.inicio - 1 : campo.fim]

    if campo.valor_fixo is not None and valor != campo.valor_fixo:
        return ErroValidacao(
            mensagem=(
                f'Campo "{campo.nome}" deveria ser "{campo.valor_fixo}", '
                f'mas veio "{valor}".'
            ),
            linha=linha_num,
            posicao_inicio=campo.inicio,
            posicao_fim=campo.fim,
            campo=campo.nome,
            valor_encontrado=valor,
            sugestao_rm=(
                f'Confira a geração do registro nessa posição -- valor '
                f'esperado fixo "{campo.valor_fixo}".'
            ),
            corrigivel_automaticamente=True,
            valor_corrigido=campo.valor_fixo,
        )

    if campo.obrigatorio and valor.strip() == "":
        return ErroValidacao(
            mensagem=f'Campo obrigatório "{campo.nome}" está em branco.',
            linha=linha_num,
            posicao_inicio=campo.inicio,
            posicao_fim=campo.fim,
            campo=campo.nome,
            valor_encontrado=valor,
            sugestao_rm="Verifique se esse dado está preenchido no cadastro de origem no RM.",
        )

    if campo.tipo == "num" and valor.strip() != "" and not valor.isdigit():
        return ErroValidacao(
            mensagem=f'Campo "{campo.nome}" deveria ser só números, mas veio "{valor}".',
            linha=linha_num,
            posicao_inicio=campo.inicio,
            posicao_fim=campo.fim,
            campo=campo.nome,
            valor_encontrado=valor,
            sugestao_rm="Verifique se há caractere inválido (letra, símbolo) nesse campo no cadastro de origem.",
        )

    return None


def _validar_registro(
    linha_num: int, texto_linha: str, layout: list[CampoLayout]
) -> list[ErroValidacao]:
    erros: list[ErroValidacao] = []

    if len(texto_linha) != TAMANHO_LINHA:
        erros.append(
            ErroValidacao(
                mensagem=(
                    f"Linha tem {len(texto_linha)} caracteres, "
                    f"deveria ter exatamente {TAMANHO_LINHA}."
                ),
                linha=linha_num,
                sugestao_rm="Arquivo pode estar truncado ou com quebra de linha errada -- confira a geração do arquivo.",
            )
        )
        return erros  # sem o tamanho certo, validar campo a campo não é confiável

    for campo in layout:
        erro = _validar_campo(linha_num, texto_linha, campo)
        if erro:
            erros.append(erro)

    return erros


def validar_cnab240(conteudo: str) -> ResultadoValidacao:
    """
    Valida a estrutura de um arquivo CNAB 240 (remessa ou retorno).

    Cobre hoje: Header de Arquivo, Header de Lote (parte fixa), Trailer de
    Lote, Trailer de Arquivo -- os registros iguais independente do banco.
    Registros de Segmento (detalhe) ainda não são validados campo a campo,
    só tem o tamanho da linha conferido.
    """
    linhas = conteudo.splitlines()
    erros: list[ErroValidacao] = []

    if not linhas:
        return ResultadoValidacao(
            valido=False, erros=[ErroValidacao(mensagem="Arquivo vazio.")]
        )

    # Header de Arquivo -- sempre a primeira linha
    erros += _validar_registro(1, linhas[0], HEADER_ARQUIVO)

    # Trailer de Arquivo -- sempre a última linha
    erros += _validar_registro(len(linhas), linhas[-1], TRAILER_ARQUIVO)

    # Linhas do meio: identifica pelo Tipo de Registro (posição 8) se é
    # header de lote ('1'), trailer de lote ('5'), ou segmento de detalhe
    # ('3' -- ainda não validado campo a campo).
    for i, texto_linha in enumerate(linhas[1:-1], start=2):
        if len(texto_linha) < 8:
            erros.append(
                ErroValidacao(
                    mensagem="Linha muito curta para identificar o tipo de registro.",
                    linha=i,
                )
            )
            continue

        tipo_registro = texto_linha[7]

        if tipo_registro == "1":
            erros += _validar_registro(i, texto_linha, HEADER_LOTE)
        elif tipo_registro == "5":
            erros += _validar_registro(i, texto_linha, TRAILER_LOTE)
        elif tipo_registro == "3":
            if len(texto_linha) != TAMANHO_LINHA:
                erros.append(
                    ErroValidacao(
                        mensagem=(
                            f"Linha tem {len(texto_linha)} caracteres, "
                            f"deveria ter {TAMANHO_LINHA}."
                        ),
                        linha=i,
                    )
                )
        else:
            erros.append(
                ErroValidacao(
                    mensagem=f'Tipo de registro desconhecido: "{tipo_registro}".',
                    linha=i,
                    posicao_inicio=8,
                    posicao_fim=8,
                    campo="Tipo de Registro",
                    valor_encontrado=tipo_registro,
                )
            )

    return ResultadoValidacao(valido=len(erros) == 0, erros=erros)
