"""
Validador do "registro online" -- o registro de boleto via API do banco
(JSON), em vez de arquivo de remessa em lote.

Usa o mesmo modelo de erro (ErroValidacao) do CNAB, e reaproveita a base
de conhecimento de erros por banco (bancos/*.py) pra traduzir uma resposta
de erro do banco numa dica pro RM.
"""

import inspect

from ..erros import ErroValidacao
from ..bancos import bb, caixa, bradesco, itau, santander, sicoob

# Qual módulo de erro usar pra cada banco -- cresce conforme novos bancos
# entram na base de conhecimento.
_MODULOS_POR_BANCO = {
    "bb": bb,
    "caixa": caixa,
    "bradesco": bradesco,
    "itau": itau,
    "santander": santander,
    "sicoob": sicoob,
}


def traduzir_erro_banco(
    banco: str,
    codigo_erro: str,
    mensagem_original: str = "",
    tabela: str | None = None,
) -> ErroValidacao:
    """
    Recebe um erro cru devolvido pelo banco (tipo o exemplo do BB:
    código 4874915, "Nosso Número já incluído anteriormente") e devolve
    um ErroValidacao já com a dica de onde corrigir no RM, se essa
    combinação banco + código já for conhecida.

    "tabela" só se aplica a bancos com mais de uma tabela de erro (hoje,
    só a Caixa -- ver bancos/caixa.py). Pra bancos com uma tabela só,
    o parâmetro é ignorado sem erro.
    """
    modulo = _MODULOS_POR_BANCO.get(banco.lower())

    # bb.py tem a função com nome específico (buscar_erro_bb); os demais
    # usam o nome genérico buscar_erro.
    buscador = getattr(modulo, "buscar_erro_bb", None) or getattr(
        modulo, "buscar_erro", None
    )

    info = None
    if buscador:
        aceita_tabela = "tabela" in inspect.signature(buscador).parameters
        if tabela is not None and aceita_tabela:
            info = buscador(codigo_erro, tabela)
        else:
            info = buscador(codigo_erro)

    if info:
        return ErroValidacao(
            mensagem=info["mensagem_banco"],
            valor_encontrado=codigo_erro,
            sugestao_rm=f'{info["causa_provavel"]} {info["sugestao_rm"]}',
        )

    # Banco/código ainda não catalogado -- devolve o erro cru mesmo assim,
    # sem dica (melhor mostrar o erro puro do que esconder ele).
    return ErroValidacao(
        mensagem=mensagem_original or f"Erro não catalogado (código {codigo_erro}).",
        valor_encontrado=codigo_erro,
        sugestao_rm=(
            f'Erro do banco "{banco}" (código {codigo_erro}) ainda não '
            "catalogado -- verifique a documentação do banco ou adicione "
            "esse código à base de conhecimento em api/_lib/cnab/bancos/."
        ),
    )
