"""
Validador do CNAB 240 especializado para a Caixa Econômica Federal.
Valida regras de negócio da Remessa (Segmento P) e lê códigos de rejeição do Retorno (Segmento T).
"""

from ..erros import ErroValidacao, ResultadoValidacao
from ..linhas import ler_linhas
from .validador import validar_cnab240
from ..bancos.caixa import buscar_erro, dica_completa, sugestao_confirmada

# Códigos de movimento retorno (pos. 16-17 do Segmento T) que indicam
# REJEIÇÃO pelo padrão FEBRABAN: 03 = entrada rejeitada, 26 = instrução
# rejeitada, 30 = alteração de dados rejeitada. Nos demais movimentos
# (ex: 06 = liquidação), o campo de motivo traz informação complementar
# (canal de pagamento etc.), não erro -- não pode virar "título rejeitado".
_MOVIMENTOS_REJEICAO = {"03", "26", "30"}

_SUGESTAO_PADRAO_REJEICAO = (
    "Confira o cadastro do título/convênio no RM (Gestão Financeira > "
    "Movimentações Bancárias > Controle Bancário) e o manual da Caixa para esse código."
)


def validar_cnab240_caixa(conteudo: str) -> ResultadoValidacao:
    """Valida um arquivo CNAB 240 da Caixa Econômica Federal (Remessa ou Retorno)."""
    # 1. Executa a validação estrutural genérica da FEBRABAN
    resultado = validar_cnab240(conteudo)
    erros = list(resultado.erros)
    linhas = ler_linhas(conteudo)

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
                    sugestao = sugestao_confirmada(dica_bento) or "Ajustar o Nosso Número no RM para iniciar com '14'."

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
                if cod_movimento not in _MOVIMENTOS_REJEICAO:
                    continue

                motivos = texto_linha[206:221]  # Posição 207 a 221 (até 5 códigos de 2 posições)
                codigos_motivo = [
                    motivos[j:j + 2] for j in range(0, len(motivos), 2)
                    if motivos[j:j + 2].strip() and motivos[j:j + 2] != "00"
                ]
                if not codigos_motivo:
                    codigos_motivo = ["(sem código de motivo)"]

                for cod_m in codigos_motivo:
                    info = buscar_erro(cod_m, tabela="entrada_240") or buscar_erro(cod_m, tabela="retorno_400")
                    if info:
                        mensagem = f'Título Rejeitado no Retorno Caixa 240: ({cod_m}) {info["mensagem_banco"]}'
                        sugestao = dica_completa(info, _SUGESTAO_PADRAO_REJEICAO)
                    else:
                        mensagem = (
                            f"Título Rejeitado no Retorno Caixa 240 (movimento {cod_movimento}): "
                            f"motivo {cod_m} ainda não catalogado nesta ferramenta."
                        )
                        sugestao = _SUGESTAO_PADRAO_REJEICAO
                    erros.append(
                        ErroValidacao(
                            mensagem=mensagem,
                            linha=i,
                            posicao_inicio=207,
                            posicao_fim=221,
                            campo="Motivo da Ocorrência",
                            valor_encontrado=cod_m,
                            sugestao_rm=sugestao,
                        )
                    )

    return ResultadoValidacao(valido=len(erros) == 0, erros=erros)
