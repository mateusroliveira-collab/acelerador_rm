#!/usr/bin/env python3
"""
Conector RM -- ponte LOCAL entre a tela do Acelerador e o RM do cliente.

Por que existe: o site roda na nuvem e não enxerga o RM, que normalmente
fica na rede interna do cliente. Este programa roda na máquina do analista
(que enxerga o RM) e repassa as chamadas GET/POST/PUT/DELETE da tela para o
REST do RM.

Segurança:
  - escuta só em 127.0.0.1 (nada de fora da máquina consegue falar com ele);
  - exige o CÓDIGO DE PAREAMENTO mostrado ao abrir (outro site aberto no
    navegador não consegue usá-lo);
  - só aceita chamadas do navegador vindas das origens informadas (--origem;
    aceita * dentro de um nome, para os endereços de deploy da Vercel, ex.:
    https://acelerador-*-minha-equipe.vercel.app);
  - só chama os endereços de RM informados ao abrir (--rm, uma ou mais
    bases com nome) e só nos caminhos permitidos (/rmsrestdataserver/ e
    /api/): não é um proxy aberto;
  - usuário e senha chegam a cada chamada, vão direto para o RM e NUNCA são
    gravados nem aparecem no log. O corpo das chamadas também não é logado.

Requisitos: Python 3.9+ (só biblioteca padrão, nada para instalar).

Uso:
  Dois cliques no arquivo (ou "python conector_rm.py" sem nada): pergunta o
  endereço do RM e do site na primeira vez e guarda em conector_rm_config.json,
  ao lado deste arquivo. Ou pelo comando montado na tela:
  python conector_rm.py --rm https://rm.cliente.com.br:8051 --origem https://SEU-APP.vercel.app
  Várias bases (a tela escolhe origem e destino pelo nome):
  python conector_rm.py --rm homolog=https://rm-hml:8051 --rm producao=https://rm:8051 --origem https://SEU-APP.vercel.app
  Opções: --porta 8765   --aceitar-certificado-autoassinado   --timeout 60   --novo-codigo

O CÓDIGO DE PAREAMENTO é gerado uma vez e guardado no mesmo arquivo: não muda
a cada abertura (use --novo-codigo para trocar). Ele também é copiado para a
área de transferência ao abrir.

Deixe a janela aberta enquanto usa as telas do Acelerador (Evento Contábil
Automático, Cadastro da GUSUARIO). Ctrl+C encerra.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSAO = "1.4.0"
PORTA_PADRAO = 8765
PREFIXOS_PERMITIDOS = ("/rmsrestdataserver/", "/api/")
METODOS = ("GET", "POST", "PUT", "DELETE")
MAX_CORPO_ENTRADA = 5_000_000  # bytes que a tela pode mandar numa chamada
MAX_CORPO_RESPOSTA = 2_000_000  # bytes da resposta do RM devolvidos à tela
MAX_REGISTROS_LOTE = 500
SEPARADOR_CHAVE = "$_$"  # chave composta no REST do RM (ex.: CODCOLIGADA$_$CODEVENTO = "1$_$1")
SE_EXISTIR = ("erro", "pular", "alterar")
SITE_PADRAO = "https://acelerador-rm.vercel.app"
# Configuração e código de pareamento guardados ao lado do conector (nunca senha).
ARQUIVO_CONFIG = Path(__file__).resolve().with_name("conector_rm_config.json")


@dataclass
class Config:
    rm: str  # https://host:porta (sem caminho) -- a base padrão
    token: str
    origens: tuple[str, ...] = ()
    aceitar_autoassinado: bool = False
    timeout: float = 60.0
    prefixos: tuple[str, ...] = PREFIXOS_PERMITIDOS
    log: list = field(default_factory=list)  # só para testes; o console recebe o mesmo texto
    # nome -> https://host:porta. Vazio = só a base `rm` (nome "principal").
    bases: dict = field(default_factory=dict)
    # Procura o RM instalado nesta máquina para mostrar o alias de cada base.
    detectar_local: bool = True

    def lista_bases(self) -> dict:
        return dict(self.bases) if self.bases else {"principal": self.rm}

    def url_da_base(self, nome: str | None) -> str:
        """Endereço da base pelo nome (vazio = padrão). Só bases abertas no conector."""
        if not nome:
            return self.rm
        bases = self.lista_bases()
        if nome not in bases:
            raise ErroConector(400, f"Base desconhecida: {nome}.",
                               "Use uma das bases abertas no conector: " + ", ".join(bases) + ".")
        return bases[nome]


class ErroConector(Exception):
    """Erro com mensagem para o analista e dica de como corrigir."""

    def __init__(self, status: int, mensagem: str, como_corrigir: str = ""):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem
        self.como_corrigir = como_corrigir

    def para_dict(self) -> dict:
        return {"ok": False, "erro": self.mensagem, "como_corrigir": self.como_corrigir}


# --- Validação de entrada -----------------------------------------------------


def _casa_curinga(valor: str, padrao: str) -> bool:
    """'*' casa letras, números e '-' (nunca '.', '/' ou ':'): fica dentro de um nome do endereço."""
    import re

    partes = [re.escape(p) for p in padrao.split("*")]
    return re.fullmatch("[a-z0-9-]+".join(partes), valor) is not None


def so_origem(endereco: str) -> str:
    """
    O navegador identifica o site só por protocolo + servidor (a "origem"):
    'https://site.vercel.app/gerador-dataserver?x=1' -> 'https://site.vercel.app'.
    Mantém o * dos curingas.
    """
    endereco = (endereco or "").strip()
    if not endereco:
        return ""
    if "://" not in endereco:
        endereco = "https://" + endereco
    esquema, _, resto = endereco.partition("://")
    servidor = resto.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    return f"{esquema.lower()}://{servidor.lower()}"


def origens_autorizadas(informadas: list[str]) -> tuple[str, ...]:
    """
    --origem informadas -> lista final: só a origem de cada endereço (sem
    caminho), mais o padrão dos deploys da Vercel e o site oficial.
    """
    saida: list[str] = []
    for o in informadas:
        for x in ([so_origem(o)] if "*" in o else origens_do_site(o)):
            if x and x not in saida:
                saida.append(x)
    return tuple(saida)


def origens_do_site(endereco: str) -> list[str]:
    """
    Endereço do site -> origens a autorizar. Endereço de deploy da Vercel
    (projeto-<9 letras>-equipe.vercel.app) muda a cada deploy: autoriza também
    projeto-*-equipe.vercel.app. Sempre inclui o site oficial.
    """
    import re

    endereco = so_origem(endereco)
    saida = [endereco] if endereco else []
    m = re.fullmatch(r"https://([a-z0-9-]+?)-[a-z0-9]{9}-([a-z0-9-]+)\.vercel\.app", endereco)
    if m:
        saida.append(f"https://{m.group(1)}-*-{m.group(2)}.vercel.app")
    if SITE_PADRAO not in saida:
        saida.append(SITE_PADRAO)
    return saida


def origem_autorizada(origem: str | None, origens: tuple[str, ...]) -> bool:
    """Origem (ex.: https://site.vercel.app) está na lista? Aceita * nos endereços da lista."""
    if not origem:
        return False
    origem = origem.rstrip("/").lower()
    for o in origens:
        o = o.rstrip("/").lower()
        if origem == o or ("*" in o and _casa_curinga(origem, o)):
            return True
    return False


def normalizar_rm(url: str) -> str:
    """'https://rm:8051/qualquer' -> 'https://rm:8051'. Lança ValueError se inválido."""
    p = urllib.parse.urlsplit((url or "").strip())
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Informe o endereço do RM com http:// ou https://, ex.: https://rm.cliente.com.br:8051")
    return f"{p.scheme}://{p.netloc}"


def montar_url(cfg: Config, caminho: str, parametros: dict | None = None, base: str | None = None) -> str:
    """Junta o RM configurado + caminho permitido + parâmetros. Só usa hosts abertos no conector."""
    caminho = (caminho or "").strip()
    if not caminho.startswith("/") or caminho.startswith("//") or "://" in caminho or "\\" in caminho:
        raise ErroConector(400, "Caminho inválido.", "Use um caminho do RM começando com /, ex.: /rmsrestdataserver/rest/GlbUsuarioData")
    partes = urllib.parse.urlsplit(caminho)
    segmentos = partes.path.split("/")
    if ".." in segmentos or not any(partes.path.startswith(p) for p in cfg.prefixos):
        raise ErroConector(
            403, "Caminho não permitido pelo conector.",
            "O conector só chama " + " ou ".join(cfg.prefixos) + " no RM informado ao abrir.",
        )
    query = urllib.parse.parse_qsl(partes.query, keep_blank_values=True)
    for chave, valor in (parametros or {}).items():
        if valor not in (None, ""):
            query.append((str(chave), str(valor)))
    url = cfg.url_da_base(base) + urllib.parse.quote(partes.path, safe="/;:@=,$-_.!~*'()%")
    # Espaço vira %20 (não "+"): mais seguro com o filtro do REST do RM.
    return url + ("?" + urllib.parse.urlencode(query, quote_via=urllib.parse.quote) if query else "")


# --- Chamada ao RM ------------------------------------------------------------


def _contexto_ssl(cfg: Config, url: str) -> ssl.SSLContext | None:
    if not url.startswith("https://"):
        return None
    if cfg.aceitar_autoassinado:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()


def _ler_corpo(dados: bytes) -> tuple[object, bool]:
    truncado = len(dados) > MAX_CORPO_RESPOSTA
    dados = dados[:MAX_CORPO_RESPOSTA]
    texto = dados.decode("utf-8", errors="replace")
    if not truncado:
        try:
            return json.loads(texto), False
        except ValueError:
            pass
    return texto, truncado


def traduzir_erro_rede(exc: BaseException, cfg: Config) -> ErroConector:
    """Erro de rede -> mensagem em português + como corrigir."""
    motivo = getattr(exc, "reason", exc)
    if isinstance(motivo, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(motivo):
        return ErroConector(
            502, "O certificado HTTPS do RM não é confiável para esta máquina.",
            "Se o RM usa certificado próprio (autoassinado), feche o conector e abra de novo com "
            "--aceitar-certificado-autoassinado. Se não deveria ser, avise a TI do cliente.",
        )
    if isinstance(motivo, ssl.SSLError):
        return ErroConector(502, "Falha no HTTPS com o RM.", "Confira se a porta é HTTPS mesmo (talvez seja http://).")
    if isinstance(motivo, (socket.timeout, TimeoutError)) or "timed out" in str(motivo):
        return ErroConector(504, f"O RM não respondeu em {int(cfg.timeout)} s.",
                            "Confira VPN/rede e se o serviço do RM (Host/REST) está no ar. Para lotes grandes, aumente --timeout.")
    if isinstance(motivo, socket.gaierror):
        return ErroConector(502, "Não encontrei o endereço do RM.",
                            "Confira o nome do servidor em --rm e se a VPN do cliente está conectada.")
    if isinstance(motivo, ConnectionRefusedError) or "refused" in str(motivo).lower():
        return ErroConector(502, "O RM recusou a conexão.",
                            "Confira a porta em --rm (a do REST/Host do RM) e se o serviço está no ar.")
    return ErroConector(502, f"Não consegui falar com o RM: {motivo}", "Confira o endereço em --rm, a VPN e o firewall.")


DICAS_HTTP = {
    401: "Usuário ou senha do RM incorretos, ou usuário sem acesso ao REST.",
    403: "O usuário não tem permissão para esta operação/DataServer no RM (perfil de acesso).",
    404: "Caminho ou registro não encontrado: confira o nome do DataServer e a chave.",
    405: "O RM não aceita este método neste caminho.",
    500: "Erro interno do RM: veja a mensagem devolvida (costuma dizer o campo ou a regra que falhou).",
}


def chamar_rm(cfg: Config, metodo: str, caminho: str, usuario: str, senha: str,
              corpo: object = None, parametros: dict | None = None, base: str | None = None) -> dict:
    metodo = (metodo or "").upper()
    if metodo not in METODOS:
        raise ErroConector(400, f"Método inválido: {metodo}.", "Use GET, POST, PUT ou DELETE.")
    if not usuario or senha is None:
        raise ErroConector(400, "Informe usuário e senha do RM.", "Eles vão direto para o RM e não são guardados.")
    url = montar_url(cfg, caminho, parametros, base)

    dados = None
    cabecalhos = {
        "Accept": "application/json",
        "Authorization": "Basic " + base64.b64encode(f"{usuario}:{senha}".encode("utf-8")).decode("ascii"),
    }
    if corpo is not None and metodo in ("POST", "PUT"):
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        cabecalhos["Content-Type"] = "application/json; charset=utf-8"

    req = urllib.request.Request(url, data=dados, method=metodo, headers=cabecalhos)
    inicio = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout, context=_contexto_ssl(cfg, url)) as resp:
            status, bruto, tipo = resp.status, resp.read(MAX_CORPO_RESPOSTA + 1), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        status, bruto, tipo = e.code, e.read(MAX_CORPO_RESPOSTA + 1), e.headers.get("Content-Type", "") if e.headers else ""
    except (urllib.error.URLError, OSError) as e:
        raise traduzir_erro_rede(e, cfg) from None
    ms = int((time.monotonic() - inicio) * 1000)

    corpo_resp, truncado = _ler_corpo(bruto)
    rotulo_base = f"[{base}] " if base else ""
    _log(cfg, f"{rotulo_base}{metodo} {urllib.parse.urlsplit(url).path} -> {status} ({ms} ms)")
    return {
        "ok": 200 <= status < 300,
        "status": status,
        "tempo_ms": ms,
        "content_type": tipo,
        "corpo": corpo_resp,
        "truncado": truncado,
        "dica": None if 200 <= status < 300 else DICAS_HTTP.get(status, "Veja a mensagem devolvida pelo RM."),
    }


def chave_do_registro(reg: object, campo_chave: str | None) -> str:
    """
    Valor da chave para a URL. campo_chave pode ser composto ("CODCOLIGADA,CODEVENTO"):
    os valores são unidos com $_$, como o RM faz ("1$_$1"). Falta algum -> "".
    """
    if not isinstance(reg, dict) or not campo_chave:
        return ""
    valores = []
    for campo in (c.strip() for c in campo_chave.split(",") if c.strip()):
        v = reg.get(campo)
        if v is None or str(v).strip() == "":
            return ""
        valores.append(str(v).strip())
    return SEPARADOR_CHAVE.join(valores)


def _existe(resposta: dict) -> bool:
    """GET pela chave achou o registro? (o RM devolve {"data": {...}} ou {"data": [...]})"""
    if not resposta.get("ok"):
        return False
    corpo = resposta.get("corpo")
    if isinstance(corpo, dict) and "data" in corpo:
        return bool(corpo["data"])
    return bool(corpo)


def enviar_lote(cfg: Config, metodo: str, caminho: str, registros: list, usuario: str, senha: str,
                campo_chave: str | None = None, parar_no_erro: bool = False,
                base: str | None = None, se_existir: str = "erro") -> dict:
    """
    Um registro por chamada (o REST DataServer recebe um por vez). PUT usa
    caminho/<chave>. Em POST, `se_existir` decide o que fazer com registro que
    já está no RM (consulta antes pela chave): "erro" (manda o POST mesmo),
    "pular" ou "alterar" (manda PUT). Devolve o resultado de cada registro.
    """
    metodo = (metodo or "").upper()
    se_existir = se_existir or "erro"
    if metodo not in ("POST", "PUT"):
        raise ErroConector(400, "Lote só com POST (incluir) ou PUT (alterar).")
    if se_existir not in SE_EXISTIR:
        raise ErroConector(400, f"Opção inválida para registro existente: {se_existir}.")
    if not isinstance(registros, list) or not registros:
        raise ErroConector(400, "Nenhum registro no lote.")
    if len(registros) > MAX_REGISTROS_LOTE:
        raise ErroConector(400, f"Lote com mais de {MAX_REGISTROS_LOTE} registros.", "Divida o arquivo em partes.")
    precisa_chave = metodo == "PUT" or se_existir != "erro"
    if precisa_chave and not campo_chave:
        raise ErroConector(400, "Informe o campo chave (ex.: CODUSUARIO ou CODCOLIGADA,CODEVENTO).")
    cfg.url_da_base(base)  # base desconhecida: recusa antes de chamar qualquer coisa

    resultados = []
    raiz = caminho.rstrip("/")
    for i, reg in enumerate(registros, start=1):
        chave = chave_do_registro(reg, campo_chave) if campo_chave else ""
        if precisa_chave and not chave:
            resultados.append({"indice": i, "chave": None, "ok": False, "status": None, "acao": None,
                               "erro": f"Registro sem {campo_chave}."})
            if parar_no_erro:
                break
            continue
        url_chave = f"{raiz}/{urllib.parse.quote(chave, safe='$_')}" if chave else raiz
        try:
            metodo_reg, acao = metodo, ("alterado" if metodo == "PUT" else "incluido")
            if metodo == "POST" and se_existir != "erro":
                if _existe(chamar_rm(cfg, "GET", url_chave, usuario, senha, base=base)):
                    if se_existir == "pular":
                        resultados.append({"indice": i, "chave": chave, "ok": True, "status": None,
                                           "acao": "pulado", "resposta": "Já existe no RM: não foi enviado."})
                        continue
                    metodo_reg, acao = "PUT", "alterado"
            r = chamar_rm(cfg, metodo_reg, url_chave if metodo_reg == "PUT" else raiz, usuario, senha,
                          corpo=reg, base=base)
            item = {"indice": i, "chave": chave or None, "ok": r["ok"], "status": r["status"],
                    "acao": acao if r["ok"] else None, "resposta": r["corpo"], "dica": r["dica"]}
        except ErroConector as e:
            item = {"indice": i, "chave": chave or None, "ok": False, "status": None, "acao": None,
                    "erro": e.mensagem, "como_corrigir": e.como_corrigir}
            resultados.append(item)
            if e.status in (502, 504):  # RM fora do ar: não adianta continuar
                break
            if parar_no_erro:
                break
            continue
        resultados.append(item)
        if parar_no_erro and not item["ok"]:
            break
    enviados = len(resultados)
    sucesso = sum(1 for r in resultados if r["ok"])
    return {"total": len(registros), "enviados": enviados, "sucesso": sucesso,
            "falhas": enviados - sucesso, "nao_enviados": len(registros) - enviados,
            "pulados": sum(1 for r in resultados if r.get("acao") == "pulado"), "resultados": resultados}


# --- Servidor local -----------------------------------------------------------


def _log(cfg: Config, texto: str) -> None:
    linha = time.strftime("%H:%M:%S ") + texto
    cfg.log.append(linha)
    print(linha, flush=True)


def criar_servidor(cfg: Config, porta: int = PORTA_PADRAO) -> ThreadingHTTPServer:
    origens_avisadas: set = set()

    class Handler(BaseHTTPRequestHandler):
        server_version = f"ConectorRM/{VERSAO}"

        def log_message(self, *args):  # silencia o log padrão (teria caminho/cliente)
            pass

        def _origem_permitida(self) -> str | None:
            origem = self.headers.get("Origin")
            if origem_autorizada(origem, cfg.origens):
                return origem
            if origem and origem not in origens_avisadas:  # avisa na janela uma vez por site
                origens_avisadas.add(origem)
                _log(cfg, f"RECUSADO: o site {origem} não está autorizado. Este conector foi aberto para: "
                          f"{', '.join(cfg.origens)}. Baixe o atalho abrir_conector.bat pela tela de {origem} "
                          "(ou apague conector_rm_config.json e abra de novo informando esse endereço).")
            return None

        def _cors(self) -> None:
            origem = self._origem_permitida()
            if origem:
                self.send_header("Access-Control-Allow-Origin", origem)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Conector-Token")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                # Chrome: site público chamando a rede local precisa desta permissão.
                self.send_header("Access-Control-Allow-Private-Network", "true")
                self.send_header("Access-Control-Max-Age", "600")

        def _responder(self, status: int, dados: dict) -> None:
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _checar_acesso(self) -> bool:
            if self.headers.get("Origin") and not self._origem_permitida():
                self._responder(403, ErroConector(
                    403, "Origem não autorizada.",
                    "Abra o conector com --origem igual ao endereço do site (copie o comando pela tela).",
                ).para_dict())
                return False
            if not secrets.compare_digest(self.headers.get("X-Conector-Token", ""), cfg.token):
                self._responder(401, {**ErroConector(
                    401, "Código de pareamento inválido.",
                    "Copie o código mostrado na janela do conector para a tela.",
                ).para_dict(), "conector": True})
                return False
            return True

        def do_OPTIONS(self):  # noqa: N802 (nome exigido pelo http.server)
            self.send_response(204 if self._origem_permitida() else 403)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _ping(self) -> None:
            """
            Diagnóstico para a tela: responde a qualquer site (sem código) só
            "sou o conector, versão X, e aceito/não aceito o seu endereço". Não
            revela bases, endereços autorizados nem o código.
            """
            origem = self.headers.get("Origin")
            corpo = json.dumps({"conector": True, "versao": VERSAO,
                                "origem_autorizada": bool(self._origem_permitida())}).encode("utf-8")
            self.send_response(200)
            if origem:
                self.send_header("Access-Control-Allow-Origin", origem)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):  # noqa: N802
            rota = self.path.split("?")[0]
            if rota == "/ping":
                return self._ping()
            if rota != "/status":
                return self._responder(404, {"ok": False, "erro": "Rota inexistente."})
            if not self._checar_acesso():
                return
            rm_local = detectar_rm_local() if cfg.detectar_local else []
            bases = [{"nome": n, "rm": u, "alias": alias_da_base(u, rm_local)} for n, u in cfg.lista_bases().items()]
            self._responder(200, {"ok": True, "conector": True, "versao": VERSAO, "rm": cfg.rm,
                                  "bases": bases, "aceita_autoassinado": cfg.aceitar_autoassinado,
                                  "rm_local": [{k: r[k] for k in ("endereco", "alias", "instalacao", "servico", "no_ar")}
                                               for r in rm_local]})

        def do_POST(self):  # noqa: N802
            rota = self.path.split("?")[0]
            if rota not in ("/rm", "/rm/lote"):
                return self._responder(404, {"ok": False, "erro": "Rota inexistente."})
            if not self._checar_acesso():
                return
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                tamanho = -1
            if tamanho < 0 or tamanho > MAX_CORPO_ENTRADA:
                return self._responder(413, ErroConector(413, "Chamada grande demais.").para_dict())
            try:
                pedido = json.loads(self.rfile.read(tamanho) or b"{}")
                if not isinstance(pedido, dict):
                    raise ValueError
            except ValueError:
                return self._responder(400, ErroConector(400, "Corpo da chamada não é JSON válido.").para_dict())
            try:
                if rota == "/rm":
                    r = chamar_rm(cfg, pedido.get("metodo"), pedido.get("caminho"), pedido.get("usuario"),
                                  pedido.get("senha"), pedido.get("corpo"), pedido.get("parametros"),
                                  pedido.get("base"))
                else:
                    r = enviar_lote(cfg, pedido.get("metodo"), pedido.get("caminho"), pedido.get("registros"),
                                    pedido.get("usuario"), pedido.get("senha"), pedido.get("campo_chave"),
                                    bool(pedido.get("parar_no_erro")), pedido.get("base"),
                                    pedido.get("se_existir") or "erro")
                    _log(cfg, f"lote {pedido.get('metodo')}: {r['sucesso']}/{r['total']} com sucesso")
            except ErroConector as e:
                _log(cfg, f"recusado: {e.mensagem}")
                return self._responder(e.status, e.para_dict())
            self._responder(200, r)

    return ThreadingHTTPServer(("127.0.0.1", porta), Handler)


