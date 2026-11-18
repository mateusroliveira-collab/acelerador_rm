"""
Casos reais para o matcher de MIT 41, extraídos de um MIT041 de
Gestão de Estoque, Compras e Contratos (documento de levantamento de
um projeto RM). Só nomes de processo e frases de "Integrações do
movimento" -- sem nome de cliente, e-mail ou dado de pessoa.

Cada caso: (id, campos como o interpretador devolveria, grupo esperado
como 1ª sugestão -- ou None quando NÃO deve haver sugestão).

ATENÇÃO: o MIT não traz o grupo, então o "esperado" é a classificação
do analista a partir do significado de negócio (ver config.GRUPOS).
Conferir/ajustar se algum caso estiver errado.
"""

CASOS = [
    ("requisicao-materiais", {
        "NOME_MOVIMENTO": "Requisição de Materiais",
        "PROCESSO_ORIGEM": "Requisição de Materiais",
        "OBSERVACAO_FISCAL": "Movimento não gera integração fiscal",
    }, "4.1"),
    ("baixa-estoque", {
        "NOME_MOVIMENTO": "Baixa de Estoque",
        "PROCESSO_ORIGEM": "Requisição de Materiais",
        "EFEITO_ESTOQUE": "Diminui o saldo atual de estoque",
        "OBSERVACAO_FISCAL": "Movimento não gera integração fiscal",
    }, "4.1"),
    ("inventario", {
        "NOME_MOVIMENTO": "Inventário",
        "PROCESSO_ORIGEM": "Contagem física dos itens de estoque",
    }, "4.1"),
    ("ajuste-estoque", {
        "NOME_MOVIMENTO": "Ajuste de Estoque",
        "PROCESSO_ORIGEM": "Inventário -- ajuste a maior ou a menor no estoque",
    }, "4.1"),
    ("solicitacao-compras", {
        "NOME_MOVIMENTO": "Solicitação de Compras",
        "PROCESSO_ORIGEM": "Requisição de Materiais",
        "OBSERVACAO_FISCAL": "Movimento não gera integração fiscal",
    }, "1.1"),
    ("ordem-compra", {
        "NOME_MOVIMENTO": "Ordem de Compra",
        "PROCESSO_ORIGEM": "Cotação -- mapa de cotação com vencedor",
        "PROCESSO_DESTINO": "Recebimento de Materiais",
        "OBSERVACAO_FISCAL": "Movimento não gera integração fiscal",
    }, "1.1"),
    ("solicitacao-servicos", {
        "NOME_MOVIMENTO": "Solicitação de Serviços",
        "PROCESSO_DESTINO": "Aquisição de Serviços (compra de serviço)",
        "OBSERVACAO_FISCAL": "Movimento não gera integração fiscal",
    }, "1.1"),
    ("recebimento-materiais", {
        "NOME_MOVIMENTO": "Recebimento de Materiais",
        "PROCESSO_ORIGEM": "Ordem de Compra enviada ao fornecedor",
        "DOCUMENTO_FISCAL": "Nota fiscal de entrada (NF-e) de compra",
        "TRIBUTACAO": "ICMS e IPI: informar alíquota e valor total",
    }, "1.2"),
    ("recebimento-ativo", {
        "NOME_MOVIMENTO": "Recebimento de Ativo Imobilizado",
        "PROCESSO_ORIGEM": "Ordem de Compra enviada ao fornecedor",
        "DOCUMENTO_FISCAL": "Nota fiscal de compra de ativo imobilizado",
        "TRIBUTACAO": "ICMS e IPI",
    }, "1.2"),
    ("aquisicao-servicos", {
        "NOME_MOVIMENTO": "Aquisição de Serviços",
        "PROCESSO_ORIGEM": "Solicitação de Serviços",
        "DOCUMENTO_FISCAL": "Nota fiscal de serviço do fornecedor",
        "RETENCOES": "ISS, INSS, PIS/COFINS/CSLL, IRRF retidos",
    }, "1.2"),
    ("devolucao-compra", {
        "NOME_MOVIMENTO": "Devolução de Compra",
        "PROCESSO_ORIGEM": "Nota de entrada de material comprado do fornecedor",
        "OBSERVACAO_FISCAL": "Movimento não gera integração fiscal",
    }, "2.2"),
    # Cadastros e gestão de contratos não são "tipo de movimento":
    # o piso de confiança deve deixá-los sem sugestão.
    ("cadastro-produtos", {
        "NOME_MOVIMENTO": "Cadastro de Produtos",
        "PROCESSO_ORIGEM": "Cadastros | Específicos | Produtos",
    }, None),
    ("manutencao-contratos", {
        "NOME_MOVIMENTO": "Manutenção de Contratos",
        "PROCESSO_ORIGEM": "Processos | Gestão de Contratos | Manutenção de Contratos",
    }, None),
]
