"""
O que a MIT 41 pede para UM movimento: estoque, financeiro, fiscal,
orçamento, contabilização, aprovação, contrato -- com o TRECHO da MIT que
justifica cada conclusão.

Determinístico, sem IA. Lê frase por frase do texto (o "TO BE" do
pré-processador ou os campos do interpretador), procura expressões de
negócio conhecidas e trata negação na mesma frase ("Movimento NÃO gera
integração fiscal" vira escritura_fiscal = não). O que a MIT não diz fica
como None ("a MIT não diz") -- nunca é chutado. Se a MIT diz coisas
contraditórias, a dimensão fica ambígua e as duas evidências aparecem.

As dimensões têm os mesmos nomes dos campos de regras_xml.RegraXml, para
o cruzamento com a biblioteca ser direto.

Para ajustar: edite as listas de REGRAS abaixo (e acrescente um caso em
tests/test_requisitos_mit41.py).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# Rótulos das dimensões, para a tela e para a ficha.
DIMENSOES = {
    "estoque": "Estoque",
    "financeiro": "Financeiro",
    "escritura_fiscal": "Escrituração fiscal",
    "natureza": "Natureza da nota",
    "emite_nfe": "Emissão de NF-e",
    "emite_nfse": "Emissão de NFS-e",
    "orcamento": "Orçamento",
    "contabiliza": "Contabilização",
    "aprovacao": "Aprovação",
    "gera_contrato": "Gera contrato",
}

_W = r"(?:[\w-]+\s+)"  # uma palavra qualquer + espaço
_NEG = r"\b(?:nao|sem|nenhum|nenhuma)\b"

# dimensão -> (regras de NEGAÇÃO [valor, regex], regras POSITIVAS [valor, regex]).
# Negação na frase vence o positivo da mesma frase.
REGRAS: dict[str, tuple[list[tuple[str, str]], list[tuple[str, str]]]] = {
    "estoque": (
        [
            ("nenhum", rf"\bnao\s+{_W}{{0,2}}(?:movimenta|altera|afeta|atualiza|mexe|impacta)\w*\s+{_W}{{0,3}}estoque"),
            ("nenhum", rf"\b(?:sem|nao\s+(?:gera|tem|possui|ha|havera|tera|causa|existe))\s+{_W}{{0,2}}"
                       rf"(?:efeito|movimentac\w*|integrac\w*|impacto|alterac\w*)\s+{_W}{{0,3}}estoque"),
            ("nenhum", rf"\bestoque\s+{_W}{{0,2}}nao\s+(?:e|sera|sofre)\s+{_W}{{0,1}}(?:afetad|alterad|movimentad|atualizad|impactad)"),
            ("nenhum", r"\bestoque\s+(?:nenhum|nao\s+se\s+aplica|nao\s+aplicavel)\b"),
        ],
        [
            ("aumenta", rf"\b(?:entrada|aumenta\w*|increment\w*|acresc\w*|alimenta\w*|abastec\w*|soma\w*)\s+{_W}{{0,4}}?estoque"),
            ("aumenta", rf"\bestoque\s+{_W}{{0,3}}(?:aumenta|e\s+incrementad|e\s+acrescid|recebe)"),
            ("diminui", rf"\b(?:baixa\w*|saida|diminu\w*|reduz\w*|consum\w*|debit\w*|retira\w*)\s+{_W}{{0,4}}?estoque"),
            ("diminui", rf"\bestoque\s+{_W}{{0,3}}(?:diminu|reduz|e\s+baixad|e\s+consumid)"),
        ],
    ),
    "financeiro": (
        [
            ("nenhum", rf"{_NEG}\s+{_W}{{0,3}}(?:financeir|contas?\s+a\s+(?:pagar|receber)|titulos?\b|lancamentos?\s+financeir)"),
            ("nenhum", rf"\bfinanceir\w*\s+{_W}{{0,2}}nao\s+(?:e|sera)\s+(?:gerad|afetad|impactad)"),
            ("nenhum", r"\bfinanceir\w*\s+(?:nenhum|nao\s+se\s+aplica)\b"),
        ],
        [
            ("pagar", r"\bcontas?\s+a\s+pagar\b"),
            ("pagar", r"\btitulos?\s+a\s+pagar\b"),
            ("pagar", rf"\blancamentos?\s+{_W}{{0,2}}a\s+pagar\b"),
            ("pagar", rf"\bpagamentos?\s+{_W}{{0,2}}(?:ao|do|a|dos|aos)\s+fornecedor"),
            ("pagar", r"\bprovis\w+\s+(?:de\s+)?pagamento"),
            ("receber", r"\bcontas?\s+a\s+receber\b"),
            ("receber", r"\btitulos?\s+a\s+receber\b"),
            ("receber", rf"\blancamentos?\s+{_W}{{0,2}}a\s+receber\b"),
            ("receber", r"\bboletos?\b"),
            ("receber", rf"\brecebimentos?\s+{_W}{{0,2}}(?:do|dos|de)\s+clientes?"),
            ("gera", rf"\b(?:gera|gerar|geracao|integra\w*)\s+{_W}{{0,3}}financeir"),
            ("gera", r"\blancamentos?\s+financeir"),
        ],
    ),
    "escritura_fiscal": (
        [
            ("nao", rf"{_NEG}\s+{_W}{{0,3}}(?:integrac\w*|efeito|escritur\w*|impacto|reflexo)\s+{_W}{{0,1}}fisca"),
            ("nao", rf"\bnao\s+{_W}{{0,2}}escritur"),
            ("nao", rf"\bnao\s+(?:gera|emite|possui|tem|havera)\s+{_W}{{0,2}}(?:documento|nota)s?\s+fisca"),
            ("nao", rf"\bfiscal\s+(?:nenhum|nao\s+se\s+aplica)\b"),
        ],
        [
            ("sim", r"\bescritur\w*"),
            ("sim", r"\blivros?\s+fisca"),
            ("sim", rf"\bintegra\w*\s+{_W}{{0,3}}fiscal"),
            ("sim", rf"\bapurac\w+\s+{_W}{{0,2}}(?:icms|ipi|iss|pis|cofins|impostos?|tributos?)"),
            ("sim", r"\bsped\b"),
            # Imposto destacado/retido na nota: documento que vai para os livros.
            ("sim", r"\b(?:icms|ipi|iss|pis|cofins|csll|irrf|inss)\b"),
        ],
    ),
    "natureza": (
        [],
        [
            ("E", rf"\bnotas?\s+fisca\w*\s+{_W}{{0,2}}de\s+(?:entrada|compra)"),
            ("E", r"\bnf-?e?\s+de\s+(?:entrada|compra)"),
            ("E", r"\bdocumentos?\s+fisca\w*\s+de\s+entrada"),
            ("E", rf"\bnotas?\s+(?:fisca\w*\s+)?{_W}{{0,3}}?(?:do|dos|de)\s+fornecedor"),
            ("S", rf"\bnotas?\s+fisca\w*\s+{_W}{{0,2}}de\s+(?:saida|venda)"),
            ("S", r"\bnf-?e?\s+de\s+(?:saida|venda)"),
            ("S", r"\bdocumentos?\s+fisca\w*\s+de\s+saida"),
        ],
    ),
    "emite_nfe": (
        [
            ("nao", rf"\bnao\s+{_W}{{0,2}}(?:emite|emitir|emissao|transmit\w*)\s+{_W}{{0,3}}(?:nf-?e\b|nota\s+fiscal\s+eletronica)"),
        ],
        [
            ("sim", rf"\b(?:emite|emitir|emissao|emitida|transmit\w*|autoriza\w*)\s+{_W}{{0,4}}"
                    rf"(?:nf-?e\b|nota\s+fiscal\s+eletronica(?!\s+de\s+servico)|danfe)"),
            ("sim", r"\bsefaz\b"),
        ],
    ),
    "emite_nfse": (
        [
            ("nao", rf"\bnao\s+{_W}{{0,2}}(?:emite|emitir|emissao)\s+{_W}{{0,3}}nfs-?e"),
        ],
        [
            ("sim", rf"\b(?:emite|emitir|emissao|emitida|transmit\w*|gera|gerar)\s+{_W}{{0,4}}"
                    rf"(?:nfs-?e\b|rps\b|nota\s+fiscal\s+(?:eletronica\s+)?de\s+servico)"),
        ],
    ),
    "orcamento": (
        [
            ("nenhum", rf"{_NEG}\s+{_W}{{0,3}}(?:controle\s+)?orcament"),
        ],
        [
            ("estorna", rf"\bestorn\w*\s+{_W}{{0,4}}orcament"),
            ("estorna", rf"\borcament\w*\s+{_W}{{0,4}}estorn"),
            # "orçamento de venda / ao cliente" é proposta comercial, não orçamento.
            ("afeta", r"\borcament\w*\b(?!\s+(?:de\s+vendas?|ao\s+cliente|para\s+o\s+cliente|do\s+cliente))"),
            ("afeta", r"\bdotac\w+"),
            ("afeta", r"\bempenh\w*"),
        ],
    ),
    "contabiliza": (
        [
            ("nao", rf"{_NEG}\s+{_W}{{0,3}}contabiliz"),
            ("nao", rf"\bnao\s+{_W}{{0,3}}(?:lancamentos?|integrac\w*|eventos?)\s+contab"),
        ],
        [
            ("sim", r"\bcontabiliz\w*"),
            ("sim", r"\blancamentos?\s+contab"),
            ("sim", r"\beventos?\s+contab"),
            ("sim", rf"\bintegra\w*\s+{_W}{{0,3}}contab"),
        ],
    ),
    "aprovacao": (
        [
            ("nao", rf"{_NEG}\s+{_W}{{0,3}}(?:aprovac|alcada|necessidade\s+de\s+aprova)"),
        ],
        [
            ("sim", r"\baprova(?:c|r|d)\w*"),
            ("sim", r"\balcadas?\b"),
            ("sim", r"\bworkflow\b"),
            ("sim", r"\bfluig\b"),
        ],
    ),
    "gera_contrato": (
        [
            ("nao", rf"{_NEG}\s+{_W}{{0,3}}contrato"),
        ],
        [
            ("sim", rf"\b(?:gera|gerar|geracao|cria|criar|criacao|inclusao|cadastr\w*|formaliza\w*)\s+{_W}{{0,3}}contratos?\b"),
        ],
    ),
}

_COMPILADAS = {
    dim: ([(v, re.compile(p)) for v, p in neg], [(v, re.compile(p)) for v, p in pos])
    for dim, (neg, pos) in REGRAS.items()
}

# Campos do interpretador (Gem) viram frases com rótulo, para as mesmas regras.
ROTULOS_CAMPOS = {
    "EFEITO_ESTOQUE": "Efeito no estoque",
    "LOCAL_ORIGEM": "Local de origem",
    "LOCAL_DESTINO": "Local de destino",
    "EFEITO_FINANCEIRO": "Efeito financeiro",
    "FINANCEIRO": "Financeiro",
    "DOCUMENTO_FISCAL": "Documento fiscal",
    "OPERACAO_FISCAL": "Operação fiscal",
    "TRIBUTACAO": "Tributação",
    "RETENCOES": "Retenções",
    "ESCRITURACAO": "Escrituração",
    "OBSERVACAO_FISCAL": "Observação fiscal",
    "ORCAMENTO": "Orçamento",
    "CONTABILIZACAO": "Contabilização",
    "APROVACAO": "Aprovação",
    "PROCESSO_ORIGEM": "Processo de origem",
    "PROCESSO_DESTINO": "Processo de destino",
}

_VARIOS_POR_FRASE = {"estoque"}

_RE_FRASE = re.compile(r"(?<=[.;!?])\s+|\n+")
TAMANHO_TRECHO = 240


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, só letras/dígitos/hífen: 'NF-e: Emissão' -> 'nf-e emissao'."""
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9\-]+", " ", s).strip()


