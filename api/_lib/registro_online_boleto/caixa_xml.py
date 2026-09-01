"""
Parser do XML de Registro Online da Caixa (sistema SIGCB) -- diferente
do que se assumiu inicialmente, essa API usa XML (estilo SOAP, com
namespace tipo "sib:", "ext:"), não JSON.

Baseado em payload real de produção (operação INCLUI_BOLETO), não em
suposição -- ver estrutura completa em ARQUITETURA/notas do projeto.
"""

import re
import xml.etree.ElementTree as ET

from .validador import ResultadoValidacaoBoleto, validar_boleto


def _remover_namespace(tag: str) -> str:
    """Remove o prefixo de namespace (ex: '{...}TITULO' ou 'sib:HEADER' -> 'HEADER')."""
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    if ":" in tag:
        tag = tag.split(":", 1)[1]
    return tag


def _achar(elemento: ET.Element, caminho: list[str]) -> ET.Element | None:
    """
    Acha um elemento filho por uma sequência de nomes de tag, ignorando
    namespace -- assim não depende de saber o prefixo exato usado.
    """
    atual = elemento
    for nome in caminho:
        proximo = None
        for filho in atual:
            if _remover_namespace(filho.tag) == nome:
                proximo = filho
                break
        if proximo is None:
            return None
        atual = proximo
    return atual


def _texto(elemento: ET.Element | None) -> str | None:
    if elemento is None or elemento.text is None:
        return None
    texto = elemento.text.strip()
    return texto if texto else None


def parsear_xml_caixa(xml_texto: str) -> dict:
    """
    Extrai os campos do XML de INCLUI_BOLETO da Caixa (SIGCB) num dict
    normalizado, compatível com o formato que validar_boleto() já espera
    (o mesmo motor universal usado pra qualquer banco).

    Tolerante a XML colado como FRAGMENTO (sem o envelope SOAP completo
    que declararia os namespaces "ext:"/"sib:") -- caso real e esperado,
    já que o analista normalmente cola só a parte que importa, não a
    mensagem inteira. Remove qualquer prefixo de namespace antes de
    interpretar, então funciona igual com ou sem declaração.

    Levanta ValueError com mensagem clara se a estrutura básica
    (DADOS, TITULO) não for encontrada -- em vez de devolver
    silenciosamente um dict vazio que pareceria "válido" por engano.
    """
    # Remove prefixo de namespace de toda tag (ex: "<sib:HEADER>" vira
    # "<HEADER>") -- não precisamos do namespace de verdade, só do nome.
    xml_sem_prefixo = re.sub(r"(</?)[A-Za-z0-9_]+:", r"\1", xml_texto)

    try:
        raiz = ET.fromstring(xml_sem_prefixo)
    except ET.ParseError as e:
        raise ValueError(f"XML mal formado: {e}")

    header = None
    for filho in raiz:
        if _remover_namespace(filho.tag) == "HEADER":
            header = filho
            break

    dados = None
    for filho in raiz:
        if _remover_namespace(filho.tag) == "DADOS":
            dados = filho
            break

    if dados is None:
        raise ValueError(
            "Não encontrei a tag <DADOS> -- confirma se é um XML de Registro "
            "Online da Caixa (operação de boleto) e não outra coisa."
        )

    titulo = _achar(dados, ["INCLUI_BOLETO", "TITULO"])
    if titulo is None:
        raise ValueError(
            "Não encontrei <DADOS><INCLUI_BOLETO><TITULO> -- essa operação "
            "pode não ser INCLUI_BOLETO, ou o XML está incompleto."
        )

    pagador_el = _achar(titulo, ["PAGADOR"])
    endereco_el = _achar(titulo, ["PAGADOR", "ENDERECO"])
    multa_el = _achar(titulo, ["MULTA"])
    juros_mora_el = _achar(titulo, ["JUROS_MORA"])

    elemento_cpf = _achar(pagador_el, ["CPF"]) if pagador_el is not None else None
    elemento_cnpj = _achar(pagador_el, ["CNPJ"]) if pagador_el is not None else None
    # Cuidado: um Element do ElementTree sem filho (ex: <CPF>123</CPF>,
    # que só tem texto) é "falso" em teste booleano do Python -- "or"
    # pularia ele por engano achando que está vazio. Precisa checar
    # "is not None" explicitamente, não usar o elemento direto num "or".
    documento_texto = (
        _texto(elemento_cpf) if elemento_cpf is not None else _texto(elemento_cnpj)
    )

    resultado = {
        "cabecalho": {
            "operacao": _texto(_achar(header, ["OPERACAO"])) if header is not None else None,
            "unidade": _texto(_achar(header, ["UNIDADE"])) if header is not None else None,
            "id_processo": _texto(_achar(header, ["ID_PROCESSO"])) if header is not None else None,
        },
        "pagador": {
            "documento": documento_texto,
            "nome": _texto(_achar(pagador_el, ["NOME"])) if pagador_el is not None else None,
            "endereco": {
                "logradouro": _texto(_achar(endereco_el, ["LOGRADOURO"])) if endereco_el is not None else None,
                "bairro": _texto(_achar(endereco_el, ["BAIRRO"])) if endereco_el is not None else None,
                "cidade": _texto(_achar(endereco_el, ["CIDADE"])) if endereco_el is not None else None,
                "uf": _texto(_achar(endereco_el, ["UF"])) if endereco_el is not None else None,
                "cep": _texto(_achar(endereco_el, ["CEP"])) if endereco_el is not None else None,
            },
        },
        "titulo": {
            "nosso_numero": _texto(_achar(titulo, ["NOSSO_NUMERO"])),
            "numero_documento": _texto(_achar(titulo, ["NUMERO_DOCUMENTO"])),
            "valor": _texto(_achar(titulo, ["VALOR"])),
            "data_emissao": _texto(_achar(titulo, ["DATA_EMISSAO"])),
            "data_vencimento": _texto(_achar(titulo, ["DATA_VENCIMENTO"])),
        },
        "multa": {
            "data": _texto(_achar(multa_el, ["DATA"])) if multa_el is not None else None,
            "percentual": _texto(_achar(multa_el, ["PERCENTUAL"])) if multa_el is not None else None,
        }
        if multa_el is not None
        else None,
        "juros_mora": {
            "tipo": _texto(_achar(juros_mora_el, ["TIPO"])) if juros_mora_el is not None else None,
            "data": _texto(_achar(juros_mora_el, ["DATA"])) if juros_mora_el is not None else None,
            "valor": _texto(_achar(juros_mora_el, ["VALOR"])) if juros_mora_el is not None else None,
        }
        if juros_mora_el is not None
        else None,
        "valor_abatimento": _texto(_achar(titulo, ["VALOR_ABATIMENTO"])),
    }
    return resultado


