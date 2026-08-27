"""
Base de conhecimento de erros específicos do Banco do Brasil -- tanto de
retorno de CNAB quanto de resposta da API de registro online.

Cresce incrementalmente: cada vez que um erro real aparecer no dia a dia,
adiciona uma entrada aqui. Não tenta cobrir tudo de uma vez -- só o que já
foi visto de verdade, pra não inventar causa/sugestão sem confirmação.
"""

# Mapa: código do erro (como o banco devolve) -> dica pronta pro RM
ERROS_CONHECIDOS: dict[str, dict[str, str]] = {
    "4874915": {
        "mensagem_banco": "Nosso Número já incluído anteriormente.",
        "causa_provavel": (
            "O sistema tentou registrar um boleto com um Nosso Número que "
            "já foi enviado ao BB antes -- geralmente acontece quando o "
            "título é reenviado sem gerar um número novo."
        ),
        "sugestao_rm": (
            "No RM, verifique a rotina de geração de Nosso Número do título "
            "em questão -- confira se ele não está sendo reprocessado/"
            "reenviado a partir de um título já registrado."
        ),
    },
}


def buscar_erro_bb(codigo: str) -> dict[str, str] | None:
    """Procura um código de erro do BB na base de conhecimento."""
    return ERROS_CONHECIDOS.get(codigo)
