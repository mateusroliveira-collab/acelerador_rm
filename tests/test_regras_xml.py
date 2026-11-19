import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST", "VERCEL"):
    os.environ.pop(_v, None)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/teste.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.index import app  # noqa: E402
from api._lib import regras_xml  # noqa: E402
from api._lib.regras_xml import regra_da_biblioteca, regra_de_conteudo  # noqa: E402

client = TestClient(app)

NF_COMPRA = ("1.2", "1.2.01-NF de Compra de Material -Levi.xml")
NFE_VENDA = ("2.2", "2.2.02-NF-e (Venda de Materias - Imobilizado)-Levi.xml")
AJUSTE_NEG = ("4.1", "4.1.03-Ajuste (-) Negativo do Estoque-Levi.xml")
SOLICITACAO = ("1.1", "1.1.04-Solicitação de Compra-Levi.xml")


def _form(form, prop, valor):
    conteudo = "" if valor is None else f"<Conteudo>{valor}</Conteudo>"
    return f"<MovTMv{form}ParamsForm><ClassProps>{prop}</ClassProps>{conteudo}</MovTMv{form}ParamsForm>"


def _xml(*forms):
    return ("<?xml version='1.0'?><_x0030_4.06>" + "".join(forms) + "</_x0030_4.06>").encode()


def test_indice_em_dia_com_a_biblioteca():
    # Falhou? Rode: python scripts/gerar_indice_regras_xml.py
    calculado = regras_xml.calcular_indice()
    regras_xml._indice.cache_clear()
    assert regras_xml._indice() == calculado["regras"], "data/regras_xml.json desatualizado"
    assert len(calculado["regras"]) >= 100


def test_nf_de_compra():
    r = regra_da_biblioteca(*NF_COMPRA)
    assert (r.estoque, r.financeiro, r.escritura_fiscal, r.natureza) == ("aumenta", "pagar", True, "E")
    assert r.contabiliza and r.cfop
    assert r.classificacao == "04.06.05"


def test_nfe_de_venda():
    r = regra_da_biblioteca(*NFE_VENDA)
    assert (r.estoque, r.financeiro, r.natureza) == ("diminui", "receber", "S")
    assert r.emite_nfe and r.escritura_fiscal


def test_ajuste_negativo_e_solicitacao():
    aj = regra_da_biblioteca(*AJUSTE_NEG)
    assert (aj.estoque, aj.financeiro, aj.escritura_fiscal) == ("diminui", "nenhum", False)
    sc = regra_da_biblioteca(*SOLICITACAO)
    assert (sc.estoque, sc.financeiro) == ("nenhum", "nenhum")
    assert "1.1.07" in sc.segue_para


def test_regra_a_partir_de_propriedades():
    r = regra_de_conteudo(_xml(
        _form("Mov", "CodTipoMovimento", "9.9.01"),
        _form("EstoqueEstoque", "EfeitoSaldoA2", "D"),
        _form("EstoqueEstoque", "EfeitoSaldoB2", "D"),
        _form("EstoqueEstoque", "EfeitoSaldoA3", "A"),
        _form("FinanceiroFaturamento", "Fatura", "true"),
        _form("FinanceiroFaturamento", "PagouRecLan", "1"),
        _form("Orcamento", "EfeitoNoSaldoOrcamento", "D"),
        _form("MovDados", "UsaAprovacao", "1"),
        _form("FiscalNFe", "NFeMunicipal", "1"),
        _form("Contabilidade", "UsarEventoCtb", "0"),
    ))
    assert r.codigo == "9.9.01"
    assert r.estoque == "diminui"
    assert r.outros_saldos == ["Saldo A3 aumenta"]
    assert r.financeiro == "receber"
    assert r.orcamento == "estorna"
    assert r.aprovacao and r.emite_nfse and not r.contabiliza
    assert any("RECEBER" in f for f in r.resumo())


def test_fatura_desligada_nao_gera_financeiro():
    r = regra_de_conteudo(_xml(
        _form("FinanceiroFaturamento", "Fatura", "false"),
        _form("FinanceiroFaturamento", "PagouRecLan", "2"),
    ))
    assert r.financeiro == "nenhum"


@pytest.mark.parametrize("conteudo", [b"isto nao e xml", b"<a><b>1</b></a>"])
def test_xml_invalido_ou_de_outro_tipo(conteudo):
    with pytest.raises(ValueError):
        regra_de_conteudo(conteudo)


@pytest.mark.parametrize("nome", ["../Movimentos do tipo 1.2/" + NF_COMPRA[1], "nao-existe.xml"])
def test_biblioteca_nao_sai_da_pasta_do_grupo(nome):
    regras_xml._indice.cache_clear()
    assert regra_da_biblioteca("1.1", nome) is None
    assert regra_da_biblioteca("9.9", "x.xml") is None


def test_rota_regra_biblioteca():
    r = client.get("/api/xml/regra", params={"grupo": NF_COMPRA[0], "arquivo": NF_COMPRA[1]})
    assert r.status_code == 200
    regra = r.json()["regra"]
    assert regra["estoque"] == "aumenta" and regra["financeiro"] == "pagar"
    assert regra["resumo"]
    assert client.get("/api/xml/regra").status_code == 400
    assert client.get("/api/xml/regra", params={"grupo": "1.1", "arquivo": "x.xml"}).status_code == 404


def test_rota_regra_personalizado():
    xml = _xml(_form("Mov", "CodTipoMovimento", "1.1.99"), _form("EstoqueEstoque", "EfeitoSaldoA2", "A"))
    r = client.post("/api/xml/enviar", params={"grupo": "1.1"}, files={"arquivo": ("regra_teste.xml", xml)})
    assert r.status_code == 200
    xml_id = r.json()["id"]
    r = client.get("/api/xml/regra", params={"id": xml_id})
    assert r.status_code == 200
    assert r.json()["regra"]["estoque"] == "aumenta"
    assert client.get("/api/xml/regra", params={"id": 999999}).status_code == 404
