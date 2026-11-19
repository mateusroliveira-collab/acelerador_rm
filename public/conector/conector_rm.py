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
  - só aceita chamadas do navegador vindas das origens informadas (--origem);
  - só chama o endereço do RM informado ao abrir (--rm) e só nos caminhos
    permitidos (/rmsrestdataserver/ e /api/): não é um proxy aberto;
  - usuário e senha chegam a cada chamada, vão direto para o RM e NUNCA são
    gravados nem aparecem no log. O corpo das chamadas também não é logado.

Requisitos: Python 3.9+ (só biblioteca padrão, nada para instalar).

Uso:
  python conector_rm.py --rm https://rm.cliente.com.br:8051 --origem https://SEU-APP.vercel.app
  Opções: --porta 8765   --aceitar-certificado-autoassinado   --timeout 60

Deixe a janela aberta enquanto usa a tela "Conector RM". Ctrl+C encerra.
"""

from __future__ import annotations

import argparse
import base64
import json
import secrets
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSAO = "1.0.0"
PORTA_PADRAO = 8765
PREFIXOS_PERMITIDOS = ("/rmsrestdataserver/", "/api/")
METODOS = ("GET", "POST", "PUT", "DELETE")
MAX_CORPO_ENTRADA = 5_000_000  # bytes que a tela pode mandar numa chamada
MAX_CORPO_RESPOSTA = 2_000_000  # bytes da resposta do RM devolvidos à tela
MAX_REGISTROS_LOTE = 500


@dataclass
class Config:
    rm: str  # https://host:porta (sem caminho)
    token: str
    origens: tuple[str, ...] = ()
    aceitar_autoassinado: bool = False
    timeout: float = 60.0
    prefixos: tuple[str, ...] = PREFIXOS_PERMITIDOS
    log: list = field(default_factory=list)  # só para testes; o console recebe o mesmo texto


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


def normalizar_rm(url: str) -> str:
    """'https://rm:8051/qualquer' -> 'https://rm:8051'. Lança ValueError se inválido."""
    p = urllib.parse.urlsplit((url or "").strip())
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Informe o endereço do RM com http:// ou https://, ex.: https://rm.cliente.com.br:8051")
    return f"{p.scheme}://{p.netloc}"


def montar_url(cfg: Config, caminho: str, parametros: dict | None = None) -> str:
    """Junta o RM configurado + caminho permitido + parâmetros. Nunca troca o host."""
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
    url = cfg.rm + urllib.parse.quote(partes.path, safe="/;:@=,$-_.!~*'()%")
    # Espaço vira %20 (não "+"): mais seguro com o filtro do REST do RM.
    return url + ("?" + urllib.parse.urlencode(query, quote_via=urllib.parse.quote) if query else "")


# --- Chamada ao RM ------------------------------------------------------------


def _contexto_ssl(cfg: Config) -> ssl.SSLContext | None:
    if not cfg.rm.startswith("https://"):
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
              corpo: object = None, parametros: dict | None = None) -> dict:
    metodo = (metodo or "").upper()
    if metodo not in METODOS:
        raise ErroConector(400, f"Método inválido: {metodo}.", "Use GET, POST, PUT ou DELETE.")
    if not usuario or senha is None:
        raise ErroConector(400, "Informe usuário e senha do RM.", "Eles vão direto para o RM e não são guardados.")
    url = montar_url(cfg, caminho, parametros)

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
        with urllib.request.urlopen(req, timeout=cfg.timeout, context=_contexto_ssl(cfg)) as resp:
            status, bruto, tipo = resp.status, resp.read(MAX_CORPO_RESPOSTA + 1), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        status, bruto, tipo = e.code, e.read(MAX_CORPO_RESPOSTA + 1), e.headers.get("Content-Type", "") if e.headers else ""
    except (urllib.error.URLError, OSError) as e:
        raise traduzir_erro_rede(e, cfg) from None
    ms = int((time.monotonic() - inicio) * 1000)

    corpo_resp, truncado = _ler_corpo(bruto)
    _log(cfg, f"{metodo} {urllib.parse.urlsplit(url).path} -> {status} ({ms} ms)")
    return {
        "ok": 200 <= status < 300,
        "status": status,
        "tempo_ms": ms,
        "content_type": tipo,
        "corpo": corpo_resp,
        "truncado": truncado,
        "dica": None if 200 <= status < 300 else DICAS_HTTP.get(status, "Veja a mensagem devolvida pelo RM."),
    }


def enviar_lote(cfg: Config, metodo: str, caminho: str, registros: list, usuario: str, senha: str,
                campo_chave: str | None = None, parar_no_erro: bool = False) -> dict:
    """
    Um registro por chamada (o REST DataServer recebe um por vez). PUT usa
    caminho/<valor do campo_chave>. Devolve o resultado de cada registro.
    """
    metodo = (metodo or "").upper()
    if metodo not in ("POST", "PUT"):
        raise ErroConector(400, "Lote só com POST (incluir) ou PUT (alterar).")
    if not isinstance(registros, list) or not registros:
        raise ErroConector(400, "Nenhum registro no lote.")
    if len(registros) > MAX_REGISTROS_LOTE:
        raise ErroConector(400, f"Lote com mais de {MAX_REGISTROS_LOTE} registros.", "Divida o arquivo em partes.")
    if metodo == "PUT" and not campo_chave:
        raise ErroConector(400, "Para alterar em lote, informe o campo chave (ex.: CODUSUARIO).")

    resultados = []
    for i, reg in enumerate(registros, start=1):
        alvo = caminho.rstrip("/")
        chave = None
        if metodo == "PUT":
            chave = str((reg or {}).get(campo_chave, "")).strip() if isinstance(reg, dict) else ""
            if not chave:
                resultados.append({"indice": i, "chave": None, "ok": False, "status": None,
                                   "erro": f"Registro sem {campo_chave}."})
                if parar_no_erro:
                    break
                continue
            alvo = f"{alvo}/{urllib.parse.quote(chave, safe='')}"
        try:
            r = chamar_rm(cfg, metodo, alvo, usuario, senha, corpo=reg)
            item = {"indice": i, "chave": chave, "ok": r["ok"], "status": r["status"], "resposta": r["corpo"],
                    "dica": r["dica"]}
        except ErroConector as e:
            item = {"indice": i, "chave": chave, "ok": False, "status": None, "erro": e.mensagem,
                    "como_corrigir": e.como_corrigir}
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
            "falhas": enviados - sucesso, "nao_enviados": len(registros) - enviados, "resultados": resultados}


# --- Servidor local -----------------------------------------------------------


def _log(cfg: Config, texto: str) -> None:
    linha = time.strftime("%H:%M:%S ") + texto
    cfg.log.append(linha)
    print(linha, flush=True)


def criar_servidor(cfg: Config, porta: int = PORTA_PADRAO) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = f"ConectorRM/{VERSAO}"

        def log_message(self, *args):  # silencia o log padrão (teria caminho/cliente)
            pass

        def _origem_permitida(self) -> str | None:
            origem = self.headers.get("Origin")
            return origem if origem and origem in cfg.origens else None

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

        def do_GET(self):  # noqa: N802
            if self.path.split("?")[0] != "/status":
                return self._responder(404, {"ok": False, "erro": "Rota inexistente."})
            if not self._checar_acesso():
                return
            self._responder(200, {"ok": True, "conector": True, "versao": VERSAO, "rm": cfg.rm,
                                  "aceita_autoassinado": cfg.aceitar_autoassinado})

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
                                  pedido.get("senha"), pedido.get("corpo"), pedido.get("parametros"))
                else:
                    r = enviar_lote(cfg, pedido.get("metodo"), pedido.get("caminho"), pedido.get("registros"),
                                    pedido.get("usuario"), pedido.get("senha"), pedido.get("campo_chave"),
                                    bool(pedido.get("parar_no_erro")))
                    _log(cfg, f"lote {pedido.get('metodo')}: {r['sucesso']}/{r['total']} com sucesso")
            except ErroConector as e:
                _log(cfg, f"recusado: {e.mensagem}")
                return self._responder(e.status, e.para_dict())
            self._responder(200, r)

    return ThreadingHTTPServer(("127.0.0.1", porta), Handler)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Conector local entre o Acelerador e o RM.")
    ap.add_argument("--rm", required=True, help="Endereço do RM, ex.: https://rm.cliente.com.br:8051")
    ap.add_argument("--origem", action="append", default=[],
                    help="Endereço do site do Acelerador (pode repetir). Ex.: https://SEU-APP.vercel.app")
    ap.add_argument("--porta", type=int, default=PORTA_PADRAO)
    ap.add_argument("--timeout", type=float, default=60.0, help="Segundos de espera por chamada ao RM.")
    ap.add_argument("--aceitar-certificado-autoassinado", action="store_true",
                    help="Aceita HTTPS com certificado próprio do cliente (não verifica o certificado).")
    a = ap.parse_args(argv)

    try:
        rm = normalizar_rm(a.rm)
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2
    origens = tuple(o.rstrip("/") for o in a.origem) or ("http://localhost:3000",)
    cfg = Config(rm=rm, token=secrets.token_hex(4).upper(), origens=origens,
                 aceitar_autoassinado=a.aceitar_certificado_autoassinado, timeout=a.timeout)
    try:
        servidor = criar_servidor(cfg, a.porta)
    except OSError:
        print(f"Erro: a porta {a.porta} já está em uso. Use --porta com outro número.", file=sys.stderr)
        return 2

    print(f"Conector RM {VERSAO}")
    print(f"  RM:      {cfg.rm}")
    print(f"  Site:    {', '.join(cfg.origens)}")
    print(f"  Porta:   {a.porta} (só esta máquina)")
    if cfg.aceitar_autoassinado:
        print("  AVISO:   certificado HTTPS do RM NÃO será verificado (--aceitar-certificado-autoassinado).")
    print()
    print(f"  CÓDIGO DE PAREAMENTO:  {cfg.token}")
    print()
    print("Deixe esta janela aberta. Senhas não são gravadas nem exibidas. Ctrl+C para encerrar.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nConector encerrado.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
