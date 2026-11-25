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
                          origens=(ORIGEM,), timeout=5, detectar_local=False)
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
    assert rec["metodo"] == "GET" and "filter=CODUSUARIO%20%3D%20%27ana%27" in rec["caminho"]
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


# --- 1.1: várias bases, chave composta, registro existente ------------------------

LOTE = "/rm/lote"
DS = "/rmsrestdataserver/rest/GlbUsuarioData"


def test_status_lista_as_bases(ambiente):
    cfg, base = ambiente
    cfg.bases = {"homolog": cfg.rm, "producao": cfg.rm}
    _, _, r = _chamar(base, "/status")
    assert [b["nome"] for b in r["bases"]] == ["homolog", "producao"] and r["versao"] == conector.VERSAO


def test_chamada_vai_para_a_base_escolhida_e_base_desconhecida_e_recusada(ambiente):
    cfg, base = ambiente
    cfg.bases = {"origem": "http://127.0.0.1:9", "destino": cfg.rm}  # origem: porta fechada
    status, _, r = _chamar(base, "/rm", {"metodo": "GET", "caminho": DS, "base": "destino",
                                         "usuario": "u", "senha": SENHA})
    assert status == 200 and r["ok"] and len(_RmFalso.recebidos) == 1
    status, _, r = _chamar(base, "/rm", {"metodo": "GET", "caminho": DS, "base": "outra",
                                         "usuario": "u", "senha": SENHA})
    assert status == 400 and "destino" in r["como_corrigir"]
    assert any("[destino] GET" in linha for linha in cfg.log)


def test_chave_composta_usa_separador_do_rm():
    reg = {"CODCOLIGADA": 1, "CODEVENTO": 7, "NOME": "x"}
    assert conector.chave_do_registro(reg, "CODCOLIGADA,CODEVENTO") == "1$_$7"
    assert conector.chave_do_registro(reg, "CODCOLIGADA, CODFALTANTE") == ""
    assert conector.chave_do_registro({"CODUSUARIO": "ana"}, "CODUSUARIO") == "ana"


def test_put_com_chave_composta(ambiente):
    _, base = ambiente
    _, _, r = _chamar(base, LOTE, {"metodo": "PUT", "caminho": "/rmsrestdataserver/rest/CtbEventoData",
                                   "campo_chave": "CODCOLIGADA,CODEVENTO", "usuario": "u", "senha": SENHA,
                                   "registros": [{"CODCOLIGADA": 1, "CODEVENTO": 1}]})
    assert r["sucesso"] == 1 and _RmFalso.recebidos[0]["caminho"].endswith("/CtbEventoData/1$_$1")


def test_post_pula_ou_altera_o_que_ja_existe(ambiente):
    _, base = ambiente
    regs = [{"CODUSUARIO": "ana"}, {"CODUSUARIO": "naoexiste"}]  # ana existe no RM falso
    pedido = {"metodo": "POST", "caminho": DS, "campo_chave": "CODUSUARIO", "usuario": "u", "senha": SENHA,
              "registros": regs}

    _, _, r = _chamar(base, LOTE, {**pedido, "se_existir": "pular"})
    assert [x["acao"] for x in r["resultados"]] == ["pulado", "incluido"] and r["pulados"] == 1
    enviados = [(x["metodo"], x["caminho"]) for x in _RmFalso.recebidos]
    assert enviados == [("GET", f"{DS}/ana"), ("GET", f"{DS}/naoexiste"), ("POST", DS)]

    _RmFalso.recebidos.clear()
    _, _, r = _chamar(base, LOTE, {**pedido, "se_existir": "alterar"})
    assert [x["acao"] for x in r["resultados"]] == ["alterado", "incluido"]
    assert ("PUT", f"{DS}/ana") in [(x["metodo"], x["caminho"]) for x in _RmFalso.recebidos]


def test_se_existir_exige_campo_chave_e_valor_valido(ambiente):
    _, base = ambiente
    pedido = {"metodo": "POST", "caminho": DS, "usuario": "u", "senha": SENHA, "registros": [{"CODUSUARIO": "a"}]}
    assert _chamar(base, LOTE, {**pedido, "se_existir": "pular"})[0] == 400
    assert _chamar(base, LOTE, {**pedido, "se_existir": "x", "campo_chave": "CODUSUARIO"})[0] == 400


