"""
Validador do CNAB 400 específico do Banco do Brasil (Cobrança).
Detecta sozinho se o arquivo é remessa ou retorno (olhando a posição 2 do header:
'1' = remessa, '2' = retorno) e valida cada registro contra o layout correto.
"""

from ..erros import ErroValidacao, ResultadoValidacao
from .layout import TAMANHO_LINHA, CampoLayout400
from .bancos import bb as layout

def _validar_campo(linha_num: int, texto_linha: str, campo: CampoLayout400):
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

def _validar_registro(linha_num: int, texto_linha: str, layout_campos):
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
        return erros

    for campo in layout_campos:
        erro = _validar_campo(linha_num, texto_linha, campo)
        if erro:
            erros.append(erro)

    return erros

def validar_cnab400_bb(conteudo: str) -> ResultadoValidacao:
    """
    Valida um arquivo CNAB 400 de Cobrança do Banco do Brasil (remessa ou retorno).
    """
    linhas = conteudo.splitlines()
    erros: list[ErroValidacao] = []

    if not linhas:
        return ResultadoValidacao(
            valido=False, erros=[ErroValidacao(mensagem="Arquivo vazio.")]
        )

    if len(linhas[0]) < 2:
        return ResultadoValidacao(
            valido=False,
            erros=[
                ErroValidacao(
                    mensagem="Primeira linha muito curta para identificar remessa/retorno.",
                    linha=1,
                )
            ],
        )

    codigo_tipo = linhas[0][1]  # posição 2 do header

    if codigo_tipo == "1":
        header_layout = layout.HEADER_REMESSA
        detalhe_layout = layout.DETALHE_REMESSA
        trailer_layout = layout.TRAILER_REMESSA
    elif codigo_tipo == "2":
        header_layout = layout.HEADER_RETORNO
        detalhe_layout = layout.DETALHE_RETORNO
        trailer_layout = layout.TRAILER_RETORNO
    else:
        return ResultadoValidacao(
            valido=False,
            erros=[
                ErroValidacao(
                    mensagem=(
                        f'Posição 2 do header deveria ser "1" (remessa) ou '
                        f'"2" (retorno), mas veio "{codigo_tipo}".'
                    ),
                    linha=1,
                    posicao_inicio=2,
                    posicao_fim=2,
                    campo="Tipo de Operação",
                    valor_encontrado=codigo_tipo,
                )
            ],
        )

    # Valida Header
    erros += _validar_registro(1, linhas[0], header_layout)
    
    # Valida Trailer
    erros += _validar_registro(len(linhas), linhas[-1], trailer_layout)

    # Valida Detalhe
    for i, texto_linha in enumerate(linhas[1:-1], start=2):
        if len(texto_linha) < 1:
            erros.append(ErroValidacao(mensagem="Linha vazia inesperada.", linha=i))
            continue

        tipo_registro = texto_linha[0]
        
        # Detalhe do BB é 7 (diferente da Caixa que é 1)
        if tipo_registro == "7":
            erros += _validar_registro(i, texto_linha, detalhe_layout)
        elif tipo_registro == "5":
            # Registro Opcional de multas/e-mail -- só checamos tamanho por enquanto
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
                    mensagem=f'Tipo de registro desconhecido: "{tipo_registro}". No BB esperado é 7 ou 5.',
                    linha=i,
                    posicao_inicio=1,
                    posicao_fim=1,
                    campo="Código do Registro",
                    valor_encontrado=tipo_registro,
                )
            )

    return ResultadoValidacao(valido=len(erros) == 0, erros=erros)