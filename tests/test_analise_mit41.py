import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST", "VERCEL"):
    os.environ.pop(_v, None)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/teste.db"

from fastapi.testclient import TestClient  # noqa: E402

from api.index import app  # noqa: E402
from api._lib.mit41.analise import (  # noqa: E402
    Candidato,
    MovimentoMit,
    analisar,
    analisar_movimento,
    grupo_pelos_requisitos,
    movimentos_de_texto,
)
from api._lib.mit41.requisitos import extrair_requisitos  # noqa: E402
from api._lib.regras_xml import RegraXml  # noqa: E402

client = TestClient(app)

NF_COMPRA = Candidato("1.2", "1.2.01-NF de Compra de Material.xml", RegraXml(
    codigo="1.2.01", nome="NF de Compra de Material", estoque="aumenta", financeiro="pagar",
    escritura_fiscal=True, natureza="E"))
NF_SERVICO = Candidato("1.2", "1.2.02-NF de Serviço.xml", RegraXml(
    codigo="1.2.02", nome="NF de Serviço", estoque="nenhum", financeiro="pagar",
    escritura_fiscal=True, natureza="E"))
NAO_USAR = Candidato("1.2", "1.2.95-NÃO UTILIZAR NF Compra de Material.xml", RegraXml(
    codigo="1.2.95", nome="NÃO UTILIZAR NF Compra de Material", estoque="aumenta", financeiro="pagar"))
REQUISICAO_1_1 = Candidato("1.1", "1.1.01-Requisição de Material.xml", RegraXml(
    codigo="1.1.01", nome="Requisição de Material", estoque="nenhum", financeiro="nenhum", natureza="E"))
AJUSTE_4_1 = Candidato("4.1", "4.1.03-Ajuste Negativo.xml", RegraXml(
    codigo="4.1.03", nome="Ajuste Negativo do Estoque", estoque="diminui", financeiro="nenhum"))

BIBLIOTECA = [NF_COMPRA, NF_SERVICO, REQUISICAO_1_1, AJUSTE_4_1]


def _mov(titulo, texto, numero="1"):
    return MovimentoMit(numero, titulo, texto, {"NOME_MOVIMENTO": titulo})


def test_pronto_quando_regra_e_nome_batem():
    r = analisar_movimento(_mov(
        "Compra de Material",
        "Lançamento da nota fiscal de entrada do fornecedor. Dá entrada no estoque. Gera contas a pagar.",
    ), BIBLIOTECA, {})
    assert r["status"] == "pronto"
    assert r["candidatos"][0]["arquivo"] == NF_COMPRA.arquivo
    assert r["confianca"] == "alta"
    assert r["ficha"]["ajustes"] == []


def test_ajustar_diz_o_parametro_e_a_frase_da_mit():
    r = analisar_movimento(_mov(
        "Compra de Material",
        "Dá entrada no estoque. Não gera financeiro; o pagamento é feito por outro sistema.",
    ), [NF_COMPRA], {})
    assert r["status"] == "ajustar"
    ajuste = r["ficha"]["ajustes"][0]
    assert ajuste["dimensao"] == "financeiro"
    assert ajuste["mit_pede"] == "não gera financeiro"
    assert ajuste["xml_base_faz"] == "gera financeiro a pagar"
    assert "PagouRecLan" in ajuste["propriedade"]
    assert ajuste["trecho"].startswith("Não gera financeiro")


def test_criar_quando_diverge_muito():
    r = analisar_movimento(_mov(
        "Venda de Produto",
        "Emissão de NF-e transmitida à SEFAZ. Baixa do estoque. Gera contas a receber. Contabiliza.",
    ), [NF_COMPRA], {})
    assert r["status"] == "criar"
    assert r["grupo"] == "2.2"
    assert r["ficha"]["xml_base"]["arquivo"] == NF_COMPRA.arquivo  # o mais próximo, como base
    assert r["ficha"]["codigo_sugerido"] == "2.2.01"


def test_sem_evidencia_nao_vira_pronto():
    r = analisar_movimento(_mov("Lançamento Diverso", "Movimento não gera integração fiscal."), [AJUSTE_4_1], {})
    assert r["status"] != "pronto"


def test_xml_de_outro_grupo_com_mesmo_nome_vira_ajustar_com_aviso():
    r = analisar_movimento(_mov(
        "Requisição de Material", "Movimento não gera integração fiscal. Não movimenta estoque.",
    ), BIBLIOTECA, {})
    assert r["candidatos"][0]["arquivo"] == REQUISICAO_1_1.arquivo
    if r["grupo"] != "1.1":
        assert r["status"] == "ajustar"
        assert any("grupo" in a for a in r["avisos"])


