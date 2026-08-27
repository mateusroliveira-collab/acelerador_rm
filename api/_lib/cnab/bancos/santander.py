"""
Base de conhecimento de erros específicos deste banco -- ainda vazia.

Mesma estrutura do bb.py: assim que um erro real aparecer (arquivo de
retorno ou resposta de registro online), adiciona uma entrada aqui no
mesmo formato, e o restante do sistema já sabe usar.
"""

ERROS_CONHECIDOS: dict[str, dict[str, str]] = {
    # "codigo_do_erro": {
    #     "mensagem_banco": "...",
    #     "causa_provavel": "...",
    #     "sugestao_rm": "...",
    # },
}


def buscar_erro(codigo: str) -> dict[str, str] | None:
    return ERROS_CONHECIDOS.get(codigo)
