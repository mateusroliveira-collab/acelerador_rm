"""
Núcleo comum do gerador de payload de DataServer do RM.

A ferramenta SÓ gera e valida: não conecta ao RM, não guarda credencial e
não grava os valores digitados em lugar nenhum. Cada módulo (um
DataServer) descreve seus campos e como montar o payload; este arquivo
cuida do que é comum -- validação por tipo e serialização.

Pra criar um módulo novo: um subpacote em api/_lib/dataserver/<modulo>/
que exporta um `MODULO` (ver glb_usuario/) e o registro em registro.py.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable

# Tipos de campo aceitos
TEXTO, EMAIL, INTEIRO, BOOLEANO, DATA = "texto", "email", "inteiro", "booleano", "data"

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LIMITE_TEXTO_PADRAO = 255  # só um teto de sanidade; limites reais por campo, quando conhecidos


@dataclass(frozen=True)
class Campo:
    nome: str  # nome do campo no DataServer (ex.: CODUSUARIO)
    rotulo: str  # como aparece na tela do RM / do formulário
    tipo: str = TEXTO
    obrigatorio: bool = False
    padrao: Any = None
    ajuda: str = ""
    aba: str = "Identificação"
    tamanho_max: int | None = None
    # Como o booleano vai no payload: "01" -> 1/0, "TF" -> "T"/"F"
    formato_booleano: str = "01"

    def para_dict(self, opcoes: list | None = None) -> dict:
        return {
            "nome": self.nome, "rotulo": self.rotulo, "tipo": self.tipo,
            "obrigatorio": self.obrigatorio, "padrao": self.padrao,
            "ajuda": self.ajuda, "aba": self.aba, "tamanho_max": self.tamanho_max,
            "formato_booleano": self.formato_booleano if self.tipo == BOOLEANO else None,
            "opcoes": opcoes,  # lista fechada de valores válidos (config do cliente) ou None
        }

    def valores_booleanos(self) -> tuple[str, str]:
        """(sim, não) como o RM grava o campo: ("1", "0") ou ("T", "F")."""
        return ("T", "F") if self.formato_booleano == "TF" else ("1", "0")


@dataclass(frozen=True)
class Modulo:
    chave: str  # usada na URL (ex.: glb-usuario)
    nome: str
    dataserver: str  # nome do DataServer no RM (ex.: GlbUsuarioData)
    descricao: str
    campos: tuple[Campo, ...]
    operacoes: tuple[str, ...]
    # (valores normalizados, operacao) -> lista de erros extras {campo, mensagem}
    regras: Callable[[dict, str], list[dict]] = lambda valores, operacao: []
    # (valores normalizados, operacao) -> avisos (não bloqueiam)
    avisos: Callable[[dict, str], list[str]] = lambda valores, operacao: []
    # (payload, operacao) -> {"nome_arquivo": ..., "instrucoes": [...]}
    entrega: Callable[[dict, str], dict] = lambda payload, operacao: {}
    # Pontos do schema que ainda não foram confirmados contra o RM real.
    nao_validado: tuple[str, ...] = field(default_factory=tuple)
    # Campo que identifica o registro (usado pra achar repetidos no lote).
    campo_chave: str | None = None
    # Versão do schema do módulo: sobe quando campos/regras mudam. Vai nas
    # respostas e no log, pra rastrear com qual versão cada arquivo foi gerado.
    versao_schema: str = "1"
    # Nome da tabela no DataSet XML do RM (ex.: GUSUARIO); None = sem saída XML.
    tabela_xml: str | None = None
    # chave da config do cliente -> campo validado contra essa lista
    # (ex.: {"codigos_acesso": "CODACESSO"})
    listas_config: dict = field(default_factory=dict)
    # (operacao, nome_arquivo, total_validos) -> instruções de envio do lote
    entrega_lote: Callable[[str, str, int], list] = lambda operacao, nome_arquivo, total: []
    # Todas as chaves que o GET do DataServer devolve, NA ORDEM do GET. O JSON
    # de saída segue esse formato (campo fora do payload sai null). Vazio = só
    # os campos do schema.
    campos_saida: tuple[str, ...] = field(default_factory=tuple)
    # (payload) -> valor do "id" do GET (a chave primária do registro); None = sem "id".
    id_do_registro: Callable[[dict], Any] | None = None

    def para_dict(self, config: dict | None = None) -> dict:
        por_campo = {campo: chave for chave, campo in self.listas_config.items()}
        campos = []
        for c in self.campos:
            lista = (config or {}).get(por_campo.get(c.nome, ""))
            campos.append(c.para_dict(list(lista) if isinstance(lista, list) and lista else None))
        return {
            "chave": self.chave, "nome": self.nome, "dataserver": self.dataserver,
            "versao_schema": self.versao_schema, "campo_chave": self.campo_chave,
            "descricao": self.descricao, "operacoes": list(self.operacoes),
            "campos": campos,
            "nao_validado": list(self.nao_validado),
            "lote": True,
        }


def _vazio(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _como_booleano(v: Any) -> bool | None:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    if isinstance(v, str) and v.strip().lower() in ("true", "t", "1", "sim", "s"):
        return True
    if isinstance(v, str) and v.strip().lower() in ("false", "f", "0", "nao", "não", "n"):
        return False
    return None


def normalizar_e_validar(
    modulo: Modulo, valores: dict, operacao: str, config: dict | None = None
) -> tuple[dict, list[dict]]:
    """
    Converte o que veio do formulário pros tipos certos e valida campo a
    campo. Devolve (valores normalizados, erros). Campo vazio vira None.
    Campos desconhecidos são ignorados (o payload só leva campos do schema).
    """
    erros: list[dict] = []
    saida: dict[str, Any] = {}

    if operacao not in modulo.operacoes:
        return {}, [{"campo": "operacao", "mensagem": f"Operação inválida: {operacao!r}."}]

    for c in modulo.campos:
        bruto = valores.get(c.nome, c.padrao)
        if c.tipo == BOOLEANO:
            if _vazio(bruto):
                bruto = c.padrao
            b = _como_booleano(bruto)
            if b is None:
                erros.append({"campo": c.nome, "mensagem": f"{c.rotulo}: valor inválido."})
            saida[c.nome] = bool(b)
            continue

        if _vazio(bruto):
            if c.obrigatorio:
                erros.append({"campo": c.nome, "mensagem": f"{c.rotulo} é obrigatório."})
            saida[c.nome] = None
            continue

        if c.tipo in (TEXTO, EMAIL):
            texto = str(bruto).strip()
            limite = c.tamanho_max or LIMITE_TEXTO_PADRAO
            if len(texto) > limite:
                erros.append({"campo": c.nome, "mensagem": f"{c.rotulo}: máximo de {limite} caracteres."})
            if c.tipo == EMAIL and not _RE_EMAIL.match(texto):
                erros.append({"campo": c.nome, "mensagem": f"{c.rotulo}: e-mail inválido."})
            saida[c.nome] = texto
        elif c.tipo == INTEIRO:
            try:
                n = int(str(bruto).strip())
                if n < 0:
                    raise ValueError
                saida[c.nome] = n
            except ValueError:
                erros.append({"campo": c.nome, "mensagem": f"{c.rotulo}: informe um número inteiro positivo."})
                saida[c.nome] = None
        elif c.tipo == DATA:
            try:
                saida[c.nome] = (
                    bruto if isinstance(bruto, date)
                    else datetime.strptime(str(bruto).strip()[:10], "%Y-%m-%d").date()
                )
            except ValueError:
                erros.append({"campo": c.nome, "mensagem": f"{c.rotulo}: data inválida (use AAAA-MM-DD)."})
                saida[c.nome] = None

    if not erros:
        erros.extend(modulo.regras(saida, operacao))
        erros.extend(_validar_listas_config(modulo, saida, config))
    return saida, erros


def _validar_listas_config(modulo: Modulo, valores: dict, config: dict | None) -> list[dict]:
    """Valida campos contra as listas fechadas da config do cliente (se houver)."""
    erros = []
    rotulos = {c.nome: c.rotulo for c in modulo.campos}
    for chave_cfg, campo in modulo.listas_config.items():
        lista = (config or {}).get(chave_cfg)
        valor = valores.get(campo)
        if not isinstance(lista, list) or not lista or valor is None:
            continue
        if str(valor).strip().lower() not in {str(x).strip().lower() for x in lista}:
            erros.append({
                "campo": campo,
                "mensagem": f"{rotulos.get(campo, campo)}: \"{valor}\" não está na lista de valores do cliente.",
            })
    return erros


def valor_no_payload(campo: Campo, valor: Any, fuso: str) -> Any:
    """Serializa um valor normalizado pro formato do payload do RM."""
    if campo.tipo == BOOLEANO:
        if campo.formato_booleano == "TF":
            return "T" if valor else "F"
        return 1 if valor else 0
    if campo.tipo == DATA:
        return f"{valor.isoformat()}T00:00:00{fuso}"
    return valor


def registro_completo(modulo: Modulo, payload: dict) -> dict:
    """
    O registro no MESMO formato do GET do DataServer: todas as chaves, na ordem
    do GET, com null no que não está no payload (credenciais e campos
    controlados pelo RM sempre saem null).
    """
    if not modulo.campos_saida:
        return dict(payload)
    registro = {chave: payload.get(chave) for chave in modulo.campos_saida}
    if "id" in registro and modulo.id_do_registro:
        registro["id"] = modulo.id_do_registro(payload)
    return registro


def envelope_get(registros: list[dict]) -> dict:
    """Envelope da resposta do GET do REST do RM: {"messages", "length", "data"}."""
    return {"messages": [], "length": len(registros), "data": registros}