def frases(texto: str) -> list[str]:
    return [f.strip() for f in _RE_FRASE.split(texto or "") if f and f.strip()]


@dataclass
class Evidencia:
    valor: str
    trecho: str

    def para_dict(self) -> dict:
        return {"valor": self.valor, "trecho": self.trecho}


@dataclass
class Requisitos:
    evidencias: dict[str, list[Evidencia]] = field(default_factory=dict)

    def valores(self, dim: str) -> list[str]:
        vistos: list[str] = []
        for e in self.evidencias.get(dim, []):
            if e.valor not in vistos:
                vistos.append(e.valor)
        return vistos

    def valor(self, dim: str) -> str | None:
        """
        Valor resolvido da dimensão, ou None se a MIT não diz ou se contradiz.
        Casos de negócio: entrada E saída de estoque no mesmo movimento é
        transferência; "gera financeiro" sem direção perde para "a pagar"/"a receber".
        """
        v = set(self.valores(dim))
        if not v:
            return None
        if dim == "estoque" and {"aumenta", "diminui"} <= v:
            return "transfere"
        if dim == "financeiro" and "gera" in v and len(v - {"gera"}) == 1:
            v -= {"gera"}
        return v.pop() if len(v) == 1 else None

    def ambiguas(self) -> list[str]:
        return [d for d in self.evidencias if self.valor(d) is None]

    def para_dict(self) -> dict:
        return {
            "valores": {d: self.valor(d) for d in DIMENSOES},
            "ambiguas": self.ambiguas(),
            "evidencias": {
                d: [e.para_dict() for e in ev] for d, ev in self.evidencias.items()
            },
        }


