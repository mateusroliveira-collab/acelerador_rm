"""
Validador e tradutor de erros do Registro Online (Caixa e Banco do Brasil).
"""
from ..erros import ErroValidacao
from ..bancos import bb, caixa


def traduzir_erro_banco(
    banco: str, codigo_erro: str, mensagem: str = "", tabela: str | None = None
) -> ErroValidacao:
    """
    Traduz o código de erro retornado pela API do banco em uma dica
    de resolução para o TOTVS RM Backoffice Financeiro.
    """
    banco_lower = banco.lower()
    info = None

    if banco_lower in ("caixa", "104"):
        info = caixa.buscar_erro(codigo_erro, tabela)
    elif banco_lower in ("bb", "banco_do_brasil", "001"):
        info = bb.buscar_erro_bb(codigo_erro)

    if info:
        causa = info.get("causa_provavel", "")
        sugestao = info.get("sugestao_rm", "")
        dica_completa = f"{causa} {sugestao}".strip()

        return ErroValidacao(
            mensagem=f'Erro {banco.upper()}: ({codigo_erro}) {info.get("mensagem_banco", mensagem)}',
            campo="Registro Online",
            valor_encontrado=codigo_erro,
            sugestao_rm=dica_completa or "Verifique o cadastro de origem no TOTVS RM.",
        )

    return ErroValidacao(
        mensagem=f"Erro {banco.upper()} ({codigo_erro}): {mensagem or 'Retorno de erro do banco.'}",
        campo="Registro Online",
        valor_encontrado=codigo_erro,
        sugestao_rm="Consulte os logs de transmissão do RM ou o manual de integração do banco.",
    )