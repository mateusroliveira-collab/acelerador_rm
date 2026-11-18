import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests" / "casos_mit41"))

from casos import CASOS  # noqa: E402
from api._lib.mit41.matcher import PISO_CONFIANCA, sugerir_grupos  # noqa: E402
from api._lib.mit41.sinonimos import achar_termo, normalizar_texto  # noqa: E402


@pytest.mark.parametrize("caso_id,campos,esperado", CASOS, ids=[c[0] for c in CASOS])
def test_casos_reais(caso_id, campos, esperado):
    r = sugerir_grupos(campos)
    if esperado is None:
        assert r == [], f"{caso_id}: não deveria sugerir nada, veio {r}"
    else:
        assert r and r[0]["grupo"] == esperado, f"{caso_id}: esperado {esperado}, veio {r}"


def test_piso_de_confianca_sempre_respeitado():
    for _, campos, _ in CASOS:
        assert all(s["pontuacao"] >= PISO_CONFIANCA for s in sugerir_grupos(campos))


def test_sinais_explicam_a_sugestao():
    r = sugerir_grupos({"NOME_MOVIMENTO": "Baixa de Estoque"})
    assert r[0]["grupo"] == "4.1" and r[0]["sinais"]


# --- limite de palavra (\b) ---------------------------------------------

def test_limite_de_palavra_nao_casa_dentro_de_outra_palavra():
    assert achar_termo("venda", normalizar_texto("Revenda de produtos")) is None
    assert achar_termo("baixa", normalizar_texto("baixar relatorio")) is None
    assert sugerir_grupos({"NOME_MOVIMENTO": "Revenda de produtos"}) == []


# --- plural e acento ------------------------------------------------------

@pytest.mark.parametrize("termo,texto", [
    ("requisicao de material", "Requisições de Materiais"),
    ("filial", "entre as filiais"),
    ("inventario", "INVENTÁRIO físico"),
    ("materia prima", "Matéria-prima"),
])
def test_plural_acento_e_hifen(termo, texto):
    achado = achar_termo(termo, normalizar_texto(texto))
    assert achado and achado[0] == "exato"


# --- busca aproximada -------------------------------------------------------

def test_erro_de_digitacao_e_reconhecido_como_aproximado():
    achado = achar_termo("transferencia", normalizar_texto("Tranferencia de estoque"))
    assert achado and achado[0] == "aproximado"
    r = sugerir_grupos({"NOME_MOVIMENTO": "Tranferencia entre filiais"})
    assert r and r[0]["grupo"] == "3.1"


def test_palavras_curtas_nao_usam_busca_aproximada():
    assert achar_termo("venda", normalizar_texto("vento")) is None
    assert achar_termo("baixa", normalizar_texto("caixa")) is None


def test_busca_aproximada_nao_gera_falso_positivo_entre_termos_parecidos():
    # "importacao" x "exportacao" e "compra" x "compre" ficam abaixo do limiar
    assert achar_termo("importacao", normalizar_texto("exportacao de mercadoria")) is None


# --- peso: termo específico vale mais que o genérico ----------------------

def test_termo_especifico_pesa_mais_que_o_generico():
    generico = sugerir_grupos({"NOME_MOVIMENTO": "Movimento de filial"})
    especifico = sugerir_grupos({"NOME_MOVIMENTO": "Transferência entre filiais"})
    assert especifico[0]["pontuacao"] > generico[0]["pontuacao"]


def test_nome_do_movimento_pesa_mais_que_o_processo_de_origem():
    so_origem = sugerir_grupos({"PROCESSO_ORIGEM": "Baixa de Estoque"})
    no_nome = sugerir_grupos({"NOME_MOVIMENTO": "Baixa de Estoque"})
    assert no_nome[0]["pontuacao"] > so_origem[0]["pontuacao"]


# --- regras que já existiam (não podem regredir) ------------------------------

def test_devolucao_de_compra_e_saida_e_devolucao_de_venda_e_entrada():
    assert sugerir_grupos({"NOME_MOVIMENTO": "Devolução de compra"})[0]["grupo"] == "2.2"
    assert sugerir_grupos({"NOME_MOVIMENTO": "Devolução de venda"})[0]["grupo"] == "1.2"


def test_dois_locais_diferentes_indicam_transferencia():
    r = sugerir_grupos({"LOCAL_ORIGEM": "Almoxarifado A", "LOCAL_DESTINO": "Almoxarifado B"})
    assert r and r[0]["grupo"] == "3.1"


def test_observacao_fiscal_nao_conta_como_efeito_fiscal():
    r = sugerir_grupos({
        "NOME_MOVIMENTO": "Solicitação de Compras",
        "OBSERVACAO_FISCAL": "Movimento não gera integração fiscal",
    })
    assert r[0]["grupo"] == "1.1"


def test_efeito_fiscal_de_entrada_nao_pontua_saida():
    r = sugerir_grupos({
        "NOME_MOVIMENTO": "Recebimento de Materiais",
        "PROCESSO_ORIGEM": "Compra do fornecedor",
        "DOCUMENTO_FISCAL": "Nota fiscal de entrada",
    })
    assert "2.2" not in [s["grupo"] for s in r]


# --- log de correção de sugestão (rota) ---------------------------------------

def test_rota_sugestao_corrigida_registra_so_quando_diverge():
    import os
    import tempfile

    for v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST", "VERCEL"):
        os.environ.pop(v, None)
    os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/m.db"
    from fastapi.testclient import TestClient

    from api.index import app
    from api._lib.db import SessionLocal
    from api._lib.models import RegistroUso

    c = TestClient(app)
    assert c.post("/api/xml/sugestao-corrigida", json={"sugerido": "1.1", "escolhido": "1.1"}).json() == {"registrado": False}
    assert c.post("/api/xml/sugestao-corrigida", json={"sugerido": "1.1", "escolhido": "9.9"}).status_code == 404
    r = c.post("/api/xml/sugestao-corrigida", json={"sugerido": "1.1", "escolhido": "1.2", "nome_movimento": "Teste"})
    assert r.json() == {"registrado": True}
    db = SessionLocal()
    try:
        assert db.query(RegistroUso).filter_by(acao="sugestao-corrigida").count() == 1
    finally:
        db.close()