def test_ler_bases():
    assert conector.ler_bases(["https://rm:8051/x"]) == {"principal": "https://rm:8051"}
    assert conector.ler_bases(["homolog=https://a:1", "producao=http://b:2"]) == {
        "homolog": "https://a:1", "producao": "http://b:2"}
    with pytest.raises(ValueError):
        conector.ler_bases(["a=https://x:1", "a=https://y:1"])
    with pytest.raises(ValueError):
        conector.ler_bases(["nome ruim=https://x:1"])


# --- 1.2: dois cliques, código fixo -------------------------------------------------

def test_codigo_de_pareamento_fica_guardado(tmp_path):
    arq = tmp_path / "cfg.json"
    c1 = conector.codigo_de_pareamento(arquivo=arq)
    assert len(c1) == 8 and conector.codigo_de_pareamento(arquivo=arq) == c1  # não muda ao reabrir
    c2 = conector.codigo_de_pareamento(novo=True, arquivo=arq)
    assert c2 != c1 and conector.codigo_de_pareamento(arquivo=arq) == c2
    assert "senha" not in arq.read_text(encoding="utf-8").lower()


def test_dois_cliques_pergunta_guarda_e_reaproveita(tmp_path, monkeypatch):
    arq = tmp_path / "cfg.json"
    respostas = iter(["endereco-ruim", "homolog=https://rm-hml:8051", "producao=https://rm:8051", "",
                      "", "s"])
    monkeypatch.setattr("builtins.input", lambda _: next(respostas))
    monkeypatch.setattr(conector, "detectar_rm_local", lambda raizes=None: [])  # máquina sem RM
    argv = conector.perguntar_argumentos(arq)
    assert argv == ["--rm", "homolog=https://rm-hml:8051", "--rm", "producao=https://rm:8051",
                    "--origem", conector.SITE_PADRAO, "--aceitar-certificado-autoassinado"]  # padrão: só o oficial
    # segunda vez: só confirma (Enter)
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert conector.perguntar_argumentos(arq) == argv


def test_dois_cliques_com_erro_segura_a_janela(monkeypatch):
    perguntas = []
    monkeypatch.setattr(conector.sys, "argv", ["conector_rm.py"])
    monkeypatch.setattr(conector, "perguntar_argumentos", lambda **_: ["--rm", "ftp://x"])
    monkeypatch.setattr("builtins.input", lambda texto: perguntas.append(texto) or "")
    monkeypatch.delenv("CONECTOR_SEM_PAUSA", raising=False)
    assert conector.iniciar() == 2
    assert perguntas and "Enter" in perguntas[0]


def test_site_nao_autorizado_e_avisado_na_janela(ambiente):
    cfg, base = ambiente
    status, _, _ = _chamar(base, "/status", origem="https://outro-site.vercel.app")
    assert status == 403
    _chamar(base, "/status", origem="https://outro-site.vercel.app")
    avisos = [l for l in cfg.log if "RECUSADO" in l]
    assert len(avisos) == 1  # uma vez por site, sem encher a janela
    assert "https://outro-site.vercel.app" in avisos[0] and ORIGEM in avisos[0]


# --- 1.3: endereços de deploy da Vercel e /ping ---------------------------------------

def test_origem_com_curinga_para_deploys_da_vercel():
    lista = ("https://acelerador-rm.vercel.app", "https://acelerador-*-mateusroliveira-collab.vercel.app")
    ok = conector.origem_autorizada
    assert ok("https://acelerador-m2sap88pd-mateusroliveira-collab.vercel.app", lista)
    assert ok("https://acelerador-git-melhorias-mateusroliveira-collab.vercel.app", lista)
    assert ok("https://acelerador-rm.vercel.app/", lista)
    assert not ok("https://acelerador-x.evil.com/-mateusroliveira-collab.vercel.app", lista)
    assert not ok("https://acelerador-x.mateusroliveira-collab.vercel.app", lista)  # * não atravessa "."
    assert not ok("https://acelerador-abc-outra-equipe.vercel.app", lista)
    assert not ok("http://acelerador-abc-mateusroliveira-collab.vercel.app", lista)
    assert not ok(None, lista)


