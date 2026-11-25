"""Modelo .xlsx, validação da planilha preenchida, planilha marcada com erros e saída XML."""
import base64
import io
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST", "VERCEL",
           "API_KEYS", "API_EXIGIR_CHAVE", "RATE_LIMIT_POR_MINUTO"):
    os.environ.pop(_v, None)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/xlsx.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook, load_workbook  # noqa: E402

from api.index import app  # noqa: E402
from api._lib.dataserver import xlsx as px  # noqa: E402
from api._lib.dataserver.glb_usuario import MODULO, gerar_payload  # noqa: E402
from api._lib.dataserver.xml_saida import gerar_xml  # noqa: E402
from api._lib.db import SessionLocal  # noqa: E402
from api._lib.models import Cliente, RegistroUso  # noqa: E402

client = TestClient(app)
V1 = "/api/v1/dataserver"

# Cabeçalho = nomes técnicos do RM, na ordem do GET de GlbUsuarioData (sem id,
# credenciais e campos controlados pelo RM).
CABECALHOS = [
    "CODUSUARIO", "NOME", "CODACESSO", "STATUS", "DATAINICIO", "IGNORARAUTENTICACAOLDAP",
    "DATAEXPIRACAO", "CODUSUARIOREDE", "DOMINIOREDE", "EMAIL", "NOMESOCIAL", "CODEXTERNO",
    "INTEGRADOFLUIG", "OIDC_ENABLED", "CONFIRMABTNOK", "ULTIMACOLIGADA", "DIASEXPSENHA",
    "OBRIGAALTERARSENHA", "ACESSONET", "LIVEID", "USUARIOTWITTER", "USUARIOFACEBOOK",
    "USUARIOLINKEDIN", "FULLDETERMINED", "USERID", "USERIDFLUIGIDENTITY",
]
COL = {nome: i for i, nome in enumerate(CABECALHOS, start=1)}  # nome do campo -> coluna do Excel


def _modelo_bytes():
    return px.gerar_modelo_xlsx(MODULO)


def _preencher(linhas: dict, modelo: bytes | None = None) -> bytes:
    """linhas: {numero_da_linha_excel: {NOME_DO_CAMPO: valor}}"""
    wb = load_workbook(io.BytesIO(modelo or _modelo_bytes()))
    ws = wb["Dados"]
    for n, cols in linhas.items():
        for campo, valor in cols.items():
            ws.cell(row=n, column=COL[campo], value=valor)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _validar(conteudo: bytes, operacao="incluir", cliente=None, nome="x.xlsx"):
    params = {"operacao": operacao}
    if cliente:
        params["cliente"] = cliente
    return client.post(f"{V1}/glb-usuario/lote-xlsx", params=params, files={"arquivo": (nome, conteudo, px.TIPO_MIME)})


ANA = {"CODUSUARIO": "ana.teste", "NOME": "Ana Teste", "EMAIL": "ana@exemplo.com", "CODACESSO": "Acesso01",
       "STATUS": 1, "OIDC_ENABLED": 0, "IGNORARAUTENTICACAOLDAP": "F", "DATAINICIO": datetime(2026, 12, 1)}


# --- modelo ------------------------------------------------------------------

def test_modelo_tem_cabecalhos_abas_validacoes_e_protecao():
    wb = load_workbook(io.BytesIO(_modelo_bytes()))
    assert wb.sheetnames == ["Dados", "Listas", "Instruções", "_meta"]
    assert wb["_meta"].sheet_state == "hidden"
    ws = wb["Dados"]
    assert [c.value for c in ws[1]] == CABECALHOS
    assert ws.freeze_panes == "A2" and ws.protection.sheet is True
    assert ws["A1"].fill.fgColor.rgb.endswith("FFF2CC") and ws["B1"].fill.fgColor.rgb.endswith("EFEFEF")
    assert "Usuário" in ws["A1"].comment.text  # a dica traz o rótulo da tela do RM
    assert ws["A1"].comment is not None
    assert ws["A2"].protection.locked is False and ws["A1"].protection.locked is True
    assert len(ws.data_validations.dataValidation) >= 8  # acesso, 4 sim/não, 2 datas, inteiros, e-mail
    formulas = {dv.formula1 for dv in ws.data_validations.dataValidation}
    assert "Listas!$A$2:$A$200" in formulas
    assert '"1,0"' in formulas and '"T,F"' in formulas  # booleanos como o RM grava
    assert '"Sim,Não"' not in formulas
    # aba Instruções traz o dicionário dos campos
    wi = wb["Instruções"]
    assert {wi.cell(row=i, column=1).value for i in range(1, wi.max_row + 1)} >= set(CABECALHOS)


