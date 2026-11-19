import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST", "VERCEL"):
    os.environ.pop(_v, None)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/ds.db"

from fastapi.testclient import TestClient  # noqa: E402

from api.index import app  # noqa: E402
from api._lib.dataserver.base import normalizar_e_validar  # noqa: E402
from api._lib.dataserver.glb_usuario import MODULO, gerar_payload  # noqa: E402
from api._lib.db import SessionLocal  # noqa: E402
from api._lib.models import RegistroUso  # noqa: E402

client = TestClient(app)

# Usuário FICTÍCIO -- nenhum dado real nos testes.
VALIDO = {
    "CODUSUARIO": "fulano.teste",
    "NOME": "Fulano de Teste",
    "EMAIL": "fulano.teste@exemplo.com",
    "CODACESSO": "Acesso01",
    "DATAINICIO": "2026-11-18",
}


def _campos_com_erro(valores, operacao="incluir"):
    _, erros = normalizar_e_validar(MODULO, valores, operacao)
    return {e["campo"] for e in erros}


def test_obrigatorios_sao_os_da_tela_do_rm():
    obrigatorios = {c.nome for c in MODULO.campos if c.obrigatorio}
    assert obrigatorios == {"CODUSUARIO", "CODACESSO", "OIDC_ENABLED", "DATAINICIO"}


def test_vazio_acusa_so_os_obrigatorios_sem_padrao():
    # OIDC_ENABLED tem padrão (desmarcado), então não dá erro.
    assert _campos_com_erro({}) == {"CODUSUARIO", "CODACESSO", "DATAINICIO"}


def test_nome_nao_e_obrigatorio():
    valores = {k: v for k, v in VALIDO.items() if k != "NOME"}
    assert _campos_com_erro(valores) == set()


def test_payload_tem_formato_do_exemplo_do_rm():
    normalizados, erros = normalizar_e_validar(MODULO, VALIDO, "incluir")
    assert erros == []
    payload = gerar_payload(normalizados)
    assert payload["CODUSUARIO"] == "fulano.teste"
    assert payload["STATUS"] == 1  # inteiro, como no exemplo
    assert payload["OIDC_ENABLED"] == 0
    assert payload["IGNORARAUTENTICACAOLDAP"] == "F"  # string T/F, como no exemplo
    assert payload["DATAINICIO"] == "2026-11-18T00:00:00-03:00"  # ISO com fuso
    assert "DATAEXPIRACAO" not in payload  # vazio = sempre válido


def test_payload_nunca_leva_senha_nem_campos_do_rm():
    normalizados, _ = normalizar_e_validar(MODULO, {**VALIDO, "SENHA": "x", "TOTPSECRETKEY": "y"}, "incluir")
    payload = gerar_payload(normalizados)
    proibidos = {"SENHA", "TOTPSECRETKEY", "SENHATWITTER", "SENHAFACEBOOK", "SENHALINKEDIN",
                 "DATAULTIMOACESSO", "CONTROLE", "ULTIMASSENHAS", "NUMLOGININVALIDO"}
    assert proibidos.isdisjoint(payload)


def test_email_invalido():
    assert "EMAIL" in _campos_com_erro({**VALIDO, "EMAIL": "isso-nao-e-email"})


def test_data_invalida_e_expiracao_antes_do_inicio():
    assert "DATAINICIO" in _campos_com_erro({**VALIDO, "DATAINICIO": "18/11/2026"})
    assert "DATAEXPIRACAO" in _campos_com_erro({**VALIDO, "DATAEXPIRACAO": "2026-01-01"})
    assert _campos_com_erro({**VALIDO, "DATAEXPIRACAO": "2027-01-01"}) == set()


def test_dias_de_expiracao_de_senha_so_inteiro_positivo():
    assert "DIASEXPSENHA" in _campos_com_erro({**VALIDO, "DIASEXPSENHA": "abc"})
    assert "DIASEXPSENHA" in _campos_com_erro({**VALIDO, "DIASEXPSENHA": "-5"})
    normalizados, erros = normalizar_e_validar(MODULO, {**VALIDO, "DIASEXPSENHA": "90"}, "incluir")
    assert erros == [] and gerar_payload(normalizados)["DIASEXPSENHA"] == 90


def test_operacao_invalida():
    assert _campos_com_erro(VALIDO, "excluir") == {"operacao"}


def test_booleanos():
    normalizados, _ = normalizar_e_validar(
        MODULO, {**VALIDO, "STATUS": False, "OIDC_ENABLED": True, "IGNORARAUTENTICACAOLDAP": True}, "incluir"
    )
    p = gerar_payload(normalizados)
    assert (p["STATUS"], p["OIDC_ENABLED"], p["IGNORARAUTENTICACAOLDAP"]) == (0, 1, "T")


# --- rotas --------------------------------------------------------------

def test_rota_modulos():
    r = client.get("/api/dataserver/modulos")
    assert r.status_code == 200
    m = r.json()[0]
    assert m["dataserver"] == "GlbUsuarioData" and m["campos"] and m["nao_validado"]
    assert m["campo_chave"] == "CODUSUARIO"  # usado pelo PUT em lote no conector


def test_rota_gerar_incluir_e_alterar():
    r = client.post("/api/dataserver/glb-usuario/gerar", json={"operacao": "incluir", "valores": VALIDO})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["payload"]["CODUSUARIO"] == "fulano.teste"
    assert corpo["nome_arquivo"] == "GlbUsuarioData_incluir_fulano.teste.json"
    assert any("POST" in i for i in corpo["instrucoes"])
    assert "SENHA" not in corpo["payload"]  # credencial nunca vai no payload

    r = client.post("/api/dataserver/glb-usuario/gerar", json={"operacao": "alterar", "valores": VALIDO})
    assert r.status_code == 200 and any("PUT" in i for i in r.json()["instrucoes"])


def test_rota_gerar_invalido_devolve_422_com_erros_por_campo():
    r = client.post("/api/dataserver/glb-usuario/gerar", json={"operacao": "incluir", "valores": {}})
    assert r.status_code == 422
    assert {e["campo"] for e in r.json()["detail"]["erros"]} == {"CODUSUARIO", "CODACESSO", "DATAINICIO"}


def test_rota_validar_com_avisos():
    r = client.post("/api/dataserver/glb-usuario/validar", json={
        "operacao": "incluir", "valores": {**VALIDO, "STATUS": False}})
    assert r.status_code == 200 and r.json()["valido"] is True
    assert any("INATIVO" in a for a in r.json()["avisos"])


def test_modulo_inexistente():
    assert client.post("/api/dataserver/nao-existe/gerar", json={"valores": {}}).status_code == 404


def test_log_de_uso_nao_guarda_valores_digitados():
    client.post("/api/dataserver/glb-usuario/gerar", json={"operacao": "incluir", "valores": VALIDO})
    db = SessionLocal()
    try:
        logs = db.query(RegistroUso).filter_by(ferramenta="dataserver").all()
        assert logs
        for linha in logs:
            assert "fulano" not in (linha.detalhes or "") and "exemplo.com" not in (linha.detalhes or "")
    finally:
        db.close()