def test_ping_diz_se_o_site_e_aceito_sem_revelar_nada(ambiente):
    _, base = ambiente
    status, cab, r = _chamar(base, "/ping", token=None, origem="https://outro-site.vercel.app")
    assert status == 200 and r == {"conector": True, "versao": conector.VERSAO, "origem_autorizada": False}
    assert cab.get("Access-Control-Allow-Origin") == "https://outro-site.vercel.app"
    _, _, r = _chamar(base, "/ping", token=None)
    assert r["origem_autorizada"] is True


def test_origens_do_site_inclui_padrao_dos_deploys():
    assert conector.origens_do_site("https://acelerador-m2sap88pd-mateusroliveira-collab.vercel.app/") == [
        "https://acelerador-m2sap88pd-mateusroliveira-collab.vercel.app",
        "https://acelerador-*-mateusroliveira-collab.vercel.app",
        conector.SITE_PADRAO,
    ]
    assert conector.origens_do_site(conector.SITE_PADRAO) == [conector.SITE_PADRAO]
    assert conector.origens_do_site("http://localhost:3000") == ["http://localhost:3000", conector.SITE_PADRAO]


# --- 1.3.1: endereço colado com o caminho da página ------------------------------------

def test_endereco_com_caminho_vira_so_a_origem():
    assert conector.so_origem("https://Acelerador-13elcv5dx-x.vercel.app/gerador-dataserver?a=1") == \
        "https://acelerador-13elcv5dx-x.vercel.app"
    assert conector.so_origem("acelerador-rm.vercel.app/hub-mit41") == "https://acelerador-rm.vercel.app"
    assert conector.so_origem("http://localhost:3000/") == "http://localhost:3000"


def test_origem_salva_com_caminho_passa_a_funcionar():
    # exatamente o que estava salvo na máquina do analista (config do 1.2)
    origens = conector.origens_autorizadas([
        "https://acelerador-13elcv5dx-mateusroliveira-collab.vercel.app/gerador-dataserver",
        "https://acelerador-rm.vercel.app",
    ])
    assert origens == (
        "https://acelerador-13elcv5dx-mateusroliveira-collab.vercel.app",
        "https://acelerador-*-mateusroliveira-collab.vercel.app",
        "https://acelerador-rm.vercel.app",
    )
    assert conector.origem_autorizada("https://acelerador-m2sap88pd-mateusroliveira-collab.vercel.app", origens)


# --- 1.4: RM instalado nesta máquina ----------------------------------------------------

def _rm_instalado(raiz, nome, porta_http, alias, instalacao="CorporeRM"):
    pasta = raiz / instalacao / "RM.Net"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{nome}.exe.config").write_text(
        '<configuration><appSettings>'
        f'<add key="DefaultDB" value="{alias}" /><add key="Port" value="8050" />'
        f'<add key="HTTPPort" value="{porta_http}" />'
        '<add key="ConnectionString" value="Password=NAO-PODE-APARECER" />'
        '</appSettings></configuration>', encoding="utf-8")


def test_detecta_rm_local_porta_alias_e_se_esta_no_ar(tmp_path):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        porta_no_ar = s.getsockname()[1]
        _rm_instalado(tmp_path, "RM.Host.Service1", 59999, "OutroBanco")
        _rm_instalado(tmp_path, "RM.Host.Service", porta_no_ar, "CorporeRM")
        _rm_instalado(tmp_path, "RM.Host.Service", 59998, "", instalacao="Base-FIEPE")
        achados = conector.detectar_rm_local([tmp_path])
    # por instalação (pasta), e o serviço principal primeiro em cada uma
    assert [(a["instalacao"], a["servico"]) for a in achados] == [
        ("Base-FIEPE", "RM.Host.Service"), ("CorporeRM", "RM.Host.Service"), ("CorporeRM", "RM.Host.Service1")]
    assert achados[1] == {"instalacao": "CorporeRM", "servico": "RM.Host.Service",
                          "endereco": f"http://localhost:{porta_no_ar}", "porta": porta_no_ar,
                          "alias": "CorporeRM", "no_ar": True}
    assert achados[2]["no_ar"] is False
    assert "NAO-PODE-APARECER" not in json.dumps(achados)
    assert conector.alias_da_base(f"http://localhost:{porta_no_ar}", achados) == "CorporeRM"
    assert conector.alias_da_base(f"http://rm.cliente.com:{porta_no_ar}", achados) is None
    assert conector.detectar_rm_local([tmp_path / "nao-existe"]) == []


