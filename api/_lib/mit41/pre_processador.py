"""
Pré-processador do documento MIT 41 BRUTO (o Word/PDF original, antes de
qualquer interpretação).

IMPORTANTE -- limite real, testado contra documento verdadeiro (MIT041
Randstad/Athena): a classificação de negócio (EFEITO_ESTOQUE=,
EFEITO_FINANCEIRO=, DOCUMENTO_FISCAL=...) está dissolvida em texto corrido
dentro da seção "TO BE", sem nenhum rótulo direto. Extrair ISSO com regra
pura não é confiável -- exige compreensão de linguagem, é o trabalho de
verdade do "Gem 1" (interpretador).

O que ESSE módulo faz, com confiabilidade real (é estrutura de documento,
não interpretação de negócio):
  - Separa cada subprocesso numerado (ex: "4.1.1.2 Requisição de Materiais")
  - Extrai o caminho "Processo Relacionado" (ex: "Movimentos | Estoque | Requisições")
  - Separa o texto "AS IS" do "TO BE"
  - Extrai a seção "GAP"

O resultado NÃO substitui o interpretador de IA -- prepara o terreno pra
ele, e deixa claro e isolado exatamente qual pedaço (o texto do "TO BE")
precisaria de IA pra virar campo estruturado.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ItemIndice:
    numero: str
    nome: str


@dataclass
class SubProcesso:
    numero: str
    titulo: str
    processo_relacionado: str | None = None
    texto_as_is: str | None = None
    texto_to_be: str | None = None
    gap: str | None = None
    texto_bruto_completo: str = ""


# Cabeçalho de subprocesso: "4.1.1.2" ou "4.1.1.2." seguido do título até
# a próxima quebra de linha/ponto forte.
_PADRAO_CABECALHO = re.compile(
    r"(\d+\.\d+\.\d+\.\d+)\.?\s+([A-ZÀ-Ú][^\n]{2,80}?)(?=\s+Processo Relacionado)",
)

_PADRAO_PROCESSO_RELACIONADO = re.compile(
    r"Processo Relacionado\s+([^\n]+?)(?=\s+Entrada de dados|\s+Descrição)"
)

_PADRAO_AS_IS = re.compile(
    r"AS IS:?\s*(.*?)(?=TO BE:|GAP|\Z)", re.DOTALL | re.IGNORECASE
)
_PADRAO_TO_BE = re.compile(
    r"TO BE:?\s*(.*?)(?=GAP|\Z)", re.DOTALL | re.IGNORECASE
)
_PADRAO_GAP = re.compile(r"\bGAP\b\s*(.*?)\Z", re.DOTALL)

# Âncora confiável pra tabela-índice: toda linha da "Descrição do
# Sub-Processo" tem "Processos relacionados..." na coluna Descrição --
# isso não muda mesmo quando a extração do PDF embaralha a ordem das
# colunas Opção/Escopo (testado contra documento real).
_PADRAO_ITEM_INDICE = re.compile(
    r"(\d+\.\d+\.\d+\.\d+)\s+(.*?)\s+Processos?\s+[Rr]elacionad[oa]s?\s+(?:a|ao|à)?\s*",
)


def _limpar(texto: str | None) -> str | None:
    if texto is None:
        return None
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto or None


def extrair_indice(texto: str) -> list[ItemIndice]:
    """
    Extrai a lista organizada de subprocessos a partir da tabela-índice
    do início do documento (ex: "4.1.1. Descrição do Sub-Processo").

    Robusto contra a extração de PDF embaralhar a ordem das colunas
    Opção (P/E) e Escopo (S/N) -- usa "Processos relacionados..." como
    âncora fixa e limpa qualquer letra solta de coluna que sobrar no meio
    do nome capturado.
    """
    itens = []
    for match in _PADRAO_ITEM_INDICE.finditer(texto):
        numero = match.group(1)
        nome_bruto = match.group(2)
        nome_limpo = re.sub(r"\b[PESN]\b", "", nome_bruto).strip()
        nome_limpo = re.sub(r"\s+", " ", nome_limpo)
        if nome_limpo:
            itens.append(ItemIndice(numero=numero, nome=nome_limpo))
    return itens


def separar_subprocessos_brutos(texto: str) -> list[str]:
    """
    Separa o texto bruto em blocos, um por subprocesso numerado (baseado
    nos cabeçalhos tipo "4.1.1.2 Requisição de Materiais"). Se não achar
    nenhum cabeçalho reconhecível, devolve o texto inteiro como um bloco
    só (compatibilidade com colagem parcial de um único subprocesso).
    """
    posicoes = [m.start() for m in _PADRAO_CABECALHO.finditer(texto)]
    if not posicoes:
        return [texto]
    posicoes.append(len(texto))
    return [texto[posicoes[i]:posicoes[i + 1]] for i in range(len(posicoes) - 1)]


def processar_subprocesso(bloco: str) -> SubProcesso:
    """Extrai a estrutura de UM bloco de subprocesso bruto."""
    cabecalho = _PADRAO_CABECALHO.search(bloco)
    numero = cabecalho.group(1) if cabecalho else ""
    titulo = _limpar(cabecalho.group(2)) if cabecalho else None

    proc_rel = _PADRAO_PROCESSO_RELACIONADO.search(bloco)
    as_is = _PADRAO_AS_IS.search(bloco)
    to_be = _PADRAO_TO_BE.search(bloco)
    gap = _PADRAO_GAP.search(bloco)

    return SubProcesso(
        numero=numero,
        titulo=titulo or "(título não identificado)",
        processo_relacionado=_limpar(proc_rel.group(1)) if proc_rel else None,
        texto_as_is=_limpar(as_is.group(1)) if as_is else None,
        texto_to_be=_limpar(to_be.group(1)) if to_be else None,
        gap=_limpar(gap.group(1)) if gap else None,
        texto_bruto_completo=bloco.strip(),
    )


def pre_processar_documento(texto: str) -> list[SubProcesso]:
    """
    Ponto de entrada principal. Primeiro lê a tabela-índice pra saber
    exatamente quais subprocessos existem e em que ordem (lista
    organizada e confiável) -- depois busca o detalhamento de cada um
    mais adiante no texto, casando pelo número.

    Se não achar tabela-índice nenhuma (documento colado só a partir do
    detalhamento, sem a tabela), cai no comportamento antigo: separa
    direto pelos cabeçalhos de detalhamento.
    """
    indice = extrair_indice(texto)

    if not indice:
        blocos = separar_subprocessos_brutos(texto)
        return [processar_subprocesso(b) for b in blocos]

    blocos_detalhe = separar_subprocessos_brutos(texto)
    detalhe_por_numero = {
        processar_subprocesso(b).numero: processar_subprocesso(b)
        for b in blocos_detalhe
    }

    resultado = []
    for item in indice:
        detalhe = detalhe_por_numero.get(item.numero)
        if detalhe:
            resultado.append(detalhe)
        else:
            # Está no índice mas ainda não tem detalhamento colado --
            # devolve só com o nome, deixando claro que falta o resto.
            resultado.append(
                SubProcesso(numero=item.numero, titulo=item.nome)
            )
    return resultado

# Palavras que, aparecendo no texto TO BE, são um indício (fraco, mas
# real) de efeito fiscal -- usado só pra alimentar o matcher com um
# "campo fiscal" aproximado, já que a extração bruta não separa isso em
# campo próprio (isso é exatamente o pedaço que precisaria de IA de
# verdade pra virar DOCUMENTO_FISCAL=/TRIBUTACAO= com confiança).
_PALAVRAS_FISCAL_APROXIMADAS = [
    "nota fiscal", "icms", "ipi", "iss", "tributação", "tributacao",
    "imposto", "nf-e", "danfe",
]


def montar_campos_para_matcher(sp: SubProcesso) -> dict[str, str]:
    """
    Constrói um dicionário "parecido" com o que o interpretador de IA
    devolveria, só que a partir dos campos brutos (sem interpretação de
    negócio de verdade). É uma ponte deliberadamente mais fraca -- serve
    pra dar uma sugestão inicial na tabela, mas não substitui a Ponte
    MIT 41 completa (que usa a saída já interpretada pelo Gem).
    """
    campos: dict[str, str] = {"NOME_MOVIMENTO": sp.titulo}
    if sp.processo_relacionado:
        campos["PROCESSO_ORIGEM"] = sp.processo_relacionado

    texto_to_be = (sp.texto_to_be or "").lower()
    for palavra in _PALAVRAS_FISCAL_APROXIMADAS:
        if palavra in texto_to_be:
            # Marca um sinal fiscal aproximado -- valor é só um trecho
            # pra transparência, não uma classificação de verdade.
            trecho_inicio = texto_to_be.find(palavra)
            campos["TRIBUTACAO"] = (sp.texto_to_be or "")[
                trecho_inicio : trecho_inicio + 60
            ]
            break

    return campos