def _trecho(frase: str) -> str:
    frase = re.sub(r"\s+", " ", frase).strip()
    return frase if len(frase) <= TAMANHO_TRECHO else frase[: TAMANHO_TRECHO - 1] + "…"


def extrair_requisitos(texto: str) -> Requisitos:
    """Requisitos de um movimento a partir de texto corrido (ex.: o TO BE)."""
    req = Requisitos()
    for frase in frases(texto):
        n = normalizar(frase)
        if not n:
            continue
        for dim, (negativas, positivas) in _COMPILADAS.items():
            achados = [v for v, rx in negativas if rx.search(n)][:1]
            if not achados:
                achados = list(dict.fromkeys(v for v, rx in positivas if rx.search(n)))
                # As regras positivas estão em ordem de especificidade: numa
                # frase, vale a primeira ("estorna o orçamento" não é também
                # "afeta"). Exceção: estoque, onde entrada + saída na mesma
                # frase é justamente a transferência.
                if dim not in _VARIOS_POR_FRASE:
                    achados = achados[:1]
            for valor in achados:
                req.evidencias.setdefault(dim, []).append(Evidencia(valor, _trecho(frase)))
    return req


def texto_de_campos(campos: dict[str, str]) -> str:
    """Campos do interpretador ("EFEITO_ESTOQUE=Aumenta") como frases com rótulo."""
    linhas = []
    for chave, valor in campos.items():
        if chave == "NOME_MOVIMENTO" or not valor:
            continue
        rotulo = ROTULOS_CAMPOS.get(chave, chave.replace("_", " ").capitalize())
        linhas.append(f"{rotulo}: {valor.strip().rstrip('.')}.")
    return "\n".join(linhas)