def test_dois_cliques_sugere_o_rm_desta_maquina(tmp_path, monkeypatch):
    arq = tmp_path / "cfg.json"
    monkeypatch.setattr(conector, "detectar_rm_local", lambda raizes=None: [
        {"instalacao": "Base-FIEPE", "servico": "RM.Host.Service", "endereco": "http://localhost:8061",
         "porta": 8061, "alias": None, "no_ar": True},
        {"instalacao": "CorporeRM", "servico": "RM.Host.Service", "endereco": "http://localhost:8051",
         "porta": 8051, "alias": "CorporeRM", "no_ar": True},
        {"instalacao": "CorporeRM", "servico": "RM.Host.Service1", "endereco": "http://localhost:8053",
         "porta": 8053, "alias": "CorporeRM", "no_ar": True},  # mesma instalação: não vira outra base
    ])
    monkeypatch.setattr("builtins.input", lambda _: "")  # Enter em tudo
    argv = conector.perguntar_argumentos(arq)
    assert argv[:4] == ["--rm", "base-fiepe=http://localhost:8061", "--rm", "corporerm=http://localhost:8051"]
    assert conector.SITE_PADRAO in argv
    assert conector.ler_bases([argv[1], argv[3]]) == {"base-fiepe": "http://localhost:8061",
                                                     "corporerm": "http://localhost:8051"}


def test_status_mostra_alias_da_base_local(ambiente, monkeypatch):
    cfg, base = ambiente
    cfg.detectar_local = True
    porta = int(cfg.rm.rsplit(":", 1)[1])
    cfg.bases = {"local": f"http://localhost:{porta}"}
    monkeypatch.setattr(conector, "detectar_rm_local", lambda raizes=None: [
        {"instalacao": "CorporeRM", "servico": "RM.Host.Service", "endereco": f"http://localhost:{porta}",
         "porta": porta, "alias": "CorporeRM", "no_ar": True}])
    _, _, r = _chamar(base, "/status")
    assert r["bases"] == [{"nome": "local", "rm": f"http://localhost:{porta}", "alias": "CorporeRM"}]
    assert r["rm_local"][0]["alias"] == "CorporeRM" and "porta" not in r["rm_local"][0]


def test_atalho_sem_bases_detecta_o_rm_e_usa_o_site_do_atalho(tmp_path, monkeypatch):
    chamado = {}
    monkeypatch.setattr(conector, "ARQUIVO_CONFIG", tmp_path / "cfg.json")
    monkeypatch.setattr(conector, "detectar_rm_local", lambda raizes=None: [
        {"instalacao": "CorporeRM", "servico": "RM.Host.Service", "endereco": "http://localhost:8051",
         "porta": 8051, "alias": "CorporeRM", "no_ar": True}])
    perguntas = []
    monkeypatch.setattr("builtins.input", lambda texto: perguntas.append(texto) or "")
    monkeypatch.setattr(conector, "main", lambda argv: chamado.setdefault("argv", argv) and 0)
    site = "https://acelerador-m2sap88pd-mateusroliveira-collab.vercel.app"
    assert conector.iniciar(["--origem", site, "--porta", "8765"]) == 0
    argv = chamado["argv"]
    assert argv[:2] == ["--rm", "corporerm=http://localhost:8051"]
    assert site in argv and "https://acelerador-*-mateusroliveira-collab.vercel.app" in argv
    assert argv[-2:] == ["--porta", "8765"]
    assert not any("site" in p.lower() for p in perguntas)  # o site veio do atalho: não pergunta
