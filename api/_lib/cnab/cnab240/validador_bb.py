"""
Validador do CNAB 240 especializado para o Banco do Brasil.
"""

from ..erros import ErroValidacao, ResultadoValidacao
from ..linhas import ler_linhas
from .validador import validar_cnab240
from ..bancos.bb import (
    CODIGO_REJEICAO_52_SIGNIFICADO_BB,
    movimento_eh_rejeicao_bb,
    significado_movimento_retorno_bb,
    significado_negativacao_bb,
)

_SUGESTAO_PADRAO = (
    "Verifique as parametrizações do Convênio/Carteira no menu Banco e "
    "Agências do RM e a tabela de motivos (campo 28.3T) do manual do BB."
)


def _motivos_segmento_t(texto_linha: str) -> list[str]:
    """Campo 28.3T (pos. 207-221): até 5 códigos de 2 posições; '00'/branco = sem motivo."""
    motivos = texto_linha[206:221]
    return [
        motivos[j:j + 2] for j in range(0, len(motivos), 2)
        if motivos[j:j + 2].strip() and motivos[j:j + 2] != "00"
    ]


def validar_cnab240_bb(conteudo: str) -> ResultadoValidacao:
    """Valida um arquivo CNAB 240 do Banco do Brasil (Remessa ou Retorno)."""
    resultado = validar_cnab240(conteudo)
    erros = list(resultado.erros)
    linhas = ler_linhas(conteudo)

    if not linhas:
        return resultado

    # Valida Código do Banco no Header de Arquivo (pos. 1-3)
    if len(linhas[0]) >= 3 and linhas[0][0:3] != "001":
        erros.append(
            ErroValidacao(
                mensagem='Código do Banco no Header deveria ser "001" (Banco do Brasil), mas veio "{}"'.format(linhas[0][0:3]),
                linha=1,
                posicao_inicio=1,
                posicao_fim=3,
                campo="Código do Banco",
                valor_encontrado=linhas[0][0:3],
                sugestao_rm="Acessar módulo Gestão Financeira > Movimentações Bancárias > Controle Bancário > Banco e Agências > Ajustar o código do banco para 001."
            )
        )

    for i, texto_linha in enumerate(linhas, start=1):
        if len(texto_linha) < 240:
            continue

        if texto_linha[7] != "3" or texto_linha[13] != "T":
            continue

        # --- REGRA DE RETORNO: Segmento T ---
        cod_movimento = texto_linha[15:17].strip()
        motivos = _motivos_segmento_t(texto_linha)

        # Negativação (85/86): o motivo usa tabela própria (Anexo 01) --
        # só é problema quando o banco RECUSOU a negativação/exclusão.
        if cod_movimento in ("85", "86"):
            for cod_m in motivos:
                significado = significado_negativacao_bb(cod_movimento, cod_m)
                if significado and "recusad" in significado.lower():
                    erros.append(
                        ErroValidacao(
                            mensagem=f"Negativação BB 240 (movimento {cod_movimento}): ({cod_m}) {significado}",
                            linha=i,
                            posicao_inicio=207,
                            posicao_fim=221,
                            campo="Motivo da Ocorrência",
                            valor_encontrado=cod_m,
                            sugestao_rm="Confira o cadastro do pagador/título no RM antes de solicitar a negativação novamente.",
                        )
                    )
            continue

        # Nos demais movimentos não-rejeição (ex: 06 = liquidação), o
        # campo de motivo é informativo -- não é erro.
        if not movimento_eh_rejeicao_bb(cod_movimento):
            continue

        descricao_mov = significado_movimento_retorno_bb(cod_movimento) or "rejeição"
        for cod_m in motivos or ["(sem código de motivo)"]:
            if cod_m == "52":
                # O manual do BB manda desconsiderar o significado FEBRABAN do 52.
                detalhe = CODIGO_REJEICAO_52_SIGNIFICADO_BB
            else:
                detalhe = "consulte a tabela de motivos de rejeição (campo 28.3T) do manual do BB"
            erros.append(
                ErroValidacao(
                    mensagem=f"Retorno BB 240 -- {descricao_mov} (movimento {cod_movimento}): motivo {cod_m} -- {detalhe}.",
                    linha=i,
                    posicao_inicio=207,
                    posicao_fim=221,
                    campo="Motivo da Ocorrência",
                    valor_encontrado=cod_m,
                    sugestao_rm=_SUGESTAO_PADRAO,
                )
            )

    return ResultadoValidacao(valido=len(erros) == 0, erros=erros)