def test_ignora_xml_marcado_nao_utilizar():
    resultado = analisar([_mov("Compra de Material", "Dá entrada no estoque.")], extras=[NAO_USAR])
    arquivos = [c["arquivo"] for c in resultado["movimentos"][0]["candidatos"]]
    assert NAO_USAR.arquivo not in arquivos


def test_pendencias_e_ambiguidade():
    r = analisar_movimento(_mov(
        "Compra de Material", "Não gera financeiro. Gera contas a pagar ao fornecedor.",
    ), BIBLIOTECA, {})
    assert "financeiro" in r["requisitos"]["ambiguas"]
    assert any("contraditória" in a for a in r["avisos"])
    assert any(p.startswith("Estoque") for p in r["ficha"]["pendencias"])


def test_sem_dados_para_cadastro():
    r = analisar_movimento(_mov("Cadastro de Produtos", "O cadastro é mantido pela equipe."), BIBLIOTECA, {})
    assert r["status"] == "sem_dados"


def test_grupo_pelos_requisitos():
    g = lambda t: grupo_pelos_requisitos(extrair_requisitos(t))  # noqa: E731
    assert g("Saída do estoque de origem e entrada no estoque de destino.") == "3.1"
    assert g("Emissão de NF-e. Gera contas a receber.") == "2.2"
    assert g("Gera contas a pagar. Escriturada nos livros fiscais.") == "1.2"
    assert g("Baixa do estoque. Não gera financeiro.") == "4.1"
    assert g("Texto sem nada.") is None


MIT_BRUTA = """
4.1.1.1 Solicitação de Compras Processo Relacionado Movimentos | Compras Descrição
AS IS: Hoje a solicitação é feita por e-mail.
TO BE: A solicitação de compras passa por aprovação do gestor. Movimento não gera integração fiscal.
Não movimenta estoque.
GAP Nenhum
4.1.1.2 Recebimento de Materiais Processo Relacionado Movimentos | Compras Descrição
TO BE: O recebimento é feito a partir da Solicitação de Compras. Lançamento da nota fiscal de entrada
do fornecedor, escriturada nos livros fiscais. Dá entrada no estoque. Gera contas a pagar.
GAP Nenhum
"""


def test_mit_bruta_usa_to_be_e_acha_fluxo():
    movs = movimentos_de_texto(MIT_BRUTA)
    assert [m.numero for m in movs] == ["4.1.1.1", "4.1.1.2"]
    assert "e-mail" not in movs[0].texto  # AS IS fica de fora
    resultado = analisar(movs)
    rec = resultado["movimentos"][1]
    assert rec["requisitos"]["valores"]["estoque"] == "aumenta"
    assert rec["requisitos"]["valores"]["financeiro"] == "pagar"
    assert rec["grupo"] == "1.2"
    assert rec["fluxo"] == [{"numero": "4.1.1.1", "titulo": "Solicitação de Compras", "direcao": "origem",
                             "trecho": "O recebimento é feito a partir da Solicitação de Compras."}]
    assert resultado["resumo"]["total"] == 2


def test_saida_do_interpretador():
    texto = (
        "[INICIO_MOVIMENTO]\nNOME_MOVIMENTO=Baixa de Estoque\n"
        "[ESTOQUE] EFEITO_ESTOQUE=Diminui o saldo atual de estoque\n"
        "OBSERVACAO_FISCAL=Movimento não gera integração fiscal\n[FIM_MOVIMENTO]"
    )
    movs = movimentos_de_texto(texto)
    assert len(movs) == 1 and movs[0].titulo == "Baixa de Estoque"
    r = analisar(movs)["movimentos"][0]
    assert r["requisitos"]["valores"]["estoque"] == "diminui"
    assert r["candidatos"]


def test_rotas_de_analise():
    r = client.post("/api/xml/analisar-mit41", json={"texto": MIT_BRUTA})
    assert r.status_code == 200
    assert r.json()["resumo"]["total"] == 2
    assert client.post("/api/xml/analisar-mit41", json={"texto": "   "}).status_code == 400
    r = client.post("/api/xml/analisar-mit41-pdf", files={"arquivo": ("mit.pdf", b"nao e pdf")})
    assert r.status_code == 400