def extrair_requisitos_de_campos(campos: dict[str, str]) -> Requisitos:
    return extrair_requisitos(texto_de_campos(campos))


# --- Fluxo entre movimentos da mesma MIT ------------------------------------

_VERBOS_DESTINO = re.compile(
    r"\b(?:gera|gerar|gerad\w*|origina|dara\s+origem|da\s+origem|transforma\w*|convert\w*|"
    r"fatura\w*|segue\s+para|enviad\w*\s+para|encaminhad\w*|vira)\b"
)
_VERBOS_ORIGEM = re.compile(
    r"\b(?:a\s+partir\s+d\w*|originad\w*|proveniente\w*|vinculad\w*|com\s+base\s+n\w*|"
    r"recebid\w*\s+d\w*|apos|oriund\w*)\b"
)


def citacoes_de_movimentos(texto: str, titulos: dict[str, str]) -> list[dict]:
    """
    Outros movimentos da MESMA MIT citados no texto, com a direção provável:
    "destino" (este movimento gera/segue para o citado), "origem" (vem do
    citado) ou "citado". titulos = {numero: titulo}.
    """
    saida: dict[str, dict] = {}
    alvos = {num: normalizar(t) for num, t in titulos.items() if len(normalizar(t)) >= 6}
    for frase in frases(texto):
        n = normalizar(frase)
        for num, alvo in alvos.items():
            pos = n.find(alvo)
            if pos < 0 or num in saida:
                continue
            antes = n[:pos]
            if _VERBOS_ORIGEM.search(antes[-60:]):
                direcao = "origem"
            elif _VERBOS_DESTINO.search(antes[-60:]):
                direcao = "destino"
            else:
                direcao = "citado"
            saida[num] = {"numero": num, "titulo": titulos[num], "direcao": direcao, "trecho": _trecho(frase)}
    return list(saida.values())
