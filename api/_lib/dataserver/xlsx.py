"""
Planilha Excel (.xlsx) do gerador de DataServer: gera o MODELO que o analista
entrega ao cliente e LÊ a planilha preenchida pra validar.

Tudo em memória -- nada do que está na planilha (pode ter dados pessoais) é
gravado em banco ou log. `openpyxl` só é importado dentro das funções, pra não
pesar no início a frio das rotas que não usam planilha.

Segurança do upload: limite de tamanho, recusa de arquivos com macro (.xlsm),
checagem do tamanho descompactado (contra "zip bomb") e leitura em modo
somente-leitura, sem executar nada do arquivo.

As travas e validações do Excel NÃO são segurança (dá pra colar valores por cima
ou desproteger a planilha): a validação de verdade é a do servidor.
"""

import io
import zipfile
from datetime import date, datetime

from .base import BOOLEANO, DATA, EMAIL, INTEIRO, TEXTO, Modulo
from .lote import MAX_LINHAS, mapear_colunas

ABA_DADOS = "Dados"
ABA_LISTAS = "Listas"
ABA_INSTRUCOES = "Instruções"
ABA_META = "_meta"
ABA_ERROS = "Erros"

MAX_BYTES = 2_000_000  # upload (a Vercel aceita ~4,5 MB por requisição, e a resposta leva o arquivo marcado)
MAX_DESCOMPACTADO = 40_000_000
LINHAS_EXTRAS_LEITURA = 5000  # tolera linhas vazias formatadas depois dos dados
TIPO_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

LINHA_FINAL_LISTA = 200


class XlsxInvalido(ValueError):
    """Arquivo que não dá pra usar (não é xlsx, tem macro, grande demais...)."""


def _cabecalho(campo) -> str:
    """Nome técnico do campo, igual ao GET do RM (ex.: CODUSUARIO)."""
    return campo.nome


def _formato_aceito(campo) -> str:
    if campo.tipo == BOOLEANO:
        sim, nao = campo.valores_booleanos()
        return f"{sim} = sim, {nao} = não"
    return {DATA: "data DD/MM/AAAA", INTEIRO: "número inteiro (0 ou mais)", EMAIL: "e-mail"}.get(campo.tipo, "texto")


def _dica(campo) -> str:
    dica = f"{campo.nome} -- {campo.rotulo}" + (" (obrigatório)" if campo.obrigatorio else "")
    dica += f"\nFormato: {_formato_aceito(campo)}"
    if campo.ajuda:
        dica += "\n" + campo.ajuda
    return dica


# ----------------------------------------------------------------------------
# Modelo
# ----------------------------------------------------------------------------

