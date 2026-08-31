"""
Motor de limpeza de XML -- adaptado do script original em Colab.

O QUE MUDOU em relação à versão original:
  - Não lê nem escreve arquivo em disco. Recebe o conteúdo do XML como
    string e devolve o resultado como string. Quem decide o que fazer
    com o resultado (mandar como download, salvar em algum lugar, etc.)
    é a rota da API, não esta função. Isso é proposital: o sistema de
    arquivos da Vercel é passageiro, então a função não pode depender
    de gravar nada em disco pra funcionar.
  - Sem os ajustes de ambiente do Colab (locale, google.colab.drive) --
    não fazem sentido fora do notebook.
  - Sem a interface de linha de comando (input()) -- os parâmetros
    (grupo, arquivo escolhido) vêm da requisição HTTP.

O QUE FICOU IGUAL:
  - O regex de limpeza e a lista de campos de amarração são exatamente
    os mesmos da versão que você já validou. Essa lógica é a parte mais
    sensível do projeto, então não vale a pena reescrever.
"""

import logging
import re

logger = logging.getLogger("XMLCleaner")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# Campos de amarração: identificadores do ambiente/cliente original que
# precisam ser zerados para o XML virar um template genérico e reutilizável.
CAMPOS_PARA_ZERAR = [
    "CodColigada", "CodFilial", "CodLoc", "CodLocal",
    "CodFrm", "IdRelatorio", "IdRelat",
    "CodCondicaoPagto", "IdNat", "CodNat", "CodVen", "CodTra",
    "CodRepr", "CodEvento", "CodigoEvento", "CodCaixa", "IdFormaPagto",
    "CodDepto", "CodCCusto", "CodClassMov", "CodCfo", "CodTab",
    "IdPrd", "EstadosDeAprovacao", "StatusLote", "Tributos",
    "OutrosCodTipoDocumento", "CodTipoDoc",
    # Adicionados depois de auditar um XML real de produção que dava erro
    # de DataGridViewComboBoxCell/chave estrangeira nos grupos 1.1, 1.2,
    # 2.2, 3.1 e 4.1 -- "CodCol" e "CodDep" generalizam os prefixos
    # antigos (cobrem casos irmãos que a lista original não previu, ex:
    # CodColCaixa, CodColCfoEmissao/Destino, CodDepartamentoDefaultMov).
    # "CodFormula" e "CodMen" são categorias novas: referência a Fórmula e
    # a Mensagem/Template, ambas configuração específica de cada ambiente.
    "CodCol", "CodDep", "CodFormula", "CodMen",
]

_REGEX_PREFIXOS = "|".join(CAMPOS_PARA_ZERAR)

# Regex "blindada": Grupo 1 = abertura do Form + ClassName + ClassProps,
# Grupo 2 = nome da tag raiz, Grupo 3 = miolo (onde mora o <Conteudo>,
# se existir), Grupo 4 = fechamento da tag. Garante que a busca não
# "vaze" para a tag seguinte.
_PADRAO_FORM = re.compile(
    r"(<([A-Za-z0-9_]+Form)>\s*<ClassName>[^<]+</ClassName>\s*<ClassProps>\s*(?:"
    + _REGEX_PREFIXOS
    + r")[A-Za-z0-9_]*\s*</ClassProps>)(.*?)(</\2>)",
    re.IGNORECASE | re.DOTALL,
)


def limpar_xml(xml_content: str) -> tuple[str, int]:
    """
    Higieniza o conteúdo de um XML, zerando os campos de amarração.

    Args:
        xml_content: conteúdo bruto do XML (já lido como string).

    Returns:
        Tupla (xml_limpo, quantidade_de_campos_anulados).
    """
    contador = 0

    def _limpar_bloco(match: re.Match) -> str:
        nonlocal contador
        miolo = match.group(3)
        if "<Conteudo" in miolo:
            contador += 1
        # Devolve a estrutura sem o conteúdo do campo (padrão de nulo do RM)
        return match.group(1) + "\n" + match.group(4)

    xml_limpo = _PADRAO_FORM.sub(_limpar_bloco, xml_content)
    logger.info("Limpeza concluída: %s campo(s) de amarração anulados.", contador)
    return xml_limpo, contador
