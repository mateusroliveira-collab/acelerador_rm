"""
Regra de negócio de um XML de parâmetros de tipo de movimento do RM.

O XML exportado pelo RM é uma lista de (formulário, propriedade, valor) --
ex.: MovTMvEstoqueEstoqueParamsForm / EfeitoSaldoA2 / "A". Este módulo lê
só as propriedades que definem o COMPORTAMENTO do movimento e traduz para
uma ficha legível: mexe no estoque? gera financeiro a pagar ou a receber?
escritura nos livros fiscais? emite NF-e? afeta orçamento? contabiliza?
para quais movimentos segue no fluxo?

Lógica pura e determinística (sem IA). O significado de cada valor foi
conferido contra os 132 XMLs da biblioteca (ex.: PagouRecLan = 2 em todas
as entradas de compra e 1 em todas as saídas de venda). O que foi INFERIDO
da biblioteca, e não lido de documentação oficial, está marcado como tal.

Ler os 132 XMLs (35 MB) leva quase 1 s; por isso a biblioteca fixa tem um
índice pré-calculado em data/regras_xml.json (gerado por
scripts/gerar_indice_regras_xml.py; um teste garante que está em dia).
XMLs personalizados (do banco) são lidos na hora, um por vez.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

from . import config

ARQUIVO_INDICE = config.BASE_DIR / "data" / "regras_xml.json"
VERSAO_INDICE = 1

# Classificação do tipo de movimento (Mov.Classificacao). Descrições INFERIDAS
# do uso na biblioteca (qual movimento usa qual código), não da documentação.
CLASSIFICACOES = {
    "04.04.03": "Implantação de saldo de estoque",
    "04.04.04": "Requisição de material",
    "04.04.05": "Baixa de material do estoque",
    "04.04.06": "Transferência de estoque",
    "04.04.07": "Ajuste / inventário de estoque",
    "04.04.10": "Devolução de material ao estoque",
    "04.06.01": "Solicitação de compra",
    "04.06.04": "Pedido / ordem de compra / contrato de compra",
    "04.06.05": "Nota fiscal de compra de material",
    "04.06.07": "Nota fiscal de serviço / documento de compra",
    "04.06.08": "Devolução de compra",
    "04.07": "Aquisição de ativo imobilizado",
    "04.08.01": "Pedido de venda / pré-nota",
    "04.08.02": "Nota fiscal de saída / faturamento",
    "04.08.04": "Devolução de venda",
    "04.09": "Outros documentos (financeiro sem nota)",
}

# Saldo 2 é o saldo de estoque de verdade (A = quantidade, B = valor): é ele
# que muda em toda NF de compra, baixa, ajuste e transferência da biblioteca.
# Os outros números aparecem só em pedidos (A3) e requisições (A10) -- nome
# exato depende da configuração do cliente, então ficam como "Saldo N".
_SALDO_ESTOQUE = "A2"
_EFEITO = {"A": "aumenta", "D": "diminui"}

# Orcamento.EfeitoNoSaldoOrcamento: N = não afeta, D = estorna (aparece só em
# devoluções/estornos); os demais (A, T, M) afetam o saldo orçamentário em
# fases diferentes -- a biblioteca usa T em solicitações, M em pedidos e A em
# notas, o que sugere comprometido/empenhado/realizado (INFERIDO).
_ORCAMENTO_FASE = {"T": "solicitação", "M": "pedido", "A": "realizado"}

_RE_STRING_LISTA = re.compile(r"<string>([^<]+)</string>")


@dataclass
class RegraXml:
    codigo: str = ""
    nome: str = ""
    classificacao: str | None = None
    classificacao_descricao: str | None = None
    estoque: str = "nenhum"  # aumenta | diminui | nenhum
    outros_saldos: list[str] = field(default_factory=list)  # ex.: "Saldo A3 aumenta"
    financeiro: str = "nenhum"  # pagar | receber | nenhum
    escritura_fiscal: bool = False
    natureza: str | None = None  # E (entrada) | S (saída)
    emite_nfe: bool = False
    emite_nfse: bool = False
    cfop: str | None = None
    cfop_fora_estado: str | None = None
    orcamento: str = "nenhum"  # nenhum | afeta | estorna
    orcamento_fase: str | None = None
    contabiliza: bool = False
    aprovacao: bool = False
    gera_contrato: bool = False
    segue_para: list[str] = field(default_factory=list)  # movimentos de destino no fluxo
    gera_por_padrao: str | None = None

    def para_dict(self) -> dict:
        d = asdict(self)
        d["resumo"] = self.resumo()
        return d

    def resumo(self) -> list[str]:
        """Frases curtas, na ordem em que o analista costuma conferir."""
        f: list[str] = []
        if self.classificacao:
            desc = f" ({self.classificacao_descricao})" if self.classificacao_descricao else ""
            f.append(f"Classificação {self.classificacao}{desc}.")
        f.append({
            "aumenta": "Estoque: aumenta o saldo (entrada).",
            "diminui": "Estoque: diminui o saldo (saída).",
        }.get(self.estoque, "Estoque: não movimenta o saldo."))
        if self.outros_saldos:
            f.append("Outros saldos: " + ", ".join(self.outros_saldos) + ".")
        f.append({
            "pagar": "Financeiro: gera lançamento a PAGAR.",
            "receber": "Financeiro: gera lançamento a RECEBER.",
        }.get(self.financeiro, "Financeiro: não gera lançamento."))
        if self.escritura_fiscal:
            f.append("Fiscal: escritura nos livros fiscais.")
        else:
            f.append("Fiscal: não escritura.")
        if self.emite_nfe:
            f.append("Emite NF-e (estadual).")
        if self.emite_nfse:
            f.append("Emite NFS-e (municipal).")
        if self.cfop:
            fora = f" / fora do estado {self.cfop_fora_estado}" if self.cfop_fora_estado else ""
            f.append(f"Natureza (CFOP) padrão: {self.cfop}{fora}.")
        if self.orcamento == "afeta":
            fase = f" (fase: {self.orcamento_fase})" if self.orcamento_fase else ""
            f.append(f"Orçamento: afeta o saldo orçamentário{fase}.")
        elif self.orcamento == "estorna":
            f.append("Orçamento: estorna o saldo orçamentário.")
        if self.contabiliza:
            f.append("Contabiliza (evento contábil).")
        if self.aprovacao:
            f.append("Exige aprovação.")
        if self.gera_contrato:
            f.append("Gera contrato.")
        if self.segue_para:
            f.append("Segue no fluxo para: " + ", ".join(self.segue_para) + ".")
        return f


def ler_propriedades(conteudo: str | bytes) -> dict[str, str | None]:
    """
    {"Estoque.EfeitoSaldoA2": "A", ...}: formulário sem o prefixo
    "MovTMv"/sufixo "ParamsForm", ponto, propriedade. Lança ValueError se não
    for um XML de parâmetros de movimento.
    """
    try:
        raiz = ET.fromstring(conteudo)
    except ET.ParseError as e:
        raise ValueError(f"XML inválido: {e}") from e
    props: dict[str, str | None] = {}
    for el in raiz:
        prop = el.findtext("ClassProps")
        if not prop:
            continue
        form = el.tag.removeprefix("MovTMv").removesuffix("ParamsForm")
        c = el.find("Conteudo")
        props[f"{form}.{prop}"] = c.text if c is not None else None
    if not props:
        raise ValueError("Não parece um XML de parâmetros de tipo de movimento do RM.")
    return props


def _verdadeiro(v: str | None) -> bool:
    return (v or "").strip().lower() in ("true", "1", "t", "s")


def regra_de_propriedades(p: dict[str, str | None]) -> RegraXml:
    r = RegraXml(
        codigo=(p.get("Mov.CodTipoMovimento") or "").strip(),
        nome=(p.get("Mov.NomeTipoMovimento") or "").strip(),
    )

    cls = (p.get("Mov.Classificacao") or "").strip() or None
    r.classificacao = cls
    r.classificacao_descricao = CLASSIFICACOES.get(cls or "")

    for chave, valor in sorted(p.items()):
        m = re.fullmatch(r"EstoqueEstoque\.EfeitoSaldo([AB]\d+)", chave)
        if not m or valor not in _EFEITO:
            continue
        saldo = m.group(1)
        if saldo == _SALDO_ESTOQUE:
            r.estoque = _EFEITO[valor]
        elif not saldo.startswith("B"):  # B = valor; já coberto pelo A correspondente
            r.outros_saldos.append(f"Saldo {saldo} {_EFEITO[valor]}")

    if _verdadeiro(p.get("FinanceiroFaturamento.Fatura")):
        r.financeiro = {"1": "receber", "2": "pagar"}.get(
            (p.get("FinanceiroFaturamento.PagouRecLan") or "").strip(), "nenhum"
        )

    r.escritura_fiscal = _verdadeiro(p.get("FiscalEscrituracao.GeraEscrituracao"))
    nat = (p.get("FiscalDados.TipoNaturezaNota") or "").strip().upper()
    r.natureza = nat if nat in ("E", "S") else None
    r.emite_nfe = _verdadeiro(p.get("FiscalNFe.NFeEstadual"))
    r.emite_nfse = _verdadeiro(p.get("FiscalNFe.NFeMunicipal"))
    r.cfop = (p.get("FiscalNatureza.CodNat") or "").strip() or None
    r.cfop_fora_estado = (p.get("FiscalNatureza.CodNatForaEstado") or "").strip() or None

    orc = (p.get("Orcamento.EfeitoNoSaldoOrcamento") or "N").strip().upper()
    if orc == "D":
        r.orcamento = "estorna"
    elif orc in _ORCAMENTO_FASE:
        r.orcamento = "afeta"
        r.orcamento_fase = _ORCAMENTO_FASE[orc]

    r.contabiliza = (p.get("Contabilidade.UsarEventoCtb") or "0").strip() not in ("", "0")
    r.aprovacao = _verdadeiro(p.get("MovDados.UsaAprovacao"))
    r.gera_contrato = _verdadeiro(p.get("Contrato.GeraContrato"))
    r.segue_para = _RE_STRING_LISTA.findall(p.get("CmpFatCaracteristicas.TipoMovFaturamento") or "")
    r.gera_por_padrao = (p.get("CmpFatCaracteristicas.CodTMvPed") or "").strip() or None
    return r


def regra_de_conteudo(conteudo: str | bytes) -> RegraXml:
    return regra_de_propriedades(ler_propriedades(conteudo))


# --- Biblioteca fixa (índice pré-calculado) ---------------------------------


def calcular_indice() -> dict:
    """Lê todos os XMLs fixos. Lento (~1 s): só para o script e o teste."""
    regras: dict[str, dict] = {}
    for grupo in config.GRUPOS:
        pasta = config.pasta_do_grupo(grupo)
        if not pasta.exists():
            continue
        for f in sorted(pasta.iterdir(), key=lambda x: x.name):
            if f.is_file() and f.suffix.lower() == ".xml":
                try:
                    regra = regra_de_conteudo(f.read_bytes())
                except ValueError:
                    continue
                regras[f"{grupo}/{f.name}"] = asdict(regra)
    return {"versao": VERSAO_INDICE, "regras": regras}


@lru_cache(maxsize=1)
def _indice() -> dict[str, dict]:
    try:
        dados = json.loads(Path(ARQUIVO_INDICE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if dados.get("versao") != VERSAO_INDICE:
        return {}
    return dados.get("regras", {})


def regra_da_biblioteca(grupo: str, nome_arquivo: str) -> RegraXml | None:
    """Regra de um XML fixo: pelo índice; se faltar, lê o arquivo."""
    dado = _indice().get(f"{grupo}/{nome_arquivo}")
    if dado is not None:
        return RegraXml(**dado)
    if not config.grupo_existe(grupo):
        return None
    caminho = config.pasta_do_grupo(grupo) / nome_arquivo
    # Só arquivos de dentro da pasta do grupo (sem "../").
    if caminho.parent != config.pasta_do_grupo(grupo) or not caminho.is_file():
        return None
    try:
        return regra_de_conteudo(caminho.read_bytes())
    except ValueError:
        return None


def regras_da_biblioteca() -> list[tuple[str, str, RegraXml]]:
    """[(grupo, nome_arquivo, regra)] de toda a biblioteca fixa, pelo índice."""
    saida = []
    for chave, dado in _indice().items():
        grupo, _, nome = chave.partition("/")
        saida.append((grupo, nome, RegraXml(**dado)))
    return saida
