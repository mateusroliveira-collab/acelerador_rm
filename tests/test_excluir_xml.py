import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Banco descartável, definido ANTES de importar a API.
for _v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST", "VERCEL"):
    os.environ.pop(_v, None)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/teste.db"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from api.index import app  # noqa: E402
from api._lib.db import SessionLocal, engine, criar_tabelas  # noqa: E402
from api._lib.models import RegistroUso, XmlPersonalizado  # noqa: E402

client = TestClient(app)
XML = b"<?xml version='1.0'?><a><b>1</b></a>"


def _enviar(nome="meu_teste_exclusao.xml", grupo="1.1"):
    r = client.post("/api/xml/enviar", params={"grupo": grupo}, files={"arquivo": (nome, XML)})
    assert r.status_code == 200
    return r.json()["id"]


def _nomes_busca(grupo="1.1"):
    return [a["nome"] for a in client.get("/api/xml/buscar", params={"grupo": grupo}).json()["arquivos"]]


def test_exclusao_reversivel_esconde_das_buscas_e_registra_log():
    xml_id = _enviar()
    assert "meu_teste_exclusao.xml" in _nomes_busca()
    assert client.get("/api/xml/pesquisar", params={"q": "meu_teste_exclusao"}).json()["total"] == 1

    r = client.delete(f"/api/xml/personalizado/{xml_id}")
    assert r.status_code == 200

    assert "meu_teste_exclusao.xml" not in _nomes_busca()
    assert client.get("/api/xml/pesquisar", params={"q": "meu_teste_exclusao"}).json()["total"] == 0
    assert client.get(f"/api/xml/baixar-personalizado/{xml_id}").status_code == 404

    db = SessionLocal()
    try:
        linha = db.query(XmlPersonalizado).filter_by(id=xml_id).one()  # linha continua lá
        assert linha.excluido is True and linha.excluido_em is not None
        assert db.query(RegistroUso).filter_by(acao="excluir-personalizado").count() >= 1
    finally:
        db.close()


def test_excluir_duas_vezes_ou_id_inexistente_da_404():
    xml_id = _enviar("outro_teste.xml")
    assert client.delete(f"/api/xml/personalizado/{xml_id}").status_code == 200
    assert client.delete(f"/api/xml/personalizado/{xml_id}").status_code == 404
    assert client.delete("/api/xml/personalizado/999999").status_code == 404


def test_xml_fixo_nunca_e_afetado():
    antes = _nomes_busca()
    client.delete("/api/xml/personalizado/1")
    assert [n for n in antes if n.startswith("1.1.01")] == [n for n in _nomes_busca() if n.startswith("1.1.01")]


def test_migracao_adiciona_colunas_em_tabela_antiga():
    with engine.begin() as c:
        c.execute(text("DROP TABLE xml_personalizado"))
        c.execute(text(
            "CREATE TABLE xml_personalizado (id INTEGER PRIMARY KEY, criado_em DATETIME, grupo VARCHAR(10),"
            " nome_arquivo VARCHAR(255), conteudo_original TEXT, conteudo_limpo TEXT, campos_zerados INTEGER)"
        ))
        c.execute(text("INSERT INTO xml_personalizado (id, grupo, nome_arquivo) VALUES (1, '1.1', 'antigo.xml')"))
    criar_tabelas()
    criar_tabelas()  # idempotente
    assert "antigo.xml" in _nomes_busca()  # linha antiga continua visível
    assert client.delete("/api/xml/personalizado/1").status_code == 200
    assert "antigo.xml" not in _nomes_busca()