def ler_bases(valores: list[str]) -> dict:
    """["homolog=https://a:1", "https://b:2"] -> {"homolog": "https://a:1", "principal": "https://b:2"}."""
    bases: dict = {}
    for i, valor in enumerate(valores, start=1):
        nome, _, url = valor.partition("=") if "=" in valor.split("://")[0] else ("", "", valor)
        nome = nome.strip() or ("principal" if len(valores) == 1 else f"base{i}")
        if not nome.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Nome de base inválido: {nome!r} (use letras, números, - e _).")
        if nome in bases:
            raise ValueError(f"Base repetida: {nome}.")
        bases[nome] = normalizar_rm(url)
    return bases


# --- RM instalado nesta máquina ----------------------------------------------


def _pastas_totvs() -> list[Path]:
    if sys.platform != "win32":
        return []
    unidade = os.environ.get("SystemDrive", "C:")
    return [Path(unidade + "\\") / "totvs"]


def _porta_aberta(porta: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=0.3):
            return True
    except OSError:
        return False


def detectar_rm_local(raizes: list[Path] | None = None) -> list[dict]:
    """
    Procura o RM instalado (RM.Host*.exe.config em <raiz>/*/RM.Net) e devolve,
    por serviço: porta HTTP (REST), alias (DefaultDB) e se está no ar. Lê só
    essas duas chaves -- nada de string de conexão ou senha.
    """
    import re

    achados: list[dict] = []
    portas_vistas: set = set()
    for raiz in (_pastas_totvs() if raizes is None else raizes):
        try:
            arquivos = list(raiz.glob("*/RM.Net/RM.Host*.exe.config")) + list(raiz.glob("RM.Net/RM.Host*.exe.config"))
        except OSError:
            continue
        # Por instalação (pasta); em cada uma, o serviço principal (RM.Host.Service) primeiro.
        arquivos.sort(key=lambda a: (a.parent.parent.name.lower(), a.name != "RM.Host.Service.exe.config", a.name))
        for arq in arquivos:
            try:
                texto = arq.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            porta = re.search(r'key="HTTPPort"\s+value="(\d+)"', texto, re.I)
            alias = re.search(r'key="DefaultDB"\s+value="([^"]*)"', texto, re.I)
            if not porta or int(porta.group(1)) in portas_vistas:
                continue
            portas_vistas.add(int(porta.group(1)))
            achados.append({
                "instalacao": arq.parent.parent.name,
                "servico": arq.name.removesuffix(".exe.config"),
                "endereco": f"http://localhost:{porta.group(1)}",
                "porta": int(porta.group(1)),
                "alias": alias.group(1) if alias else None,
                "no_ar": _porta_aberta(int(porta.group(1))),
            })
    return achados


