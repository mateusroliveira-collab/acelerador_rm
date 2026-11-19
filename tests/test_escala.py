"""
Preparação pra escalar/produtizar: API v1, segurança desligada por padrão,
configuração por cliente, versão de schema e o contrato com o Google Sheets.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST", "VERCEL",
           "API_KEYS", "API_EXIGIR_CHAVE", "RATE_LIMIT_POR_MINUTO"):
    os.environ.pop(_v, None)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/escala.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.index import app  # noqa: E402
from api._lib import seguranca  # noqa: E402
from api._lib.db import SessionLocal  # noqa: E402
from api._lib.models import Cliente, RegistroUso  # noqa: E402

client = TestClient(app)
V1 = "/api/v1/dataserver"


@pytest.fixture(autouse=True)
def _ambiente_limpo(monkeypatch):
    for v in ("API_KEYS", "API_EXIGIR_CHAVE", "RATE_LIMIT_POR_MINUTO"):
        monkeypatch.delenv(v, raising=False)
    seguranca._janelas.clear()


def _cadastrar_cliente(codigo, config, ativo=True):
    db = SessionLocal()
    try:
        db.query(Cliente).filter_by(codigo=codigo).delete()
        db.add(Cliente(codigo=codigo, nome=codigo.upper(), ativo=ativo, config=json.dumps(config)))
        db.commit()
    finally:
        db.close()


VALORES = {"CODUSUARIO": "ana.teste", "CODACESSO": "Acesso01", "DATAINICIO": "2026-01-01"}


# --- API v1 e alias --------------------------------------------------------

def test_v1_e_alias_respondem_igual_e_so_v1_esta_na_documentacao():
    a = client.get(f"{V1}/modulos").json()
    b = client.get("/api/dataserver/modulos").json()
    assert a == b and a[0]["versao_schema"] == "1"
    paths = client.get("/openapi.json").json()["paths"]
    assert any(p.startswith("/api/v1/dataserver") for p in paths)
    assert not any(p.startswith("/api/dataserver") for p in paths)


# --- segurança desligada por padrão / ligada por ambiente --------------------

def test_sem_configuracao_a_api_continua_aberta():
    assert client.get(f"{V1}/modulos").status_code == 200


def test_exigir_chave(monkeypatch):
    monkeypatch.setenv("API_KEYS", "chave-a:clienteA,chave-b:clienteB")
    monkeypatch.setenv("API_EXIGIR_CHAVE", "1")
    assert client.get(f"{V1}/modulos").status_code == 401
    assert client.get(f"{V1}/modulos", headers={"X-API-Key": "errada"}).status_code == 401
    assert client.get(f"{V1}/modulos", headers={"X-API-Key": "chave-a"}).status_code == 200


def test_chaves_configuradas_mas_nao_obrigatorias_nao_bloqueiam(monkeypatch):
    monkeypatch.setenv("API_KEYS", "chave-a:clienteA")
    assert client.get(f"{V1}/modulos").status_code == 200  # sem chave -> "interno"


def test_limite_de_uso(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_POR_MINUTO", "3")
    codigos = [client.get(f"{V1}/modulos").status_code for _ in range(5)]
    assert codigos == [200, 200, 200, 429, 429]


# --- configuração por cliente ---------------------------------------------------

def test_codigos_de_acesso_do_cliente_viram_opcoes_e_validacao():
    _cadastrar_cliente("acme", {"glb-usuario": {"codigos_acesso": ["Acesso01", "Acesso02"]}})
    modulo = client.get(f"{V1}/modulos", params={"cliente": "acme"}).json()[0]
    codacesso = next(c for c in modulo["campos"] if c["nome"] == "CODACESSO")
    assert codacesso["opcoes"] == ["Acesso01", "Acesso02"]
    sem_cliente = client.get(f"{V1}/modulos").json()[0]
    assert next(c for c in sem_cliente["campos"] if c["nome"] == "CODACESSO")["opcoes"] is None

    ok = client.post(f"{V1}/glb-usuario/gerar", json={"operacao": "incluir", "cliente": "acme", "valores": VALORES})
    assert ok.status_code == 200
    ruim = client.post(f"{V1}/glb-usuario/gerar", json={
        "operacao": "incluir", "cliente": "acme", "valores": {**VALORES, "CODACESSO": "Admin99"}})
    assert ruim.status_code == 422
    assert ruim.json()["detail"]["erros"][0]["campo"] == "CODACESSO"


def test_lista_do_cliente_nao_diferencia_maiuscula():
    _cadastrar_cliente("acme", {"glb-usuario": {"codigos_acesso": ["Acesso01"]}})
    r = client.post(f"{V1}/glb-usuario/gerar", json={
        "operacao": "incluir", "cliente": "acme", "valores": {**VALORES, "CODACESSO": "ACESSO01"}})
    assert r.status_code == 200


def test_cliente_inativo_ou_inexistente_nao_aplica_lista():
    _cadastrar_cliente("velho", {"glb-usuario": {"codigos_acesso": ["Só"]}}, ativo=False)
    for cod in ("velho", "nao-existe"):
        r = client.post(f"{V1}/glb-usuario/gerar", json={"operacao": "incluir", "cliente": cod, "valores": VALORES})
        assert r.status_code == 200


def test_com_chave_de_api_o_cliente_e_o_da_chave_nao_o_informado(monkeypatch):
    _cadastrar_cliente("clientea", {"glb-usuario": {"codigos_acesso": ["Acesso01"]}})
    _cadastrar_cliente("clienteb", {"glb-usuario": {"codigos_acesso": ["Outro"]}})
    monkeypatch.setenv("API_KEYS", "chave-a:clientea")
    monkeypatch.setenv("API_EXIGIR_CHAVE", "1")
    # tenta se passar pelo clienteb: a lista usada continua sendo a do clientea
    r = client.post(f"{V1}/glb-usuario/gerar", headers={"X-API-Key": "chave-a"},
                    json={"operacao": "incluir", "cliente": "clienteb", "valores": VALORES})
    assert r.status_code == 200
    modulo = client.get(f"{V1}/modulos", params={"cliente": "clienteb"}, headers={"X-API-Key": "chave-a"}).json()[0]
    assert next(c for c in modulo["campos"] if c["nome"] == "CODACESSO")["opcoes"] == ["Acesso01"]


def test_config_corrompida_nao_derruba_a_geracao():
    db = SessionLocal()
    try:
        db.query(Cliente).filter_by(codigo="quebrado").delete()
        db.add(Cliente(codigo="quebrado", ativo=True, config="{isso não é json"))
        db.commit()
    finally:
        db.close()
    r = client.post(f"{V1}/glb-usuario/gerar", json={"operacao": "incluir", "cliente": "quebrado", "valores": VALORES})
    assert r.status_code == 200


# --- versão de schema e trilha de auditoria -----------------------------------------

def test_versao_do_schema_nas_respostas_e_no_log_sem_dados_pessoais():
    r = client.post(f"{V1}/glb-usuario/gerar", json={"operacao": "incluir", "cliente": "acme", "valores": VALORES})
    assert r.json()["versao_schema"] == "1"
    db = SessionLocal()
    try:
        ultimo = db.query(RegistroUso).filter_by(ferramenta="dataserver").order_by(RegistroUso.id.desc()).first()
        detalhes = json.loads(ultimo.detalhes)
        assert detalhes["versao_schema"] == "1" and detalhes["cliente"] == "acme"
        assert "ana.teste" not in ultimo.detalhes
    finally:
        db.close()


# --- Planilha modelo (Google Sheets) ---------------------------------------------------

def test_contrato_com_o_sheets_valores_como_a_planilha_mostra():
    """Colar da planilha traz o texto exibido: 'Sim'/'Não', datas dd/MM/yyyy, cabeçalho = nome do campo."""
    texto = "\n".join([
        "\t".join(["CODUSUARIO", "NOME", "EMAIL", "CODACESSO", "STATUS", "OIDC_ENABLED", "DATAINICIO", "DATAEXPIRACAO"]),
        "\t".join(["ana.teste", "Ana", "ana@exemplo.com", "Acesso01", "Sim", "Não", "18/11/2026", ""]),
        "\t".join(["bia.teste", "Bia", "", "Acesso01", "Não", "Não", "01/12/2026", "31/12/2026"]),
    ])
    r = client.post(f"{V1}/glb-usuario/lote", json={"operacao": "incluir", "texto": texto})
    assert r.status_code == 200
    corpo = r.json()
    assert (corpo["validos"], corpo["invalidos"]) == (2, 0)
    linhas = [json.loads(l) for l in corpo["jsonl"].strip().splitlines()]
    assert linhas[0]["STATUS"] == 1 and linhas[1]["STATUS"] == 0
    assert linhas[1]["DATAEXPIRACAO"] == "2026-12-31T00:00:00-03:00"
    assert corpo["versao_schema"] == "1"


def test_erro_do_lote_traz_campo_e_numero_de_linha_da_planilha():
    texto = "CODUSUARIO\tCODACESSO\tDATAINICIO\nana\tAcesso01\t18/11/2026\nbia\t\t99/99/2026"
    corpo = client.post(f"{V1}/glb-usuario/lote", json={"operacao": "incluir", "texto": texto}).json()
    ruim = corpo["linhas"][1]
    assert ruim["linha"] == 3 and not ruim["valido"]
    assert {e["campo"] for e in ruim["erros"]} == {"CODACESSO", "DATAINICIO"}


# Cabeçalhos exatamente como estão na planilha modelo (rótulos da tela do RM; * = obrigatório).
CABECALHOS_PLANILHA = [
    "Usuário *", "Nome", "Nome Social", "E-Mail", "Código de Acesso *", "Ativo", "Login OIDC *",
    "Alterar senha no próximo login", "Força a troca de senha a cada (dias)", "Início de Validade *",
    "Expiração de Validade", "Usuário de rede", "Domínio de rede", "Ignorar autenticação LDAP",
]


def test_cabecalhos_da_planilha_modelo_mapeiam_todos_os_campos():
    from api._lib.dataserver.glb_usuario import MODULO
    from api._lib.dataserver.lote import mapear_colunas

    mapa, ignoradas = mapear_colunas(MODULO, CABECALHOS_PLANILHA)
    assert ignoradas == []
    assert [mapa[i] for i in range(len(CABECALHOS_PLANILHA))] == [c.nome for c in MODULO.campos]


def test_colar_a_planilha_modelo_inteira_funciona_ponta_a_ponta():
    linhas = [
        "\t".join(CABECALHOS_PLANILHA),
        "\t".join(["maria.silva", "Maria Silva", "", "maria@exemplo.com", "Acesso01", "Sim", "Não", "Sim", "", "01/12/2026", "", "", "", "Não"]),
        "\t".join(["", "", "", "", "", "", "", "", "", "", "", "", "", ""]),  # linha vazia da planilha
    ]
    r = client.post(f"{V1}/glb-usuario/lote", json={"operacao": "incluir", "texto": "\n".join(linhas)})
    corpo = r.json()
    assert r.status_code == 200 and (corpo["validos"], corpo["invalidos"], corpo["total"]) == (1, 0, 1)
    assert corpo["avisos_gerais"] == []


@pytest.mark.parametrize("env,esperado", [
    ("https://docs.google.com/spreadsheets/d/1q053_56zJQWJ3FTkN7V3vhVffT-KExQpqDD93QBQwvU/edit?pli=1&gid=0#gid=0",
     "https://docs.google.com/spreadsheets/d/1q053_56zJQWJ3FTkN7V3vhVffT-KExQpqDD93QBQwvU/copy"),
    ("", None),
    ("https://evil.example.com/spreadsheets/d/1q053_56zJQWJ3FTkN7V3vhVffT-KExQpqDD93QBQwvU", None),
    ("javascript:alert(1)", None),
    ("http://docs.google.com/spreadsheets/d/1q053_56zJQWJ3FTkN7V3vhVffT-KExQpqDD93QBQwvU", None),
])
def test_link_da_planilha_modelo(monkeypatch, env, esperado):
    monkeypatch.setenv("PLANILHA_MODELO_GLB_USUARIO", env)
    modulo = client.get(f"{V1}/modulos").json()[0]
    assert modulo["planilha_modelo_url"] == esperado


def test_rotas_do_apps_script_foram_removidas():
    assert client.get(f"{V1}/google-sheets/script", params={"base": "https://x.com"}).status_code == 404
    assert client.get(f"{V1}/google-sheets/manifesto").status_code == 404


def test_links_da_planilha_modelo_copia_e_download(monkeypatch):
    id_ = "1q053_56zJQWJ3FTkN7V3vhVffT-KExQpqDD93QBQwvU"
    monkeypatch.setenv("PLANILHA_MODELO_GLB_USUARIO", f"https://docs.google.com/spreadsheets/d/{id_}/edit?gid=0")
    m = client.get(f"{V1}/modulos").json()[0]
    assert m["planilha_modelo_url"] == f"https://docs.google.com/spreadsheets/d/{id_}/copy"
    assert m["planilha_modelo_xlsx_url"] == f"https://docs.google.com/spreadsheets/d/{id_}/export?format=xlsx"

    monkeypatch.setenv("PLANILHA_MODELO_GLB_USUARIO", "https://evil.example.com/x")
    m = client.get(f"{V1}/modulos").json()[0]
    assert m["planilha_modelo_url"] is None and m["planilha_modelo_xlsx_url"] is None


def test_modelo_csv_publico_passa_na_propria_validacao():
    csv = client.get(f"{V1}/glb-usuario/modelo-csv").content.decode("utf-8-sig")
    r = client.post(f"{V1}/glb-usuario/lote", json={"operacao": "incluir", "texto": csv})
    assert r.json()["validos"] == 1
