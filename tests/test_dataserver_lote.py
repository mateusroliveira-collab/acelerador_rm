import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from api._lib.dataserver.glb_usuario import MODULO, gerar_payload  # noqa: E402
from api._lib.dataserver.lote import MAX_LINHAS, LoteInvalido, processar_lote  # noqa: E402

CAB = "CODUSUARIO;NOME;EMAIL;CODACESSO;STATUS;DATAINICIO"


def lote(texto, operacao="incluir"):
    return processar_lote(MODULO, texto, operacao, gerar_payload)


def test_lote_valido_ponta_a_ponta():
    r = lote(f"{CAB}\nana.teste;Ana Teste;ana@exemplo.com;Acesso01;sim;18/11/2026\n"
             "bia.teste;Bia Teste;bia@exemplo.com;Acesso02;não;01/12/2026")
    assert (r["total"], r["validos"], r["invalidos"]) == (2, 2, 0)
    registros = [json.loads(l) for l in r["jsonl"].strip().splitlines()]
    assert registros[0]["CODUSUARIO"] == "ana.teste" and registros[0]["STATUS"] == 1
    assert registros[0]["DATAINICIO"] == "2026-11-18T00:00:00-03:00"  # dd/mm/aaaa convertido
    assert registros[1]["STATUS"] == 0
    assert r["nome_arquivo"].endswith("_lote.jsonl")
    assert json.loads(r["json"]) == registros
    assert any("Invoke-RestMethod -Method Post" in i for i in r["instrucoes"])


def test_colar_do_excel_usa_tabulacao():
    r = lote("CODUSUARIO\tCODACESSO\tDATAINICIO\nana.teste\tAcesso01\t18/11/2026")
    assert r["validos"] == 1


def test_cabecalho_por_rotulo_da_tela_e_sem_acento():
    r = lote("Usuário;Código de Acesso;Início de Validade;E-Mail\nana.teste;Acesso01;2026-11-18;ana@exemplo.com")
    assert r["validos"] == 1 and r["avisos_gerais"] == []


def test_erros_por_linha_com_numero_da_planilha():
    r = lote(f"{CAB}\nana.teste;Ana;ana@exemplo.com;Acesso01;sim;18/11/2026\n"
             ";Sem Codigo;email-ruim;;sim;31/02/2026")
    assert (r["validos"], r["invalidos"]) == (1, 1)
    ruim = r["linhas"][1]
    assert ruim["linha"] == 3 and not ruim["valido"]
    assert {e["campo"] for e in ruim["erros"]} >= {"CODUSUARIO", "CODACESSO", "EMAIL", "DATAINICIO"}
    assert len(r["jsonl"].strip().splitlines()) == 1  # inválida fica fora do arquivo


def test_usuario_repetido_no_arquivo():
    r = lote(f"{CAB}\nana.teste;A;;Acesso01;sim;18/11/2026\nANA.TESTE;B;;Acesso01;sim;18/11/2026")
    assert r["validos"] == 1
    erro = r["linhas"][1]["erros"][0]
    assert erro["campo"] == "CODUSUARIO" and "linha 2" in erro["mensagem"]


def test_coluna_desconhecida_e_coluna_obrigatoria_ausente_viram_avisos():
    r = lote("CODUSUARIO;XPTO\nana.teste;lixo")
    assert any("XPTO" in a for a in r["avisos_gerais"])
    assert any("Código de Acesso" in a for a in r["avisos_gerais"])
    assert r["validos"] == 0 and "jsonl" not in r


def test_alterar_gera_script_com_put_e_chave_na_url():
    r = lote(f"{CAB}\nana.teste;Ana;;Acesso01;sim;18/11/2026", operacao="alterar")
    script = next(i for i in r["instrucoes"] if "Invoke-RestMethod" in i)
    assert "-Method Put" in script and "$cod" in script and "-Encoding UTF8" in script
    assert '"SENHA"' not in r["jsonl"]  # credencial (a chave exata), não OBRIGAALTERARSENHA


def test_lote_nao_leva_senha_mesmo_que_venha_coluna():
    r = lote(f"{CAB};SENHA\nana.teste;Ana;;Acesso01;sim;18/11/2026;segredo123")
    assert "segredo123" not in r["jsonl"] and any("SENHA" in a for a in r["avisos_gerais"])


@pytest.mark.parametrize("texto", ["", "   ", CAB, "\n\n"])
def test_entradas_inuteis(texto):
    with pytest.raises(LoteInvalido):
        lote(texto)


def test_limite_de_linhas():
    linhas = "\n".join(f"u{i};Acesso01;18/11/2026" for i in range(MAX_LINHAS + 1))
    with pytest.raises(LoteInvalido):
        lote("CODUSUARIO;CODACESSO;DATAINICIO\n" + linhas)


def test_nenhuma_coluna_reconhecida():
    with pytest.raises(LoteInvalido):
        lote("foo;bar\n1;2")


# --- rotas -----------------------------------------------------------------

def test_rotas_lote_e_modelo():
    import os
    import tempfile

    for v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST", "VERCEL"):
        os.environ.pop(v, None)
    os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/lote.db"
    from fastapi.testclient import TestClient

    from api.index import app
    from api._lib.db import SessionLocal
    from api._lib.models import RegistroUso

    c = TestClient(app)
    modelo = c.get("/api/dataserver/glb-usuario/modelo-csv")
    assert modelo.status_code == 200 and "attachment" in modelo.headers["content-disposition"]
    texto = modelo.content.decode("utf-8-sig")
    assert texto.startswith("CODUSUARIO;") and "SENHA" not in texto.splitlines()[0].split(";")

    # o modelo, sem editar, tem que passar na própria validação
    r = c.post("/api/dataserver/glb-usuario/lote", json={"operacao": "incluir", "texto": texto})
    assert r.status_code == 200 and r.json()["validos"] == 1

    assert c.post("/api/dataserver/glb-usuario/lote", json={"operacao": "incluir", "texto": ""}).status_code == 400
    assert c.post("/api/dataserver/glb-usuario/lote", json={"operacao": "x", "texto": texto}).status_code == 422
    assert c.post("/api/dataserver/nao-existe/lote", json={"texto": texto}).status_code == 404

    db = SessionLocal()
    try:
        logs = db.query(RegistroUso).filter_by(acao="gerar-lote").all()
        assert logs and all("usuario.exemplo" not in (l.detalhes or "") for l in logs)
    finally:
        db.close()
