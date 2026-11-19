import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from api._lib.mit41.requisitos import (  # noqa: E402
    citacoes_de_movimentos,
    extrair_requisitos,
    extrair_requisitos_de_campos,
)


def _v(texto, dim):
    return extrair_requisitos(texto).valor(dim)


@pytest.mark.parametrize("texto,esperado", [
    ("O recebimento dará entrada no estoque do almoxarifado.", "aumenta"),
    ("A nota fiscal aumenta o saldo de estoque.", "aumenta"),
    ("A requisição faz a baixa do estoque no momento do atendimento.", "diminui"),
    ("O consumo do material diminui o saldo atual de estoque.", "diminui"),
    ("Movimento não movimenta estoque.", "nenhum"),
    ("Sem efeito no estoque.", "nenhum"),
    ("Saída do estoque de origem e entrada no estoque de destino.", "transfere"),
    ("A solicitação é aprovada pelo gestor.", None),  # não fala de estoque
])
def test_estoque(texto, esperado):
    assert _v(texto, "estoque") == esperado


@pytest.mark.parametrize("texto,esperado", [
    ("Gera título no contas a pagar com vencimento conforme condição de pagamento.", "pagar"),
    ("O pagamento ao fornecedor é provisionado no financeiro.", "pagar"),
    ("Gera contas a receber e boleto para o cliente.", "receber"),
    ("Integra com o financeiro gerando lançamento a pagar.", "pagar"),
    ("Integra com o financeiro.", "gera"),
    ("Não gera financeiro.", "nenhum"),
    ("Não há títulos nesta etapa.", "nenhum"),
])
def test_financeiro(texto, esperado):
    assert _v(texto, "financeiro") == esperado


def test_negacao_fiscal_vence_na_mesma_frase():
    assert _v("Movimento não gera integração fiscal.", "escritura_fiscal") == "nao"
    assert _v("A nota é escriturada nos livros fiscais.", "escritura_fiscal") == "sim"
    assert _v("Gera apuração de ICMS e IPI.", "escritura_fiscal") == "sim"


def test_contradicao_vira_ambigua_com_as_duas_evidencias():
    req = extrair_requisitos("Não gera financeiro. Gera contas a pagar ao fornecedor.")
    assert req.valor("financeiro") is None
    assert "financeiro" in req.ambiguas()
    assert {e.valor for e in req.evidencias["financeiro"]} == {"nenhum", "pagar"}


def test_nfe_emissao_vs_entrada_de_nota_do_fornecedor():
    assert _v("Emissão de NF-e transmitida à SEFAZ.", "emite_nfe") == "sim"
    assert _v("Importação do XML da NF-e recebida do fornecedor.", "emite_nfe") is None
    assert _v("Emissão de NFS-e na prefeitura.", "emite_nfse") == "sim"
    assert _v("Emissão de NFS-e na prefeitura.", "emite_nfe") is None
    assert _v("Lançamento da nota fiscal de entrada do fornecedor.", "natureza") == "E"
    assert _v("Emite nota fiscal de venda.", "natureza") == "S"


def test_orcamento_nao_confunde_com_orcamento_de_venda():
    assert _v("Consome o saldo orçamentário do centro de custo.", "orcamento") == "afeta"
    assert _v("A devolução estorna o orçamento consumido.", "orcamento") == "estorna"
    assert _v("O vendedor envia o orçamento ao cliente.", "orcamento") is None
    assert _v("Não há controle orçamentário.", "orcamento") == "nenhum"


def test_contabil_aprovacao_contrato():
    assert _v("Contabiliza pelo evento contábil 22.", "contabiliza") == "sim"
    assert _v("Não gera contabilização.", "contabiliza") == "nao"
    assert _v("Passa por aprovação por alçada no Fluig.", "aprovacao") == "sim"
    assert _v("Não necessita aprovação.", "aprovacao") == "nao"
    assert _v("Ao final é gerado o contrato com o fornecedor.", "gera_contrato") is None
    assert _v("O pedido gera o contrato de fornecimento.", "gera_contrato") == "sim"


def test_trecho_e_a_frase_original_com_acento():
    req = extrair_requisitos("Primeira frase qualquer. Movimento não gera integração fiscal.")
    assert req.evidencias["escritura_fiscal"][0].trecho == "Movimento não gera integração fiscal."


def test_campos_do_interpretador():
    req = extrair_requisitos_de_campos({
        "NOME_MOVIMENTO": "Baixa de Estoque",
        "EFEITO_ESTOQUE": "Diminui o saldo atual de estoque",
        "OBSERVACAO_FISCAL": "Movimento não gera integração fiscal",
    })
    assert req.valor("estoque") == "diminui"
    assert req.valor("escritura_fiscal") == "nao"
    req = extrair_requisitos_de_campos({"EFEITO_ESTOQUE": "Nenhum", "DOCUMENTO_FISCAL": "NF-e de entrada"})
    assert req.valor("estoque") == "nenhum"
    assert req.valor("natureza") == "E"
    # Caso real (MIT anonimizada): serviço com retenções.
    req = extrair_requisitos_de_campos({
        "DOCUMENTO_FISCAL": "Nota fiscal de serviço do fornecedor",
        "RETENCOES": "ISS, INSS, PIS/COFINS/CSLL, IRRF retidos",
    })
    assert req.valor("natureza") == "E"
    assert req.valor("escritura_fiscal") == "sim"


def test_para_dict_tem_todas_as_dimensoes():
    d = extrair_requisitos("Gera contas a pagar.").para_dict()
    assert d["valores"]["financeiro"] == "pagar"
    assert d["valores"]["estoque"] is None
    assert set(d["valores"]) >= {"estoque", "financeiro", "escritura_fiscal", "orcamento"}


def test_citacoes_de_outros_movimentos():
    titulos = {"4.1.1.3": "Ordem de Compra", "4.1.1.1": "Solicitação de Compras", "4.1.1.9": "Inventário"}
    texto = (
        "A cotação é criada a partir da Solicitação de Compras aprovada. "
        "O vencedor gera a Ordem de Compra para o fornecedor."
    )
    c = {x["numero"]: x["direcao"] for x in citacoes_de_movimentos(texto, titulos)}
    assert c == {"4.1.1.1": "origem", "4.1.1.3": "destino"}
