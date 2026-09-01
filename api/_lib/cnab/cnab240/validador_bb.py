"""
Validador do CNAB 240 especializado para o Banco do Brasil.
"""

from ..erros import ErroValidacao, ResultadoValidacao
from .validador import validar_cnab240
from ..bancos.bb import (
    buscar_erro_bb, 
    CODIGOS_OCORRENCIA_PAGAMENTO_BB, 
    CODIGOS_MOVIMENTO_RETORNO_BB_SAO_REJEICAO
)


def validar_cnab240_bb(conteudo: str) -> ResultadoValidacao:
    """Valida um arquivo CNAB 240 do Banco do Brasil (Remessa ou Retorno)."""
    resultado = validar_cnab240(conteudo)
    erros = list(resultado.erros)
    linhas = conteudo.splitlines()

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

        if texto_linha[7] == "3":
            codigo_segmento = texto_linha[13]

            # --- REGRA DE RETORNO: Segmento T ---
            if codigo_segmento == "T":
                cod_movimento = texto_linha[15:17].strip()
                motivos = texto_linha[206:221].strip()

                if cod_movimento in CODIGOS_MOVIMENTO_RETORNO_BB_SAO_REJEICAO or motivos:
                    codigos_motivo = [motivos[j:j+2] for j in range(0, len(motivos), 2) if motivos[j:j+2].strip()]
                    
                    for cod_m in codigos_motivo:
                        if cod_m and cod_m != "00":
                            msg_banco = CODIGOS_OCORRENCIA_PAGAMENTO_BB.get(cod_m)
                            info_conhecida = buscar_erro_bb(cod_m)
                            
                            sugestao = (
                                info_conhecida["sugestao_rm"] if info_conhecida 
                                else "Verifique as parametrizações do Convênio/Carteira no menu Banco e Agências do RM."
                            )
                            
                            erros.append(
                                ErroValidacao(
                                    mensagem=f'Ocorrência de Retorno BB 240: ({cod_m}) {msg_banco or "Ocorrência Não Catalogada"}',
                                    linha=i,
                                    posicao_inicio=207,
                                    posicao_fim=221,
                                    campo="Motivo da Ocorrência",
                                    valor_encontrado=cod_m,
                                    sugestao_rm=sugestao
                                )
                            )

    return ResultadoValidacao(valido=len(erros) == 0, erros=erros)