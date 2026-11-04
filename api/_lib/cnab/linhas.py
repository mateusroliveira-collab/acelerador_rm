"""
Leitura das linhas de um arquivo CNAB (240 ou 400), compartilhada por
todos os validadores e pelo corretor.

Arquivo gerado por banco/ERP frequentemente termina com linhas em branco
extras ou com o caractere de fim de arquivo do DOS (0x1A, "Ctrl+Z"). Sem
tratar isso, a "última linha" vira uma linha vazia e o validador acusa
"trailer inválido" num arquivo que está correto.
"""

_FIM_DE_ARQUIVO_DOS = "\x1a"


def ler_linhas(conteudo: str) -> list[str]:
    """Quebra o conteúdo em linhas, descartando linhas em branco no final."""
    linhas = conteudo.splitlines()
    while linhas and linhas[-1].strip(" \t" + _FIM_DE_ARQUIVO_DOS) == "":
        linhas.pop()
    return linhas


def detectar_quebra_de_linha(conteudo: str) -> str:
    """Devolve a quebra de linha usada no arquivo original (CNAB costuma exigir CRLF)."""
    return "\r\n" if "\r\n" in conteudo else "\n"