def gerar_modelo_xlsx(modulo: Modulo, config: dict | None = None) -> bytes:
    """Modelo do módulo: aba Dados (travada, com validações), Listas e Instruções."""
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill, Protection
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = ABA_DADOS
    campos = modulo.campos
    amarelo = PatternFill("solid", fgColor="FFF2CC")
    cinza = PatternFill("solid", fgColor="EFEFEF")
    ultima = MAX_LINHAS + 1
    por_campo_lista = {campo: chave for chave, campo in modulo.listas_config.items()}

    for j, c in enumerate(campos, start=1):
        letra = get_column_letter(j)
        cel = ws.cell(row=1, column=j, value=_cabecalho(c))
        cel.font = Font(bold=True)
        cel.fill = amarelo if c.obrigatorio else cinza
        cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cel.comment = Comment(_dica(c), "Acelerador RM", width=280, height=110)
        ws.column_dimensions[letra].width = max(16, min(38, len(_cabecalho(c)) + 4))

        faixa = f"{letra}2:{letra}{ultima}"
        dv = None
        if c.nome in por_campo_lista:  # lista vem da aba Listas
            dv = DataValidation(type="list", formula1=f"{ABA_LISTAS}!$A$2:$A${LINHA_FINAL_LISTA}", allow_blank=True)
            dv.error = "Escolha um código da lista (aba Listas)."
        elif c.tipo == BOOLEANO:  # valores como o RM grava: 1/0 ou T/F
            sim, nao = c.valores_booleanos()
            dv = DataValidation(type="list", formula1=f'"{sim},{nao}"', allow_blank=True)
            dv.error = f"Escolha {sim} (sim) ou {nao} (não)."
        elif c.tipo == DATA:
            dv = DataValidation(type="custom", formula1=f"ISNUMBER({letra}2)", allow_blank=True)
            dv.error = "Informe uma data válida no formato DD/MM/AAAA."
        elif c.tipo == INTEIRO:
            dv = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
            dv.error = "Informe um número inteiro, zero ou maior."
        elif c.tipo == EMAIL:
            dv = DataValidation(
                type="custom",
                formula1=f'AND(ISNUMBER(SEARCH("@",{letra}2)),ISNUMBER(SEARCH(".",{letra}2)),ISERROR(SEARCH(" ",{letra}2)))',
                allow_blank=True,
            )
            dv.error = "Informe um e-mail válido."
        if dv:
            dv.errorTitle = "Valor inválido"
            dv.errorStyle = "stop"
            dv.showErrorMessage = True
            dv.promptTitle = c.nome[:30]
            dv.prompt = (c.rotulo + ": " + (c.ajuda or _formato_aceito(c)))[:250]
            dv.showInputMessage = True
            ws.add_data_validation(dv)
            dv.add(faixa)

        # Formato e destrava das células de dados (o resto da aba fica protegido).
        formato = "DD/MM/YYYY" if c.tipo == DATA else "@"
        texto_simples = c.tipo in (TEXTO, EMAIL, DATA) or (c.tipo == BOOLEANO and c.formato_booleano == "TF")
        for linha in range(2, ultima + 1):
            cel_dado = ws.cell(row=linha, column=j)
            cel_dado.protection = Protection(locked=False)
            if texto_simples:
                cel_dado.number_format = formato

    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "A2"
    ws.protection.sheet = True  # sem senha: o analista desprotege em Revisão > Desproteger planilha

    # --- Listas ---------------------------------------------------------------
    wl = wb.create_sheet(ABA_LISTAS)
    wl["A1"] = "CODACESSO (códigos de acesso)"
    wl["A1"].font = Font(bold=True)
    codigos = (config or {}).get("codigos_acesso") if config else None
    if not (isinstance(codigos, list) and codigos):
        codigos = ["Acesso01", "Acesso02"]
        wl["C1"] = ("EXEMPLO: troque pelos códigos de acesso do cliente antes de enviar a planilha. "
                    "(Revisão > Desproteger planilha; sem senha.)")
    for i, cod in enumerate(codigos[: LINHA_FINAL_LISTA - 1], start=2):
        wl.cell(row=i, column=1, value=str(cod))
    wl.column_dimensions["A"].width = 28
    wl.protection.sheet = True

    # --- Instruções -----------------------------------------------------------
    wi = wb.create_sheet(ABA_INSTRUCOES)
    linhas = [
        f"Como preencher -- {modulo.nome} ({modulo.dataserver})",
        "",
        "1. Preencha a aba Dados, uma linha por usuário. Colunas com fundo amarelo são obrigatórias.",
        "2. O cabeçalho usa os nomes dos campos do RM, na mesma ordem em que o RM devolve os dados.",
        "3. Passe o mouse no título da coluna (ou selecione a célula) para ver o que é e como preencher.",
        "4. Sim/não vai como o RM grava: 1 = sim e 0 = não (IGNORARAUTENTICACAOLDAP usa T = sim e F = não).",
        "5. Colunas com seta têm uma lista: escolha o valor. Datas: DD/MM/AAAA.",
        "6. Deixe vazio o que não souber -- exceto as colunas obrigatórias.",
        "7. NÃO informe senha: ela não faz parte deste cadastro.",
        "8. Não altere o cabeçalho (linha 1) nem a ordem das colunas.",
        "9. Ao terminar, salve e envie a planilha ao seu analista.",
        "",
        f"Versão do modelo: {modulo.chave} v{modulo.versao_schema}",
    ]
    for i, texto in enumerate(linhas, start=1):
        wi.cell(row=i, column=1, value=texto)
    wi["A1"].font = Font(bold=True, size=13)

    # Dicionário dos campos (uma linha por coluna da aba Dados).
    inicio = len(linhas) + 2
    for j, titulo in enumerate(("Campo", "Descrição", "Obrigatório", "Formato", "Observação"), start=1):
        wi.cell(row=inicio, column=j, value=titulo).font = Font(bold=True)
    for i, c in enumerate(campos, start=inicio + 1):
        wi.cell(row=i, column=1, value=c.nome)
        wi.cell(row=i, column=2, value=c.rotulo)
        wi.cell(row=i, column=3, value="Sim" if c.obrigatorio else "")
        wi.cell(row=i, column=4, value=_formato_aceito(c))
        wi.cell(row=i, column=5, value=c.ajuda)
    for letra, largura in zip("ABCDE", (26, 36, 12, 28, 70)):
        wi.column_dimensions[letra].width = largura
    wi.protection.sheet = True

    # --- _meta (oculta): identifica módulo e versão pra detectar modelo antigo ---
    wm = wb.create_sheet(ABA_META)
    wm["A1"], wm["B1"] = "modulo", modulo.chave
    wm["A2"], wm["B2"] = "versao_schema", str(modulo.versao_schema)
    wm.sheet_state = "hidden"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ----------------------------------------------------------------------------
