"""
Testes do conector local (public/conector/conector_rm.py), com um RM falso
rodando em outra thread. Nada sai da máquina.
"""

import base64
import importlib.util
import json
import socket
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_ARQ = Path(__file__).resolve().parent.parent / "public" / "conector" / "conector_rm.py"
_spec = importlib.util.spec_from_file_location("conector_rm", _ARQ)
conector = importlib.util.module_from_spec(_spec)
sys.modules["conector_rm"] = conector  # dataclass precisa achar o módulo
_spec.loader.exec_module(conector)

ORIGEM = "https://acelerador.exemplo.com"
SENHA = "s3nh@-secreta"


class _RmFalso(BaseHTTPRequestHandler):
    recebidos: list = []

    def log_message(self, *a):
        pass

    def _tratar(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(tamanho) if tamanho else b""
        _RmFalso.recebidos.append({
            "metodo": self.command, "caminho": self.path,
            "auth": self.headers.get("Authorization"), "corpo": json.loads(corpo) if corpo else None,
        })
        if "ruim" in self.path or (corpo and b'"ruim"' in corpo):
            status, resp = 500, {"message": "Campo CODACESSO inválido"}
        elif self.path.endswith("/naoexiste"):
            status, resp = 404, {"message": "Registro não encontrado"}
        else:
            status, resp = 200, {"data": [{"CODUSUARIO": "ana"}], "length": 1}
        dados = json.dumps(resp).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    do_GET = do_POST = do_PUT = do_DELETE = _tratar


def _subir(servidor):
    t = threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    return servidor


@pytest.fixture()
def ambiente():
    _RmFalso.recebidos = []
    rm = _subir(ThreadingHTTPServer(("127.0.0.1", 0), _RmFalso))
    cfg = conector.Config(rm=f"http://127.0.0.1:{rm.server_address[1]}", token="ABCD1234",
                          origens=(ORIGEM,), timeout=5)
    srv = _subir(conector.criar_servidor(cfg, 0))
    yield cfg, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    rm.shutdown()


def _chamar(base, rota, corpo=None, token="ABCD1234", origem=ORIGEM, metodo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(base + rota, data=dados, method=metodo or ("POST" if dados else "GET"))
    if token:
        req.add_header("X-Conector-Token", token)
    if origem:
        req.add_header("Origin", origem)
    if dados:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, dict(r.headers), json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        corpo_erro = e.read()
        return e.code, dict(e.headers), json.loads(corpo_erro) if corpo_erro else {}


def test_status_com_codigo_certo(ambiente):
    cfg, base = ambiente
    status, cab, dados = _chamar(base, "/status")
    assert status == 200 and dados["conector"] and dados["rm"] == cfg.rm
    assert cab["Access-Control-Allow-Origin"] == ORIGEM


def test_codigo_errado_ou_origem_estranha_sao_barrados(ambiente):
    _, base = ambiente
    status, _, dados = _chamar(base, "/status", token="ERRADO")
    assert status == 401 and dados["conector"] is True and dados["como_corrigir"]
    status, cab, _ = _chamar(base, "/status", origem="https://site-malicioso.com")
    assert status == 403 and "Access-Control-Allow-Origin" not in cab


def test_preflight_cors_e_rede_privada(ambiente):
    _, base = ambiente
    status, cab, _ = _chamar(base, "/rm", token=None, metodo="OPTIONS")
    assert status == 204
    assert cab["Access-Control-Allow-Private-Network"] == "true"
    assert "X-Conector-Token" in cab["Access-Control-Allow-Headers"]
    status, _, _ = _chamar(base, "/rm", token=None, origem="https://outro.com", metodo="OPTIONS")
    assert status == 403


def test_get_repassa_autenticacao_e_parametros(ambiente):
    _, base = ambiente
    status, _, r = _chamar(base, "/rm", {
        "metodo": "GET", "caminho": "/rmsrestdataserver/rest/GlbUsuarioData",
        "parametros": {"filter": "CODUSUARIO = 'ana'"}, "usuario": "mestre", "senha": SENHA,
    })
    assert status == 200 and r["ok"] and r["status"] == 200
    assert r["corpo"]["data"][0]["CODUSUARIO"] == "ana"
    rec = _RmFalso.recebidos[-1]
    assert rec["metodo"] == "GET" and "filter=CODUSUARIO" in rec["caminho"]
    assert base64.b64decode(rec["auth"].split()[1]).decode() == f"mestre:{SENHA}"


@pytest.mark.parametrize("metodo", ["POST", "PUT", "DELETE"])
def test_post_put_delete(ambiente, metodo):
    _, base = ambiente
    corpo = {"CODUSUARIO": "ana", "NOME": "Ana"}
    caminho = "/rmsrestdataserver/rest/GlbUsuarioData" + ("" if metodo == "POST" else "/ana")
    status, _, r = _chamar(base, "/rm", {"metodo": metodo, "caminho": caminho, "corpo": corpo,
                                         "usuario": "mestre", "senha": SENHA})
    assert status == 200 and r["ok"]
    rec = _RmFalso.recebidos[-1]
    assert rec["metodo"] == metodo
    assert rec["corpo"] == (None if metodo == "DELETE" else corpo)


def test_erro_do_rm_volta_com_dica(ambiente):
    _, base = ambiente
    _, _, r = _chamar(base, "/rm", {"metodo": "GET", "caminho": "/rmsrestdataserver/rest/GlbUsuarioData/naoexiste",
                                    "usuario": "mestre", "senha": SENHA})
    assert r["ok"] is False and r["status"] == 404 and "chave" in r["dica"]


@pytest.mark.parametrize("caminho", [
    "http://outro-host/rmsrestdataserver/rest/X",
    "//outro-host/rmsrestdataserver/rest/X",
    "/rmsrestdataserver/../admin",
    "/outra/coisa",
    "rmsrestdataserver/rest/X",
])
def test_nao_e_proxy_aberto(ambiente, caminho):
    _, base = ambiente
    status, _, r = _chamar(base, "/rm", {"metodo": "GET", "caminho": caminho, "usuario": "u", "senha": "s"})
    assert status in (400, 403) and r["como_corrigir"]
    assert _RmFalso.recebidos == []


def test_metodo_e_credenciais_obrigatorios(ambiente):
    _, base = ambiente
    caminho = "/rmsrestdataserver/rest/GlbUsuarioData"
    assert _chamar(base, "/rm", {"metodo": "PATCH", "caminho": caminho, "usuario": "u", "senha": "s"})[0] == 400
    assert _chamar(base, "/rm", {"metodo": "GET", "caminho": caminho})[0] == 400


def test_lote_post_continua_apos_erro_e_conta(ambiente):
    _, base = ambiente
    regs = [{"CODUSUARIO": "ana"}, {"CODUSUARIO": "ruim"}, {"CODUSUARIO": "bia"}]
    status, _, r = _chamar(base, "/rm/lote", {"metodo": "POST", "caminho": "/rmsrestdataserver/rest/GlbUsuarioData",
                                              "registros": regs, "usuario": "mestre", "senha": SENHA})
    assert status == 200
    assert (r["total"], r["sucesso"], r["falhas"], r["nao_enviados"]) == (3, 2, 1, 0)
    assert r["resultados"][1]["ok"] is False and r["resultados"][1]["status"] == 500


def test_lote_put_usa_chave_na_url_e_para_no_erro(ambiente):
    _, base = ambiente
    regs = [{"CODUSUARIO": "ana"}, {"NOME": "sem chave"}, {"CODUSUARIO": "bia"}]
    _, _, r = _chamar(base, "/rm/lote", {"metodo": "PUT", "caminho": "/rmsrestdataserver/rest/GlbUsuarioData",
                                         "campo_chave": "CODUSUARIO", "parar_no_erro": True,
                                         "registros": regs, "usuario": "mestre", "senha": SENHA})
    assert (r["enviados"], r["sucesso"], r["nao_enviados"]) == (2, 1, 1)
    assert _RmFalso.recebidos[0]["caminho"].endswith("/GlbUsuarioData/ana")


def test_senha_nunca_aparece_no_log(ambiente):
    cfg, base = ambiente
    _chamar(base, "/rm", {"metodo": "POST", "caminho": "/rmsrestdataserver/rest/GlbUsuarioData",
                          "corpo": {"CODUSUARIO": "ana"}, "usuario": "mestre", "senha": SENHA})
    texto = "\n".join(cfg.log)
    assert SENHA not in texto and "mestre" not in texto and "ana" not in texto
    assert "POST /rmsrestdataserver/rest/GlbUsuarioData -> 200" in texto


def test_rm_fora_do_ar_da_mensagem_de_como_corrigir():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta_livre = s.getsockname()[1]
    cfg = conector.Config(rm=f"http://127.0.0.1:{porta_livre}", token="X", timeout=3)
    with pytest.raises(conector.ErroConector) as e:
        conector.chamar_rm(cfg, "GET", "/rmsrestdataserver/rest/X", "u", "s")
    assert e.value.status == 502 and "porta" in e.value.como_corrigir


def test_normalizar_rm():
    assert conector.normalizar_rm("https://rm.cliente.com:8051/qualquer/coisa") == "https://rm.cliente.com:8051"
    with pytest.raises(ValueError):
        conector.normalizar_rm("rm.cliente.com:8051")


def test_main_recusa_endereco_invalido(capsys):
    assert conector.main(["--rm", "ftp://x"]) == 2