def test_cabecalhos_do_modelo_mapeiam_todos_os_campos():
    from api._lib.dataserver.lote import mapear_colunas
    mapa, ignoradas = mapear_colunas(MODULO, CABECALHOS)
    assert ignoradas == [] and [mapa[i] for i in range(len(CABECALHOS))] == [c.nome for c in MODULO.campos]


def test_planilha_antiga_com_rotulos_continua_sendo_lida():
    from api._lib.dataserver.lote import mapear_colunas
    antigos = ["Usuário *", "Nome", "Código de Acesso *", "Ativo", "Início de Validade *", "Login OIDC *"]
    mapa, ignoradas = mapear_colunas(MODULO, antigos)
    assert ignoradas == [] and list(mapa.values()) == ["CODUSUARIO", "NOME", "CODACESSO", "STATUS",
                                                        "DATAINICIO", "OIDC_ENABLED"]


def test_rota_do_modelo_baixa_um_xlsx_valido():
    r = client.get(f"{V1}/glb-usuario/modelo-xlsx")
    assert r.status_code == 200 and r.headers["content-type"].startswith(px.TIPO_MIME)
    assert "attachment" in r.headers["content-disposition"]
    assert load_workbook(io.BytesIO(r.content)).sheetnames[0] == "Dados"


def test_modelo_do_cliente_ja_vem_com_os_codigos_de_acesso():
    db = SessionLocal()
    try:
        db.query(Cliente).filter_by(codigo="xlsx-cli").delete()
        db.add(Cliente(codigo="xlsx-cli", ativo=True, config=json.dumps({"glb-usuario": {"codigos_acesso": ["Fin01", "Rh02"]}})))
        db.commit()
    finally:
        db.close()
    r = client.get(f"{V1}/glb-usuario/modelo-xlsx", params={"cliente": "xlsx-cli"})
    wl = load_workbook(io.BytesIO(r.content))["Listas"]
    assert [wl.cell(row=i, column=1).value for i in (2, 3, 4)] == ["Fin01", "Rh02", None]
    # sem cliente: códigos de exemplo + aviso
    wl0 = load_workbook(io.BytesIO(_modelo_bytes()))["Listas"]
    assert wl0["A2"].value == "Acesso01" and "EXEMPLO" in str(wl0["C1"].value)


def test_modelo_vazio_nao_tem_o_que_validar():
    r = _validar(_modelo_bytes())
    assert r.status_code == 400 and "Nenhuma linha" in r.json()["detail"]


# --- validação da planilha preenchida -----------------------------------------------

def test_planilha_preenchida_valida_e_gera_json_e_xml():
    ok = {**ANA, "CODUSUARIO": "bia.teste", "CODACESSO": "Acesso02"}
    r = _validar(_preencher({2: ANA, 3: ok}))
    corpo = r.json()
    assert r.status_code == 200 and (corpo["total"], corpo["validos"], corpo["invalidos"]) == (2, 2, 0)
    registros = [json.loads(l) for l in corpo["jsonl"].strip().splitlines()]
    assert registros[0]["CODUSUARIO"] == "ana.teste" and registros[0]["STATUS"] == 1
    assert registros[0]["DATAINICIO"] == "2026-12-01T00:00:00-03:00"  # data real do Excel
    assert "anotado_b64" not in corpo
    assert corpo["xml"].startswith('<?xml version="1.0" encoding="utf-8"?>\n<GlbUsuario>')
    assert corpo["xml"].count("<GUSUARIO>") == 2 and "<CODUSUARIO>ana.teste</CODUSUARIO>" in corpo["xml"]
    assert corpo["nome_arquivo_xml"].endswith(".xml")
    # JSON baixado = formato do GET (envelope + todas as chaves, na ordem do RM)
    get = json.loads(corpo["json"])
    assert list(get) == ["messages", "length", "data"] and get["length"] == 2
    assert get["data"][0]["id"] == "ana.teste" and get["data"][0]["SENHA"] is None