# Leitura da planilha preenchida
# ----------------------------------------------------------------------------

def _celula_para_texto(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Sim" if v else "Não"
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def _validar_arquivo(conteudo: bytes) -> None:
    if not conteudo:
        raise XlsxInvalido("Arquivo vazio.")
    if len(conteudo) > MAX_BYTES:
        raise XlsxInvalido(f"Arquivo muito grande (limite de {MAX_BYTES // 1_000_000} MB).")
    try:
        zf = zipfile.ZipFile(io.BytesIO(conteudo))
    except zipfile.BadZipFile:
        raise XlsxInvalido("O arquivo não é um .xlsx válido (salve a planilha como Pasta de Trabalho do Excel).")
    nomes = zf.namelist()
    if any("vbaProject" in n for n in nomes):
        raise XlsxInvalido("Planilhas com macro (.xlsm) não são aceitas. Salve como .xlsx comum.")
    if "xl/workbook.xml" not in nomes:
        raise XlsxInvalido("O arquivo não parece uma planilha do Excel (.xlsx).")
    if sum(i.file_size for i in zf.infolist()) > MAX_DESCOMPACTADO:
        raise XlsxInvalido("Arquivo grande demais depois de descompactado.")


def ler_planilha(conteudo: bytes) -> tuple[str, list[int], dict]:
    """
    Lê a aba Dados (ou a primeira aba) e devolve (texto tabulado, números das
    linhas da planilha de cada linha de dado, meta). Linhas vazias são puladas.
    """
    _validar_arquivo(conteudo)
    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    except Exception:
        raise XlsxInvalido("Não consegui ler a planilha. Confirme que o arquivo não está corrompido.")
    try:
        ws = wb[ABA_DADOS] if ABA_DADOS in wb.sheetnames else wb.worksheets[0]
        meta = {}
        if ABA_META in wb.sheetnames:
            for linha in wb[ABA_META].iter_rows(min_row=1, max_row=5, max_col=2, values_only=True):
                if linha and linha[0]:
                    meta[str(linha[0])] = _celula_para_texto(linha[1])

        cabecalho: list[str] = []
        linhas: list[list[str]] = []
        numeros: list[int] = []
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=MAX_LINHAS + 1 + LINHAS_EXTRAS_LEITURA, values_only=True), start=1):
            textos = [_celula_para_texto(v) for v in row]
            if i == 1:
                while textos and textos[-1] == "":
                    textos.pop()  # colunas vazias à direita
                cabecalho = textos
                continue
            if not any(textos):
                continue
            linhas.append((textos + [""] * len(cabecalho))[: len(cabecalho)])
            numeros.append(i)
    finally:
        wb.close()

    if not cabecalho:
        raise XlsxInvalido("A primeira linha da aba Dados (cabeçalho) está vazia.")
    if not linhas:
        raise XlsxInvalido("Nenhuma linha preenchida na aba Dados.")
    texto = "\n".join(["\t".join(cabecalho)] + ["\t".join(l) for l in linhas])
    return texto, numeros, meta


