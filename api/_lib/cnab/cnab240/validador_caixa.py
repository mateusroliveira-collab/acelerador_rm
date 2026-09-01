"""
Validador do CNAB 240 especializado para a Caixa Econômica Federal.
Valida regras de negócio da Remessa (Segmento P) e lê códigos de rejeição do Retorno (Segmento T).
"""

from ..erros import ErroValidacao, ResultadoValidacao
from .validador import validar_cnab240
from ..bancos.caixa import buscar_erro


def validar_cnab240_caixa(conteudo: str) -> ResultadoValidacao:
    """Valida um arquivo CNAB 240 da Caixa Econômica Federal (Remessa ou Retorno)."""
    # 1. Executa a validação estrutural genérica da FEBRABAN
    resultado = validar_cnab240(conteudo)
    erros = list(resultado.erros)
    linhas = conteudo.splitlines()

    if not linhas:
        return resultado

    # 2. Valida o Código do Banco no Header de Arquivo (pos. 1-3)
    if len(linhas[0]) >= 3 and linhas[0][0:3] != "104":
        erros.append(
            ErroValidacao(
                mensagem='Código do Banco no Header deveria ser "104" (Caixa), mas veio "{}"'.format(linhas[0][0:3]),
                linha=1,
                posicao_inicio=1,
                posicao_fim=3,
                campo="Código do Banco",
                valor_encontrado=linhas[0][0:3],
                sugestao_rm="Acessar módulo Gestão Financeira > Movimentações Bancárias > Controle Bancário > Banco e Agências > Ajustar o código do banco para 104."
            )
        )

    # 3. Análise detalhada segmento por segmento
    for i, texto_linha in enumerate(linhas, start=1):
        if len(texto_linha) < 240:
            continue

        # Verifica se é um registro de Detalhe (Tipo '3')
        if texto_linha[7] == "3":
            codigo_segmento = texto_linha[13]  # Posição 14

            # --- REGRA DE REMESSA: Segmento P (Cobrança) ---
            if codigo_segmento == "P":
                nosso_numero = texto_linha[37:57].strip()  # Posição 38 a 57
                if nosso_numero and len(nosso_numero) >= 17 and not nosso_numero.startswith("14"):
                    dica_bento = buscar_erro("24", tabela="critica_remessa_400")
                    sugestao = dica_bento["sugestao_rm"] if dica_bento else "Ajustar o Nosso Número no RM para iniciar com '14'."

                    erros.append(
                        ErroValidacao(
                            mensagem="Nosso Número na Caixa deve iniciar com a modalidade/prefixo '14' para Cobrança Registrada.",
                            linha=i,
                            posicao_inicio=38,
                            posicao_fim=57,
                            campo="Nosso Número",
                            valor_encontrado=nosso_numero,
                            sugestao_rm=sugestao
                        )
                    )

            # --- REGRA DE RETORNO: Segmento T (Status / Rejeição) ---
            elif codigo_segmento == "T":
                cod_movimento = texto_linha[15:17].strip()  # Posição 16 a 17 (Ex: 03 = Rejeição)
                motivos = texto_linha[206:221].strip()       # Posição 207 a 221 (Até 5 códigos de 2 dígitos)

                if cod_movimento == "03" or motivos:
                    # Decompõe os pares de códigos de motivo
                    codigos_motivo = [motivos[j:j+2] for j in range(0, len(motivos), 2) if motivos[j:j+2].strip()]
                    
                    for cod_m in codigos_motivo:
                        if cod_m and cod_m != "00":
                            info = buscar_erro(cod_m, tabela="entrada_240") or buscar_erro(cod_m, tabela="retorno_400")
                            if info:
                                erros.append(
                                    ErroValidacao(
                                        mensagem=f'Título Rejeitado no Retorno Caixa 240: ({cod_m}) {info["mensagem_banco"]}',
                                        linha=i,
                                        posicao_inicio=207,
                                        posicao_fim=221,
                                        campo="Motivo da Ocorrência",
                                        valor_encontrado=cod_m,
                                        sugestao_rm=f'{info["causa_provavel"]} {info["sugestao_rm"]}'
                                    )
                                )

    return ResultadoValidacao(valido=len(erros) == 0, erros=erros)