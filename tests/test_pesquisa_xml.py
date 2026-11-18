import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api._lib.pesquisa_xml import ItemXml, normalizar, pesquisar  # noqa: E402


def nomes(consulta, extras=None):
    return [i.nome for i in pesquisar(consulta, extras)]


def test_normalizar():
    assert normalizar("Requisição DE Material") == "requisicao de material"


def test_consulta_vazia():
    assert pesquisar("") == []
    assert pesquisar("   ") == []


def test_codigo_com_pontos():
    r = pesquisar("1.1.01")
    assert r and all(i.grupo == "1.1" for i in r)
    assert any(i.nome.startswith("1.1.01-") for i in r)


def test_codigo_sem_pontos_acha_formato_antigo():
    # "1101-Solicitação..." não tem pontos no nome.
    assert any(n.startswith("1101-") for n in nomes("1.1.01"))
    assert any(n.startswith("1.1.01-") for n in nomes("1101"))


def test_ignora_acento_e_maiuscula():
    assert nomes("REQUISICAO") == nomes("requisição") != []


def test_varias_palavras_em_qualquer_ordem():
    assert nomes("material compra") == nomes("compra material") != []


def test_busca_entre_grupos():
    grupos = {i.grupo for i in pesquisar("nota")}
    assert len(grupos) > 1


def test_sem_resultado():
    assert pesquisar("zzzxxxyyy") == []


def test_inclui_contribuidos():
    extra = ItemXml(grupo="2.1", nome="Meu pedido especial.xml", personalizado=True, id=7)
    r = pesquisar("especial", [extra])
    assert r == [extra]