# ----------------------------------------------------------------------------
# Planilha devolvida com os erros marcados
# ----------------------------------------------------------------------------

def anotar_planilha(conteudo: bytes, modulo: Modulo, resultado: dict) -> bytes:
    """
    A MESMA planilha, com as células com erro em vermelho + comentário com o
    motivo, e uma aba "Erros" com o resumo. `resultado["linhas"][i]["linha"]`
    precisa estar na numeração da planilha.
    """
    from openpyxl import load_workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Font, PatternFill

    wb = load_workbook(io.BytesIO(conteudo))
    ws = wb[ABA_DADOS] if ABA_DADOS in wb.sheetnames else wb.worksheets[0]
    cab = [str(c.value or "") for c in ws[1]]
    mapa, _ = mapear_colunas(modulo, cab)
    coluna_do_campo = {campo: idx + 1 for idx, campo in mapa.items()}
    vermelho = PatternFill("solid", fgColor="F4C7C3")

    for l in resultado["linhas"]:
        if l["valido"]:
            continue
        por_coluna: dict[int, list[str]] = {}
        for e in l["erros"]:
            por_coluna.setdefault(coluna_do_campo.get(e["campo"], 1), []).append(e["mensagem"])
        for col, msgs in por_coluna.items():
            cel = ws.cell(row=l["linha"], column=col)
            cel.fill = vermelho
            cel.comment = Comment("\n".join(msgs), "Acelerador RM", width=280, height=100)

    if ABA_ERROS in wb.sheetnames:
        del wb[ABA_ERROS]
    we = wb.create_sheet(ABA_ERROS, 0)
    we.append(["Linha", modulo.campo_chave or "Registro", "Problemas"])
    for c in we[1]:
        c.font = Font(bold=True)
    for l in resultado["linhas"]:
        if not l["valido"]:
            we.append([l["linha"], l.get("chave") or "", " | ".join(e["mensagem"] for e in l["erros"])])
    we.column_dimensions["A"].width = 8
    we.column_dimensions["B"].width = 24
    we.column_dimensions["C"].width = 100

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def processar_planilha(modulo: Modulo, conteudo: bytes, operacao: str, gerar_payload, config=None):
    """
    Valida uma planilha .xlsx. Devolve (resultado, numeros) onde as linhas do
    resultado já estão na numeração da planilha (a do Excel).
    """
    from .lote import processar_lote

    texto, numeros, meta = ler_planilha(conteudo)
    resultado = processar_lote(modulo, texto, operacao, gerar_payload, config)
    for l in resultado["linhas"]:
        l["linha"] = numeros[l["linha"] - 2]  # número da linha no Excel
    if meta.get("modulo") and meta["modulo"] != modulo.chave:
        resultado["avisos_gerais"].append(
            f"Esta planilha é do módulo '{meta['modulo']}', mas a validação é de '{modulo.chave}'."
        )
    elif meta.get("versao_schema") and meta["versao_schema"] != str(modulo.versao_schema):
        resultado["avisos_gerais"].append(
            f"Modelo desatualizado (v{meta['versao_schema']}; atual v{modulo.versao_schema}). "
            "Baixe o modelo novo e passe os dados para ele."
        )
    return resultado, numeros
