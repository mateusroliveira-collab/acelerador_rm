"""
Validador do "registro online" -- o registro de boleto via API do banco (JSON),
em vez de arquivo de remessa em lote.
Usa o mesmo modelo de erro (ErroValidacao) do CNAB, e reaproveita a base
de conhecimento de erros por banco (bancos/*.py) pra traduzir uma resposta
de erro do banco numa dica pro RM.
"""
import inspect
from ..erros import ErroValidacao
from ..bancos import bb, caixa

# Qual módulo de erro usar pra cada banco -- cresce conforme novos bancos
# entram na base de conhecimento.
_MODULOS_POR_BANCO = {
    "bb": bb,
    "caixa": caixa,
}

def traduzir_erro_banco(
    banco: str,
    codigo_erro: str,
    mensagem_original: str = "",
    tabela: str | None = None,
) -> ErroValidacao:
    """
    Recebe um erro cru devolvido pelo banco e devolve
    um ErroValidacao já com a dica de onde corrigir no RM, se essa
    combinação banco + código já for conhecida.
    """
    modulo = _MODULOS_POR_BANCO.get(banco.lower())
    
    # Se o banco não existir no nosso dicionário, devolve erro amigável
    if not modulo:
        return ErroValidacao(
            mensagem=mensagem_original or f"Erro não catalogado (código {codigo_erro}).",
            valor_encontrado=codigo_erro,
            sugestao_rm=f'Banco "{banco}" não configurado na base de conhecimento.',
        )

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