def test_booleanos_e_data_como_texto_do_excel():
    linha = {**ANA, "STATUS": True, "OIDC_ENABLED": False, "DATAINICIO": "01/12/2026", "DIASEXPSENHA": 90.0}
    corpo = _validar(_preencher({2: linha})).json()
    reg = json.loads(corpo["jsonl"])
    assert corpo["validos"] == 1 and reg["STATUS"] == 1 and reg["OIDC_ENABLED"] == 0
    assert reg["DIASEXPSENHA"] == 90 and reg["DATAINICIO"].startswith("2026-12-01")


def test_valores_no_formato_do_rm_e_sim_nao_antigo():
    rm = {**ANA, "STATUS": "0", "OIDC_ENABLED": "1", "IGNORARAUTENTICACAOLDAP": "T", "OBRIGAALTERARSENHA": 0}
    antigo = {**ANA, "CODUSUARIO": "bia.teste", "STATUS": "Não", "IGNORARAUTENTICACAOLDAP": "Sim"}
    corpo = _validar(_preencher({2: rm, 3: antigo})).json()
    assert corpo["validos"] == 2
    a, b = [json.loads(l) for l in corpo["jsonl"].strip().splitlines()]
    assert (a["STATUS"], a["OIDC_ENABLED"], a["IGNORARAUTENTICACAOLDAP"], a["OBRIGAALTERARSENHA"]) == (0, 1, "T", 0)
    assert (b["STATUS"], b["IGNORARAUTENTICACAOLDAP"]) == (0, "T")


def test_erros_usam_o_numero_da_linha_do_excel_mesmo_com_linhas_em_branco_no_meio():
    # linhas 2 (ok), 3 e 4 em branco, 5 (erro: sem código de acesso e e-mail ruim), 6 (usuário repetido)
    ruim = {**ANA, "CODUSUARIO": "bia.teste", "CODACESSO": None, "EMAIL": "email-ruim"}
    repetida = {**ANA}
    corpo = _validar(_preencher({2: ANA, 5: ruim, 6: repetida})).json()
    assert (corpo["total"], corpo["validos"], corpo["invalidos"]) == (3, 1, 2)
    por_linha = {l["linha"]: l for l in corpo["linhas"]}
    assert set(por_linha) == {2, 5, 6}  # numeração da planilha, não da lista
    assert {e["campo"] for e in por_linha[5]["erros"]} == {"EMAIL", "CODACESSO"}
    assert por_linha[6]["erros"][0]["campo"] == "CODUSUARIO"
    assert len(corpo["jsonl"].strip().splitlines()) == 1


def test_planilha_marcada_devolve_o_mesmo_arquivo_com_celulas_vermelhas_e_comentarios():
    ruim = {**ANA, "CODUSUARIO": "bia.teste", "CODACESSO": None, "EMAIL": "email-ruim"}
    corpo = _validar(_preencher({2: ANA, 5: ruim})).json()
    marcada = base64.b64decode(corpo["anotado_b64"])
    wb = load_workbook(io.BytesIO(marcada))
    ws = wb["Dados"]
    assert wb.sheetnames[0] == "Erros"
    assert ws["J5"].fill.fgColor.rgb.endswith("F4C7C3") and "e-mail" in ws["J5"].comment.text.lower()  # EMAIL
    assert ws["C5"].fill.fgColor.rgb.endswith("F4C7C3") and "obrigatório" in ws["C5"].comment.text  # CODACESSO
    assert ws["A2"].fill.fgColor.rgb != ws["J5"].fill.fgColor.rgb  # linha válida não é marcada
    assert len(ws.data_validations.dataValidation) >= 8  # as validações do modelo continuam lá
    assert wb["Erros"]["B1"].value == "CODUSUARIO"
    assert wb["Erros"]["A2"].value == 5 and wb["Erros"]["B2"].value == "bia.teste"
    # a planilha marcada pode ser validada de novo (é um xlsx comum)
    assert _validar(marcada).status_code == 200


