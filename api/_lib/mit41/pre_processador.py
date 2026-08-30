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


# Cabeçalho/rodapé que o PDF real injeta NO MEIO do texto quando extrai
# (ex: "7 MIT041 – ESPECIFICAÇÃO DE PROCESSOS" aparecendo entre duas
# frases por causa de quebra de página) -- removido antes de qualquer
# outra extração, senão quebra os regex de item/seção no meio.
_PADRAO_RUIDO_PAGINA = re.compile(
    r"\d{1,3}\s+MIT\s?0?41\s*[–\-]\s*ESPECIFICAÇÃO DE PROCESSOS",
    re.IGNORECASE,
)

# Cabeçalho de subprocesso: número com 3 a 5 níveis (ex: "4.1.1.2",
# "5.1.1", "4.1.1.1.1") seguido do título até a próxima quebra/ponto forte.
# Antes só aceitava exatamente 4 níveis -- documento real tem seções
# diferentes (Compras, Estoque, Contratos) que podem numerar diferente.
_PADRAO_CABECALHO = re.compile(
    r"(\d+(?:\.\d+){2,4})\.?\s+([A-ZÀ-Ú][^\n]{2,80}?)(?=\s+Processo Relacionado)",
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
# Fronteira extra: para no próximo título de seção de nível 1 (ex: "5.
# Processo Relacionado", "7. Aprovação"), não só em \Z -- sem isso, o GAP
# do ÚLTIMO subprocesso de cada seção "vaza" e engole a tabela-índice ou
# a seção seguinte inteira.
_PADRAO_GAP = re.compile(
    r"\bGAP\b\s*(.*?)(?=\n\s*\d+\.\s+[A-ZÀ-Ú]|\Z)", re.DOTALL
)

# Âncora confiável pra tabela-índice: toda linha da "Descrição do
# Sub-Processo" tem "Processos relacionados..." na coluna Descrição --
# isso não muda mesmo quando a extração do PDF embaralha a ordem das
# colunas Opção/Escopo (testado contra documento real). Numeração também
# flexível aqui (3 a 5 níveis).
_PADRAO_ITEM_INDICE = re.compile(
    r"(\d+(?:\.\d+){2,4})\s+(.*?)\s+Processos?\s+[Rr]elacionad[oa]s?\s+(?:a|ao|à)?\s*",
)

# Fronteira de índice: precisa bater exatamente com "N.N.N" (3 a 5
# níveis) -- protege contra outras tabelas do documento (CNPJs de
# filiais, assinatura de aprovação) que não são o índice de subprocessos.
_PADRAO_NUMERO = re.compile(r"^\d+(?:\.\d+){2,4}$")


def _limpar_ruido(texto: str) -> str:
    """Remove cabeçalho/rodapé repetido que o PDF injeta no meio do texto."""
    return _PADRAO_RUIDO_PAGINA.sub(" ", texto)


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


def eh_tabela_indice(tabela: list) -> bool:
    """
    Identifica se uma tabela extraída pelo pdfplumber é uma das tabelas-
    índice "Descrição do Sub-Processo" -- usa o cabeçalho Item/Nome como
    âncora, estável mesmo quando o layout de colunas varia.
    """
    if not tabela or not tabela[0] or len(tabela[0]) < 2:
        return False
    cab = [str(c or "").strip().lower() for c in tabela[0][:2]]
    return cab == ["item", "nome"]


def extrair_indice_de_tabelas(tabelas: list) -> list[ItemIndice]:
    """
    Extrai a lista de subprocessos a partir das tabelas de VERDADE que o
    pdfplumber reconstrói via geometria do PDF (page.extract_tables()) --
    não do texto linear (extract_text()).

    Substitui extrair_indice(texto) como caminho principal quando há um
    PDF de verdade disponível: documento real mostrou que o pdfplumber
    embaralha a ordem de leitura de forma inconsistente sempre que a
    célula "Descrição" quebra em duas linhas (o texto "Processos
    relacionados..." pode aparecer ANTES do número/nome da linha, e o
    próprio "Nome" pode vir partido em duas linhas) -- regra sobre esse
    texto corrido não é confiável. A extração de tabela usa a posição
    real dos elementos no PDF, então não sofre desse problema.
    """
    itens = []
    for tabela in tabelas:
        if not eh_tabela_indice(tabela):
            continue
        for linha in tabela[1:]:
            if not linha or not linha[0]:
                continue
            numero = str(linha[0]).strip()
            if not _PADRAO_NUMERO.match(numero):
                continue  # linha de continuação/cabeçalho (P- Padrão, etc.)
            nome = re.sub(r"\s+", " ", str(linha[1] or "")).strip()
            if nome:
                itens.append(ItemIndice(numero=numero, nome=nome))
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


def pre_processar_documento(
    texto: str,
    indice_pre_extraido: list[ItemIndice] | None = None,
) -> list[SubProcesso]:
    """
    Ponto de entrada principal. Se indice_pre_extraido for passado (a
    rota de upload de PDF sempre passa, via extrair_indice_de_tabelas --
    fonte confiável, usa geometria real do PDF), usa ele. Senão, cai no
    extrair_indice(texto) via regex sobre texto linear -- mantido só por
    compatibilidade com colagem de texto direto (sem PDF), onde não tem
    tabela geométrica disponível pra extrair.

    Depois de saber o índice (por qualquer uma das duas fontes), busca o
    detalhamento de cada subprocesso mais adiante no texto, casando pelo
    número.
    """
    texto = _limpar_ruido(texto)
    indice = (
        indice_pre_extraido if indice_pre_extraido is not None else extrair_indice(texto)
    )

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
        # Busca com limite de palavra (\b) -- não com "in" simples.
        # Palavras curtas tipo "iss" (ISS) e "ipi" (IPI) são substring
        # de palavras comuns em português ("emissão", "município",
        # "princípio") -- já mordeu isso uma vez com "iss" dentro de
        # "Emissão" em documento real. Limite de palavra resolve pra
        # qualquer palavra da lista, atual ou futura.
        if re.search(r"\b" + re.escape(palavra) + r"\b", texto_to_be):
            match = re.search(r"\b" + re.escape(palavra) + r"\b", texto_to_be)
            trecho_inicio = match.start()
            campos["TRIBUTACAO"] = (sp.texto_to_be or "")[
                trecho_inicio : trecho_inicio + 60
            ]
            break

    return campos


def gerar_texto_para_ponte(subprocessos: list[SubProcesso]) -> str:
    """
    Converte os subprocessos extraídos no formato que a Ponte MIT 41 do
    Buscador de XML já sabe ler (o mesmo formato do interpretador de IA)
    -- pra copiar daqui e colar lá, em vez de colar a tabela visual
    (que é frágil: cópia de tabela renderizada perde alinhamento e não
    tem "CAMPO=valor" nenhum pra reconhecer).
    """
    blocos = []
    for sp in subprocessos:
        linhas = ["[INICIO_MOVIMENTO]", f"NOME_MOVIMENTO={sp.titulo}"]
        if sp.processo_relacionado:
            linhas.append(f"PROCESSO_ORIGEM={sp.processo_relacionado}")
        if sp.texto_to_be:
            texto_to_be_lower = sp.texto_to_be.lower()
            for palavra in _PALAVRAS_FISCAL_APROXIMADAS:
                if palavra in texto_to_be_lower:
                    linhas.append(f"TRIBUTACAO={sp.texto_to_be[:120]}")
                    break
        linhas.append("[FIM_MOVIMENTO]")
        blocos.append("\n".join(linhas))
    return "\n\n".join(blocos)