def _para_boleto_universal(dados_caixa: dict) -> dict:
    """
    Converte o dict extraído do XML da Caixa pro formato que o
    validar_boleto() universal já entende (mesmo usado por qualquer
    banco) -- reaproveita a lógica de CPF/CNPJ, data e multa já pronta,
    sem duplicar regra nenhuma.
    """
    titulo = dados_caixa.get("titulo", {})
    pagador = dados_caixa.get("pagador", {})
    endereco = pagador.get("endereco", {})
    multa = dados_caixa.get("multa")

    payload: dict = {
        "pagador": {
            "documento": pagador.get("documento"),
            "endereco": endereco,
        },
        "titulo": {
            "valor": float(titulo["valor"]) if titulo.get("valor") else None,
            "data_emissao": titulo.get("data_emissao"),
            "data_vencimento": titulo.get("data_vencimento"),
        },
    }
    if multa and multa.get("percentual"):
        payload["multa"] = {"percentual": float(multa["percentual"])}
    return payload


def validar_boleto_xml_caixa(xml_texto: str) -> ResultadoValidacaoBoleto:
    """
    Ponto de entrada: recebe o XML bruto da Caixa, extrai, e roda as
    mesmas regras universais (CPF/CNPJ, data, valor, multa legal,
    endereço) -- mais avisos específicos do formato Caixa (juros de
    mora, abatimento) que não são erro, só informação.
    """
    dados = parsear_xml_caixa(xml_texto)
    payload_universal = _para_boleto_universal(dados)
    resultado = validar_boleto(payload_universal)

    # Avisos específicos da Caixa -- não são erro (não têm limite legal
    # confirmado com a mesma certeza da multa de 2%), só transparência.
    # Importante: isso NÃO pode afetar resultado.valido -- é informativo.
    juros_mora = dados.get("juros_mora")
    if juros_mora and juros_mora.get("valor"):
        resultado.avisos.append(
            f"Juros de mora informado: {juros_mora['valor']}% "
            f"({juros_mora.get('tipo', 'tipo não informado')}). "
            "Isso é diferente de multa -- confirma se a taxa está de "
            "acordo com o combinado no contrato do cliente."
        )
    return resultado
