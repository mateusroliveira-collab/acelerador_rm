"""
Análise da MIT 41 inteira contra a biblioteca de XMLs.

Para cada movimento da MIT:
  1. o que a MIT pede (requisitos.py), com a frase que justifica;
  2. o grupo (1.1 a 4.1): matcher atual; se ele não decidir, os requisitos;
  3. o XML da biblioteca que mais se parece -- comparando a REGRA de negócio
     de cada XML (regras_xml.py) com o que a MIT pede, mais o nome;
  4. a classificação:
       pronto  -> há XML sem nenhuma divergência com a MIT;
       ajustar -> há XML-base, mas 1 ou 2 parâmetros divergem (diz quais);
       criar   -> nada parecido (3+ divergências ou grupo sem XML): ficha
                  de criação a partir do XML mais próximo;
       sem_dados -> não parece tipo de movimento, ou a MIT não detalha.
  5. a ficha: grupo, código sugerido, XML-base, ajustes (parâmetro a mexer,
     com a frase da MIT), o que a MIT não diz (confirmar com o cliente) e o
     fluxo (de qual movimento vem, para qual segue).

Determinístico, sem IA. Pesos e limites ficam nas constantes abaixo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..regras_xml import RegraXml, regras_da_biblioteca
from .matcher import sugerir_grupos
from .parser import parsear_mit41, separar_movimentos
from .pre_processador import SubProcesso, montar_campos_para_matcher, pre_processar_documento
from .requisitos import (
    DIMENSOES,
    Requisitos,
    citacoes_de_movimentos,
    extrair_requisitos,
    normalizar,
    texto_de_campos,
)

# Peso de cada dimensão no casamento MIT x XML. Divergência custa peso + 1.
PESOS = {
    "estoque": 3, "financeiro": 3, "escritura_fiscal": 2, "natureza": 1,
    "emite_nfe": 2, "emite_nfse": 2, "orcamento": 1, "contabiliza": 1,
    "aprovacao": 1, "gera_contrato": 1,
}
PESO_NOME = 8  # multiplicado pela semelhança de nome (0 a 1)
BONUS_GRUPO = 3
NOME_FORTE = 0.5  # metade ou mais das palavras do título da MIT no nome do XML
MAX_DIVERGENCIAS_AJUSTAR = 2

# Dimensões que, sem resposta da MIT, viram pendência a confirmar com o cliente.
ESSENCIAIS = ("estoque", "financeiro", "escritura_fiscal")

# Onde mexer no XML/parametrização. Área = aba da parametrização do tipo de
# movimento (nomes INFERIDOS dos formulários do XML); propriedade = nome exato
# no XML exportado do RM.
PARAMETROS = {
    "estoque": ("Estoque", "EfeitoSaldoA2 / EfeitoSaldoB2 (A = aumenta, D = diminui, N = nenhum)"),
    "financeiro": ("Financeiro > Faturamento", "Fatura (true/false) e PagouRecLan (1 = receber, 2 = pagar)"),
    "escritura_fiscal": ("Fiscal > Escrituração", "GeraEscrituracao"),
    "natureza": ("Fiscal > Dados", "TipoNaturezaNota (E/S)"),
    "emite_nfe": ("Fiscal > NF-e", "NFeEstadual"),
    "emite_nfse": ("Fiscal > NF-e", "NFeMunicipal"),
    "orcamento": ("Orçamento", "EfeitoNoSaldoOrcamento (N = nenhum, D = estorna, T/M/A = afeta)"),
    "contabiliza": ("Contabilidade", "UsarEventoCtb e CodEvento"),
    "aprovacao": ("Movimento > Dados", "UsaAprovacao"),
    "gera_contrato": ("Contrato", "GeraContrato"),
}

_TEXTO_VALOR = {
    "estoque": {"aumenta": "aumenta o estoque", "diminui": "diminui o estoque",
                "nenhum": "não movimenta estoque", "transfere": "transfere estoque (sai de um local, entra em outro)"},
    "financeiro": {"pagar": "gera financeiro a pagar", "receber": "gera financeiro a receber",
                   "nenhum": "não gera financeiro", "gera": "gera financeiro (a MIT não diz se é a pagar ou a receber)"},
    "natureza": {"E": "nota de entrada", "S": "nota de saída", None: "sem natureza definida"},
    "orcamento": {"afeta": "afeta o orçamento", "estorna": "estorna o orçamento", "nenhum": "não afeta o orçamento"},
}

_NOMES_BOOL = {
    "escritura_fiscal": "escritura nos livros fiscais",
    "emite_nfe": "emite NF-e",
    "emite_nfse": "emite NFS-e",
    "contabiliza": "contabiliza",
    "aprovacao": "exige aprovação",
    "gera_contrato": "gera contrato",
}

_STOP = {"de", "da", "do", "das", "dos", "e", "a", "o", "as", "os", "para", "p", "por", "com",
         "em", "no", "na", "nos", "nas", "c", "s", "ao", "levi", "movimento", "processo"}
_IGNORAR_XML = re.compile(r"nao utilizar|concluir", re.IGNORECASE)


@dataclass
class MovimentoMit:
    numero: str
    titulo: str
    texto: str  # texto que descreve o que o movimento faz (TO BE ou campos)
    campos_matcher: dict[str, str] = field(default_factory=dict)


@dataclass
class Candidato:
    grupo: str
    arquivo: str
    regra: RegraXml
    id: int | None = None  # XML personalizado


# --- Entrada ----------------------------------------------------------------


def movimentos_de_texto(texto: str) -> list[MovimentoMit]:
    """
    Aceita a saída do interpretador ([INICIO_MOVIMENTO]...) OU o texto bruto
    da MIT (subprocessos numerados com TO BE).
    """
    if "[INICIO_MOVIMENTO]" in texto:
        movs = []
        for i, bloco in enumerate(separar_movimentos(texto), start=1):
            campos = parsear_mit41(bloco)
            if not campos:
                continue
            movs.append(MovimentoMit(
                numero=str(i),
                titulo=campos.get("NOME_MOVIMENTO") or f"Movimento {i}",
                texto=texto_de_campos(campos),
                campos_matcher=campos,
            ))
        return movs
    return movimentos_de_subprocessos(pre_processar_documento(texto))


def movimentos_de_subprocessos(subprocessos: list[SubProcesso]) -> list[MovimentoMit]:
    movs = []
    for sp in subprocessos:
        # O AS IS descreve o processo ATUAL; o que vale para a parametrização
        # é o TO BE (+ GAP). Sem TO BE identificado, usa o bloco inteiro.
        partes = [p for p in (sp.texto_to_be, sp.gap) if p]
        texto = "\n".join(partes) if partes else sp.texto_bruto_completo
        if not (texto or "").strip() and not sp.numero:
            continue  # texto vazio / sem nenhum subprocesso reconhecível
        movs.append(MovimentoMit(
            numero=sp.numero, titulo=sp.titulo, texto=texto or "",
            campos_matcher=montar_campos_para_matcher(sp),
        ))
    return movs


# --- Comparação MIT x XML ----------------------------------------------------


def _valor_xml(dim: str, regra: RegraXml):
    v = getattr(regra, dim)
    if isinstance(v, bool):
        return "sim" if v else "nao"
    return v


def compativel(dim: str, pedido: str, regra: RegraXml, grupo: str) -> bool:
    xml = _valor_xml(dim, regra)
    if dim == "estoque" and pedido == "transfere":
        return grupo == "3.1" or xml in ("aumenta", "diminui")
    if dim == "financeiro" and pedido == "gera":
        return xml in ("pagar", "receber")
    return pedido == xml


def descrever(dim: str, valor) -> str:
    if dim in _TEXTO_VALOR:
        return _TEXTO_VALOR[dim].get(valor, str(valor))
    nome = _NOMES_BOOL.get(dim, dim)
    return nome if valor == "sim" else f"não {nome}"


def _tokens(texto: str) -> set[str]:
    saida = set()
    for t in normalizar(texto).replace("-", " ").split():
        if t in _STOP or t.isdigit() or len(t) < 2:
            continue
        saida.add(t[:-1] if len(t) > 4 and t.endswith("s") else t)
    return saida


def semelhanca_nome(titulo_mit: str, candidato: Candidato) -> float:
    """Quanto do título da MIT aparece no nome do XML (0 a 1)."""
    alvo = _tokens(titulo_mit)
    if not alvo:
        return 0.0
    nome = _tokens(candidato.regra.nome) | _tokens(candidato.arquivo.rsplit(".", 1)[0])
    return len(alvo & nome) / len(alvo)


def pontuar(mov: MovimentoMit, req: Requisitos, cand: Candidato, grupo_alvo: str | None) -> dict:
    pontos = 0.0
    divergencias, coincidencias = [], []
    for dim in DIMENSOES:
        pedido = req.valor(dim)
        if pedido is None:
            continue
        if compativel(dim, pedido, cand.regra, cand.grupo):
            pontos += PESOS[dim]
            coincidencias.append(dim)
        else:
            pontos -= PESOS[dim] + 1
            divergencias.append(dim)
    nome = semelhanca_nome(mov.titulo, cand)
    pontos += PESO_NOME * nome
    if grupo_alvo and cand.grupo == grupo_alvo:
        pontos += BONUS_GRUPO
    return {"pontos": round(pontos, 2), "divergencias": divergencias,
            "coincidencias": coincidencias, "semelhanca_nome": round(nome, 2)}


# --- Grupo ------------------------------------------------------------------


def grupo_pelos_requisitos(req: Requisitos) -> str | None:
    """Grupo deduzido só do que a MIT pede (usado quando o matcher não decide)."""
    estoque, fin = req.valor("estoque"), req.valor("financeiro")
    escritura, nat = req.valor("escritura_fiscal"), req.valor("natureza")
    emite = "sim" in (req.valor("emite_nfe"), req.valor("emite_nfse"))
    if estoque == "transfere":
        return "3.1"
    if fin == "receber" or nat == "S" or emite:
        return "2.2" if (escritura == "sim" or emite) else "2.1"
    if fin == "pagar" or nat == "E":
        return "1.2" if (escritura == "sim" or nat == "E") else "1.1"
    if estoque in ("aumenta", "diminui") and fin in (None, "nenhum"):
        return "4.1"
    return None


def _proximo_codigo(grupo: str, candidatos: list[Candidato]) -> str:
    maior = 0
    for c in candidatos:
        m = re.fullmatch(re.escape(grupo) + r"\.(\d+)", c.regra.codigo or "")
        if c.grupo == grupo and m:
            maior = max(maior, int(m.group(1)))
    return f"{grupo}.{maior + 1:02d}"


# --- Análise ----------------------------------------------------------------


def candidatos_da_biblioteca(extras: list[Candidato] | None = None) -> list[Candidato]:
    base = [Candidato(g, n, r) for g, n, r in regras_da_biblioteca()]
    todos = base + list(extras or [])
    return [c for c in todos if not _IGNORAR_XML.search(normalizar(f"{c.regra.nome} {c.arquivo}"))]


def analisar_movimento(mov: MovimentoMit, candidatos: list[Candidato], titulos: dict[str, str]) -> dict:
    req = extrair_requisitos(mov.texto)
    sugestoes = sugerir_grupos(mov.campos_matcher or {"NOME_MOVIMENTO": mov.titulo})
    grupo_matcher = sugestoes[0]["grupo"] if sugestoes else None
    grupo_req = grupo_pelos_requisitos(req)
    # O conteúdo vence o nome quando a MIT descreve o comportamento com
    # clareza (2+ dimensões essenciais): "Compra de Material" que escritura,
    # dá entrada no estoque e gera contas a pagar é 1.2, não 1.1.
    conteudo_forte = sum(req.valor(d) is not None for d in ESSENCIAIS) >= 2
    if grupo_req and (not grupo_matcher or (conteudo_forte and grupo_req != grupo_matcher)):
        grupo, origem_grupo = grupo_req, "requisitos da MIT"
    elif grupo_matcher:
        grupo, origem_grupo = grupo_matcher, "nome e processo"
    else:
        grupo, origem_grupo = None, None

    avisos = []
    if grupo_matcher and grupo_req and grupo_matcher != grupo_req:
        avisos.append(
            f"O nome sugere o grupo {grupo_matcher}, mas o que a MIT descreve combina com o "
            f"{grupo_req}. Usado: {grupo}. Confira antes de criar."
        )
    for dim in req.ambiguas():
        avisos.append(f"A MIT é contraditória sobre {DIMENSOES[dim].lower()}: veja as frases e decida.")

    conhecidos = [d for d in DIMENSOES if req.valor(d) is not None]
    fluxo = citacoes_de_movimentos(mov.texto, {n: t for n, t in titulos.items() if n != mov.numero})

    if not grupo and not conhecidos:
        return {
            "numero": mov.numero, "titulo": mov.titulo, "status": "sem_dados",
            "grupo": None, "origem_grupo": None, "requisitos": req.para_dict(),
            "candidatos": [], "ficha": None, "fluxo": fluxo,
            "avisos": ["Não parece um tipo de movimento (ex.: cadastro) ou a MIT não detalha o comportamento."],
        }

    # Candidatos: XMLs do grupo provável + XMLs de QUALQUER grupo com nome bem
    # parecido (a biblioteca tem movimento guardado em grupo "errado", ex.:
    # Requisição de Material em 1.1).
    grupos_validos = {g for g in (grupo, grupo_req) if g}
    pool = [
        c for c in candidatos
        if c.grupo in grupos_validos or semelhanca_nome(mov.titulo, c) >= NOME_FORTE
    ] or candidatos
    ranking = sorted(
        ((pontuar(mov, req, c, grupo), c) for c in pool),
        key=lambda x: (-x[0]["pontos"], len(x[0]["divergencias"]), x[1].grupo, x[1].arquivo),
    )
    top = ranking[:3]

    confianca = "baixa"
    if top:
        p, _ = top[0]
        forte_nome = p["semelhanca_nome"] >= NOME_FORTE
        if forte_nome and len(p["coincidencias"]) >= 2:
            confianca = "alta"
        elif forte_nome or len(p["coincidencias"]) >= 2:
            confianca = "media"

    if not top:
        status = "criar"
    else:
        n_div = len(top[0][0]["divergencias"])
        status = "pronto" if n_div == 0 else ("ajustar" if n_div <= MAX_DIVERGENCIAS_AJUSTAR else "criar")
        if status == "pronto" and confianca == "baixa":
            # Sem divergência, mas também sem evidência (nome diferente e a MIT
            # quase não detalha): não dá para afirmar que o XML serve.
            status = "criar"
            avisos.append(
                "Nenhum XML com nome parecido e a MIT detalha pouco: o XML-base indicado é só o "
                "mais próximo pela regra. Confirme o comportamento com o cliente."
            )
        if status == "pronto" and grupo and top[0][1].grupo != grupo:
            status = "ajustar"
            avisos.append(
                f"O XML mais parecido está no grupo {top[0][1].grupo}, mas o movimento é do grupo "
                f"{grupo}: crie no grupo certo usando o XML como base."
            )

    base = top[0][1] if top else None
    ajustes = []
    if base:
        for dim in top[0][0]["divergencias"]:
            area, prop = PARAMETROS[dim]
            ajustes.append({
                "dimensao": dim, "rotulo": DIMENSOES[dim],
                "mit_pede": descrever(dim, req.valor(dim)),
                "xml_base_faz": descrever(dim, _valor_xml(dim, base.regra)),
                "area": area, "propriedade": prop,
                "trecho": req.evidencias[dim][0].trecho,
            })
    pendencias = [
        f"{DIMENSOES[d]}: a MIT não diz -- confirmar com o cliente."
        for d in ESSENCIAIS if req.valor(d) is None and d not in req.ambiguas()
    ]
    grupo_ficha = grupo or (base.grupo if base else None)
    ficha = {
        "grupo": grupo_ficha,
        "codigo_sugerido": _proximo_codigo(grupo_ficha, candidatos) if grupo_ficha else None,
        "nome": mov.titulo,
        "xml_base": {"grupo": base.grupo, "arquivo": base.arquivo, "id": base.id,
                     "codigo": base.regra.codigo, "nome": base.regra.nome} if base else None,
        "ajustes": ajustes,
        "pendencias": pendencias,
        "regra_desejada": [
            f"{DIMENSOES[d]}: {descrever(d, req.valor(d))}." for d in conhecidos
        ],
        "segue_para_no_xml_base": base.regra.segue_para if base else [],
    }

    return {
        "numero": mov.numero, "titulo": mov.titulo, "status": status, "confianca": confianca,
        "grupo": grupo, "origem_grupo": origem_grupo, "sugestoes_grupo": sugestoes[:2],
        "requisitos": req.para_dict(),
        "candidatos": [
            {"grupo": c.grupo, "arquivo": c.arquivo, "id": c.id, "codigo": c.regra.codigo,
             "nome": c.regra.nome, "resumo": c.regra.resumo(), **p}
            for p, c in top
        ],
        "ficha": ficha, "fluxo": fluxo, "avisos": avisos,
    }


def analisar(movimentos: list[MovimentoMit], extras: list[Candidato] | None = None) -> dict:
    candidatos = candidatos_da_biblioteca(extras)
    titulos = {m.numero: m.titulo for m in movimentos}
    resultados = [analisar_movimento(m, candidatos, titulos) for m in movimentos]
    contagem = {s: 0 for s in ("pronto", "ajustar", "criar", "sem_dados")}
    for r in resultados:
        contagem[r["status"]] += 1
    return {
        "resumo": {"total": len(resultados), **contagem, "xmls_na_biblioteca": len(candidatos)},
        "movimentos": resultados,
    }