def test_modelo_antigo_gera_aviso_de_versao():
    wb = load_workbook(io.BytesIO(_preencher({2: ANA})))
    wb["_meta"]["B2"] = "0"
    buf = io.BytesIO()
    wb.save(buf)
    corpo = _validar(buf.getvalue()).json()
    assert any("desatualizado" in a for a in corpo["avisos_gerais"])


def test_alterar_funciona_com_planilha():
    corpo = _validar(_preencher({2: ANA}), operacao="alterar").json()
    assert corpo["validos"] == 1 and any("-Method Put" in i for i in corpo["instrucoes"])


def test_lista_do_cliente_vale_para_a_planilha():
    db = SessionLocal()
    try:
        db.query(Cliente).filter_by(codigo="xlsx-lista").delete()
        db.add(Cliente(codigo="xlsx-lista", ativo=True, config=json.dumps({"glb-usuario": {"codigos_acesso": ["Fin01"]}})))
        db.commit()
    finally:
        db.close()
    corpo = _validar(_preencher({2: ANA}), cliente="xlsx-lista").json()  # Acesso01 não está na lista dele
    assert corpo["invalidos"] == 1 and corpo["linhas"][0]["erros"][0]["campo"] == "CODACESSO"


# --- segurança do upload -------------------------------------------------------------

def test_arquivos_invalidos_sao_recusados_com_mensagem_clara():
    assert _validar(b"isso nao e um xlsx").status_code == 400
    assert _validar(b"").status_code == 400

    com_macro = io.BytesIO()
    with zipfile.ZipFile(com_macro, "w") as z:
        z.writestr("xl/workbook.xml", "<x/>")
        z.writestr("xl/vbaProject.bin", b"macro")
    r = _validar(com_macro.getvalue())
    assert r.status_code == 400 and "macro" in r.json()["detail"]

    grande = _validar(b"0" * (px.MAX_BYTES + 10))
    assert grande.status_code == 400 and "grande" in grande.json()["detail"]

    zip_qualquer = io.BytesIO()
    with zipfile.ZipFile(zip_qualquer, "w") as z:
        z.writestr("leiame.txt", "oi")
    assert _validar(zip_qualquer.getvalue()).status_code == 400


def test_zip_bomb_e_recusado(monkeypatch):
    monkeypatch.setattr(px, "MAX_DESCOMPACTADO", 100)
    r = _validar(_modelo_bytes())
    assert r.status_code == 400 and "descompactado" in r.json()["detail"]


def test_operacao_invalida_e_modulo_inexistente():
    assert _validar(_preencher({2: ANA}), operacao="excluir").status_code == 422
    r = client.post(f"{V1}/nao-existe/lote-xlsx", files={"arquivo": ("x.xlsx", b"x", px.TIPO_MIME)})
    assert r.status_code == 404


def test_log_nao_guarda_dados_da_planilha():
    _validar(_preencher({2: ANA}))
    db = SessionLocal()
    try:
        logs = db.query(RegistroUso).filter_by(acao="gerar-lote-xlsx").all()
        assert logs and all("ana.teste" not in (l.detalhes or "") and "exemplo.com" not in (l.detalhes or "") for l in logs)
    finally:
        db.close()


# --- saída XML ------------------------------------------------------------------------

def test_xml_escapa_caracteres_especiais():
    payload = gerar_payload({"CODUSUARIO": "a&b", "NOME": "Fulano <Teste> \"x\"", "CODACESSO": "Acesso01", "STATUS": True,
                             "OIDC_ENABLED": False, "DATAINICIO": datetime(2026, 1, 1).date()})
    xml = gerar_xml(MODULO, [payload])
    assert "<CODUSUARIO>a&amp;b</CODUSUARIO>" in xml and "&lt;Teste&gt;" in xml
    import xml.etree.ElementTree as ET
    assert ET.fromstring(xml.encode("utf-8")).tag == "GlbUsuario"  # XML bem formado


def test_xml_vazio_quando_nao_ha_registros():
    assert gerar_xml(MODULO, []) is None