def sugerir_bases(rm_local: list[dict]) -> list[str]:
    """
    Uma base por instalação no ar ("nome=endereço"), pelo serviço principal.
    As outras instâncias da mesma instalação (Service1, 2...) são o mesmo banco.
    """
    saida, instalacoes = [], set()
    for r in rm_local:
        if not r["no_ar"] or r["instalacao"] in instalacoes:
            continue
        instalacoes.add(r["instalacao"])
        nome = _re_nome(r["instalacao"])
        saida.append(f"{nome}={r['endereco']}")
    return saida


def _re_nome(texto: str) -> str:
    import re

    nome = re.sub(r"[^a-z0-9_-]+", "-", texto.lower()).strip("-")
    return nome or "rm"


def alias_da_base(url: str, rm_local: list[dict]) -> str | None:
    """Alias (DefaultDB) de uma base que aponta para um RM desta máquina."""
    partes = urllib.parse.urlsplit(url)
    if (partes.hostname or "").lower() not in ("localhost", "127.0.0.1", "::1"):
        return None
    for r in rm_local:
        if r["porta"] == partes.port:
            return r["alias"]
    return None


# --- Configuração guardada e modo "dois cliques" ------------------------------


def ler_config(arquivo: Path | None = None) -> dict:
    try:
        dados = json.loads((arquivo or ARQUIVO_CONFIG).read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def salvar_config(dados: dict, arquivo: Path | None = None) -> None:
    try:
        (arquivo or ARQUIVO_CONFIG).write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # pasta sem permissão de escrita: segue sem guardar


def codigo_de_pareamento(novo: bool = False, arquivo: Path | None = None) -> str:
    """Código guardado (não muda a cada abertura); gera e guarda se não houver ou se novo=True."""
    dados = ler_config(arquivo)
    codigo = str(dados.get("codigo") or "")
    if novo or len(codigo) != 8 or not all(c in "0123456789ABCDEF" for c in codigo):
        codigo = secrets.token_hex(4).upper()
        salvar_config({**dados, "codigo": codigo}, arquivo)
    return codigo


def copiar_para_area_de_transferencia(texto: str) -> bool:
    comandos = {"win32": ["clip"], "darwin": ["pbcopy"]}.get(sys.platform)
    if not comandos:
        return False
    try:
        subprocess.run(comandos, input=texto.encode("utf-8"), check=True, timeout=5,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _perguntar(texto: str, padrao: str = "") -> str:
    resposta = input(f"{texto}{f' [{padrao}]' if padrao else ''}: ").strip()
    return resposta or padrao


def perguntar_argumentos(arquivo: Path | None = None, origens: list[str] | None = None) -> list[str]:
    """
    Modo dois cliques: usa a configuração guardada ou pergunta e guarda.
    `origens`: endereço(s) do site já informados (ex.: pelo atalho .bat) -- aí não pergunta o site.
    """
    dados = ler_config(arquivo)
    if origens:
        dados = {**dados, "origem": list(origens_autorizadas(origens))}
    bases = [b for b in dados.get("bases", []) if isinstance(b, str) and b.strip()]
    print(f"Conector RM {VERSAO}\n")
    if bases:
        print("Configuração guardada:")
        for b in bases:
            print(f"  Base: {b}")
        print(f"  Site: {', '.join(dados.get('origem') or [SITE_PADRAO])}\n")
        if _perguntar("Usar esta configuração? (S/n)", "S").lower().startswith("s"):
            return _argumentos(dados)
    locais = detectar_rm_local()
    sugestao = sugerir_bases(locais)
    if sugestao:
        print("Encontrei o RM instalado neste computador:")
        for b in sugestao:
            nome, _, url = b.partition("=")
            r = next(x for x in locais if x["endereco"] == url)
            alias = r["alias"] or "padrão da instalação"
            print(f"  {nome:<16} {url:<24} alias {alias}  (pasta {r['instalacao']})")
        texto = "Usar estas bases?" if len(sugestao) > 1 else "Usar esta base?"
        if _perguntar(f"{texto} (S/n)", "S").lower().startswith("s"):
            bases = sugestao
            dados = {**dados, "bases": bases, "origem": _origens_ou_pergunta(dados, origens), "autoassinado": False}
            salvar_config(dados, arquivo)
            print(f"\nConfiguração guardada em {(arquivo or ARQUIVO_CONFIG).name} (na próxima vez é só dar dois cliques).\n")
            return _argumentos(dados)
        print()
    print("Endereço do RM (o do REST/Host, ex.: https://rm.cliente.com.br:8051).")
    print("Para mais de uma base, use nome=endereço (ex.: homolog=https://rm-hml:8051).")
    bases = []
    while True:
        b = _perguntar(f"Base {len(bases) + 1}" + (" (Enter para terminar)" if bases else ""))
        if not b:
            if bases:
                break
            continue
        try:
            ler_bases([b])
        except ValueError as e:
            print(f"  {e}")
            continue
        bases.append(b)
    origem = _origens_ou_pergunta(dados, origens)
    autoassinado = _perguntar("O RM usa certificado HTTPS próprio (autoassinado)? (s/N)", "N").lower().startswith("s")
    dados = {**dados, "bases": bases, "origem": origem, "autoassinado": autoassinado}
    salvar_config(dados, arquivo)
    print(f"\nConfiguração guardada em {(arquivo or ARQUIVO_CONFIG).name} (na próxima vez é só dar dois cliques).\n")
    return _argumentos(dados)


def _origens_ou_pergunta(dados: dict, origens: list[str] | None) -> list[str]:
    if origens:
        return list(origens_autorizadas(origens))
    origem = so_origem(_perguntar("Endereço do site do Acelerador (pode colar o link da página)",
                                  (dados.get("origem") or [SITE_PADRAO])[0]))
    return origens_do_site(origem)


def _argumentos(dados: dict) -> list[str]:
    argv: list[str] = []
    for b in dados.get("bases", []):
        argv += ["--rm", b]
    for o in dados.get("origem") or [SITE_PADRAO]:
        argv += ["--origem", o]
    if dados.get("porta"):
        argv += ["--porta", str(dados["porta"])]
    if dados.get("autoassinado"):
        argv.append("--aceitar-certificado-autoassinado")
    return argv


def main(argv: list[str] | None = None, arquivo_config: Path | None = None) -> int:
    ap = argparse.ArgumentParser(description="Conector local entre o Acelerador e o RM.")
    ap.add_argument("--rm", required=True, action="append",
                    help="Endereço do RM, ex.: https://rm.cliente.com.br:8051. Para várias bases, repita com "
                         "nome=endereço: --rm homolog=https://rm-hml:8051 --rm producao=https://rm:8051")
    ap.add_argument("--origem", action="append", default=[],
                    help="Endereço do site do Acelerador (pode repetir). Ex.: https://SEU-APP.vercel.app")
    ap.add_argument("--porta", type=int, default=PORTA_PADRAO)
    ap.add_argument("--timeout", type=float, default=60.0, help="Segundos de espera por chamada ao RM.")
    ap.add_argument("--aceitar-certificado-autoassinado", action="store_true",
                    help="Aceita HTTPS com certificado próprio do cliente (não verifica o certificado).")
    ap.add_argument("--novo-codigo", action="store_true", help="Gera um código de pareamento novo.")
    a = ap.parse_args(argv)

    try:
        bases = ler_bases(a.rm)
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2
    origens = origens_autorizadas(a.origem) or ("http://localhost:3000",)
    cfg = Config(rm=next(iter(bases.values())), token=codigo_de_pareamento(a.novo_codigo, arquivo_config),
                 origens=origens, aceitar_autoassinado=a.aceitar_certificado_autoassinado, timeout=a.timeout,
                 bases=bases)
    try:
        servidor = criar_servidor(cfg, a.porta)
    except OSError:
        print(f"Erro: a porta {a.porta} já está em uso (o conector já está aberto em outra janela?). "
              "Feche a outra janela ou use --porta com outro número.", file=sys.stderr)
        return 2

    print(f"Conector RM {VERSAO}")
    for nome, url in cfg.lista_bases().items():
        print(f"  Base:    {nome} = {url}")
    print(f"  Site:    {', '.join(cfg.origens)}")
    print(f"  Porta:   {a.porta} (só esta máquina)")
    if cfg.aceitar_autoassinado:
        print("  AVISO:   certificado HTTPS do RM NÃO será verificado (--aceitar-certificado-autoassinado).")
    copiado = copiar_para_area_de_transferencia(cfg.token)
    print()
    print("  " + "=" * 44)
    print(f"     CÓDIGO DE PAREAMENTO:   {cfg.token}")
    print("  " + "=" * 44)
    print("  " + ("Já copiado: é só colar (Ctrl+V) na tela do Acelerador." if copiado
                  else "Digite este código na tela do Acelerador."))
    print("  O código fica guardado e não muda a cada abertura.")
    print()
    print("Deixe esta janela aberta. Senhas não são gravadas nem exibidas. Ctrl+C para encerrar.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nConector encerrado.")
    finally:
        servidor.server_close()
    return 0


def _separar_origens(args: list[str]) -> tuple[list[str], list[str]]:
    """(valores de --origem, demais argumentos)."""
    origens, resto, i = [], [], 0
    while i < len(args):
        if args[i] == "--origem" and i + 1 < len(args):
            origens.append(args[i + 1])
            i += 2
            continue
        if args[i].startswith("--origem="):
            origens.append(args[i].split("=", 1)[1])
        else:
            resto.append(args[i])
        i += 1
    return origens, resto


def iniciar(args: list[str] | None = None) -> int:
    """
    Ponto de entrada. Sem --rm (dois cliques, ou o atalho sem bases): descobre
    ou pergunta as bases, e não deixa a janela sumir em erro.
    """
    args = sys.argv[1:] if args is None else args
    if any(a == "--rm" or a.startswith("--rm=") or a in ("-h", "--help") for a in args):
        return main(args)
    try:
        origens, resto = _separar_origens(args)
        codigo = main(perguntar_argumentos(origens=origens or None) + resto)
    except KeyboardInterrupt:
        return 1
    except EOFError:
        print("\nA janela não recebeu a resposta. Abra o conector com dois cliques (ou pelo abrir_conector.bat).")
        return 1
    except Exception as e:  # noqa: BLE001 -- mostrar qualquer erro antes de a janela fechar
        print(f"\nErro inesperado: {e}")
        codigo = 1
    if codigo != 0 and os.environ.get("CONECTOR_SEM_PAUSA") != "1":
        try:
            input("\nPressione Enter para fechar esta janela...")
        except (EOFError, KeyboardInterrupt):
            pass
    return codigo


if __name__ == "__main__":
    sys.exit(iniciar())
