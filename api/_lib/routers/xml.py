"""
Rotas da API para o buscador e higienizador de XML / MIT 41.

Este arquivo NÃO é um entrypoint da Vercel -- é um módulo comum,
importado pelo api/index.py através de app.include_router(). Toda a
lógica pesada (limpeza de XML) mora em xml_cleaner.py; aqui só
orquestra: recebe a requisição, chama a lógica, devolve a resposta.
"""

import re
import unicodedata
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, UploadFile, File
from pydantic import BaseModel

from .. import config
from ..xml_cleaner import limpar_xml
from ..mit41.parser import parsear_mit41, separar_movimentos
from ..mit41.matcher import sugerir_grupos
from ..mit41.pre_processador import (
    pre_processar_documento,
    montar_campos_para_matcher,
    gerar_texto_para_ponte,
    extrair_indice_de_tabelas,
)
from ..pesquisa_xml import ItemXml, LIMITE_RESULTADOS, pesquisar
from ..regras_xml import regra_da_biblioteca, regra_de_conteudo
from ..registro_uso import registrar_uso
from ..db import SessionLocal
from ..models import XmlPersonalizado

router = APIRouter(prefix="/api/xml", tags=["xml"])


def _nome_limpo(nome_original: str | None) -> str:
    """'arquivo.xml' -> 'arquivo_LIMPO.xml' (só tira a última extensão)."""
    base = (nome_original or "arquivo").rsplit(".", 1)[0] or "arquivo"
    return base + "_LIMPO.xml"


def _resposta_download_xml(conteudo: str, nome_saida: str, campos_zerados: int) -> Response:
    """
    Monta a resposta de download. O nome vai em dois formatos: um ASCII
    simples (fallback) e o "filename*" do RFC 5987 com o nome real em
    UTF-8. Antes o nome ia cru no header -- qualquer caractere fora do
    Latin-1 (ex: travessão "—") derrubava a rota com erro 500, e aspas no
    nome quebravam o header.
    """
    nome_ascii = (
        unicodedata.normalize("NFKD", nome_saida).encode("ascii", "ignore").decode("ascii")
    )
    nome_ascii = re.sub(r'[^A-Za-z0-9._ ()-]', "_", nome_ascii) or "arquivo_LIMPO.xml"
    return Response(
        content=conteudo,
        media_type="application/xml",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{nome_ascii}\"; filename*=UTF-8''{quote(nome_saida)}"
            ),
            "X-Campos-Zerados": str(campos_zerados),
        },
    )


_LIMITE_TEXTO = 2_000_000
_MSG_LIMITE = "Arquivo muito grande (limite de ~2MB de texto pra esse tipo de envio)."


class TextoMit41(BaseModel):
    texto: str


@router.post("/sugerir-grupo")
def sugerir_grupo_por_mit41(corpo: TextoMit41, tarefas: BackgroundTasks):
    """
    Recebe um trecho colado da saída do interpretador de MIT 41 -- pode
    ser UM movimento ou o documento INTEIRO com vários -- separa cada
    [INICIO_MOVIMENTO]...[FIM_MOVIMENTO], extrai os campos de cada um, e
    devolve sugestões de grupo por movimento.
    """
    blocos = separar_movimentos(corpo.texto)
    resultados = []
    for bloco in blocos:
        campos = parsear_mit41(bloco)
        if not campos:
            continue
        resultados.append(
            {
                "nome_movimento": campos.get("NOME_MOVIMENTO"),
                "campos_extraidos": campos,
                "sugestoes": sugerir_grupos(campos),
            }
        )

    if not resultados:
        raise HTTPException(
            status_code=400,
            detail="Não consegui reconhecer nenhum campo nesse texto. Confirma se é a saída do interpretador de MIT 41.",
        )
    tarefas.add_task(registrar_uso, "mit41", "sugerir-grupo", {"total_movimentos": len(resultados)})

    return {"movimentos": resultados}


class SugestaoCorrigida(BaseModel):
    sugerido: str | None = None  # 1ª sugestão do matcher (None = não sugeriu nada)
    escolhido: str  # grupo que o analista de fato escolheu
    nome_movimento: str | None = None


@router.post("/sugestao-corrigida")
def registrar_sugestao_corrigida(corpo: SugestaoCorrigida, tarefas: BackgroundTasks):
    """
    Registra no log de uso quando o analista escolhe um grupo diferente da
    1ª sugestão do matcher -- insumo pra ajustar o dicionário de sinônimos
    (mit41/sinonimos.py) depois. Guarda só o nome do movimento, nunca o
    texto do documento.
    """
    if not config.grupo_existe(corpo.escolhido):
        raise HTTPException(status_code=404, detail=f"Grupo '{corpo.escolhido}' não encontrado.")
    if corpo.sugerido == corpo.escolhido:
        return {"registrado": False}  # concordou com a sugestão: nada a aprender
    tarefas.add_task(
        registrar_uso,
        "mit41",
        "sugestao-corrigida",
        {
            "sugerido": corpo.sugerido,
            "escolhido": corpo.escolhido,
            "nome_movimento": (corpo.nome_movimento or "")[:200],
        },
    )
    return {"registrado": True}


@router.post("/pre-processar-mit41")
async def pre_processar_mit41_bruto(arquivo: UploadFile = File(...)):
    """
    Recebe o PDF BRUTO de um documento MIT 41, extrai o texto e separa a
    estrutura confiável via regras puras.
    """
    import pdfplumber
    import io

    conteudo_bytes = await arquivo.read()
    try:
        with pdfplumber.open(io.BytesIO(conteudo_bytes)) as pdf:
            texto = "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)
            tabelas = []
            for pagina in pdf.pages:
                tabelas.extend(pagina.extract_tables())
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Não consegui ler esse arquivo como PDF. Confirma se o arquivo não está corrompido.",
        )

    if not texto.strip():
        raise HTTPException(
            status_code=400,
            detail="O PDF não retornou texto (pode ser um PDF escaneado/imagem, sem texto selecionável).",
        )

    indice = extrair_indice_de_tabelas(tabelas)
    subprocessos = pre_processar_documento(texto, indice_pre_extraido=indice)
    try:
        registrar_uso("mit41", "pre-processar", {"total_subprocessos": len(subprocessos)})
    except Exception:
        pass

    return {
        "texto_para_ponte": gerar_texto_para_ponte(subprocessos),
        "subprocessos": [
            {
                "numero": sp.numero,
                "titulo": sp.titulo,
                "processo_relacionado": sp.processo_relacionado,
                "texto_as_is": sp.texto_as_is,
                "texto_to_be": sp.texto_to_be,
                "gap": sp.gap,
                "campos_que_precisam_de_ia": [
                    "EFEITO_ESTOQUE", "EFEITO_FINANCEIRO", "DOCUMENTO_FISCAL",
                    "CONTABILIZACAO", "REGRAS",
                ] if sp.texto_to_be else [],
                "sugestao_aproximada": sugerir_grupos(montar_campos_para_matcher(sp)),
            }
            for sp in subprocessos
        ]
    }


@router.post("/limpar-avulso")
async def limpar_xml_avulso(tarefas: BackgroundTasks, arquivo: UploadFile = File(...)):
    """Higieniza um XML enviado na hora, SEM salvar no banco ou disco."""
    conteudo_bytes = await arquivo.read()
    try:
        conteudo_original = conteudo_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Arquivo não parece ser um XML de texto válido (falha ao decodificar).",
        )

    if len(conteudo_original) > _LIMITE_TEXTO:
        raise HTTPException(status_code=400, detail=_MSG_LIMITE)

    xml_limpo, campos_zerados = limpar_xml(conteudo_original)

    tarefas.add_task(registrar_uso, "xml", "limpar-avulso", {"campos_zerados": campos_zerados})

    return _resposta_download_xml(xml_limpo, _nome_limpo(arquivo.filename), campos_zerados)


@router.post("/enviar")
async def enviar_xml_personalizado(grupo: str, arquivo: UploadFile = File(...)):
    """Recebe um XML de referência do usuário e guarda higienizado no banco."""
    if not config.grupo_existe(grupo):
        raise HTTPException(status_code=404, detail=f"Grupo '{grupo}' não encontrado.")

    conteudo_bytes = await arquivo.read()
    try:
        conteudo_original = conteudo_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Arquivo não parece ser um XML de texto válido (falha ao decodificar).",
        )

    if len(conteudo_original) > _LIMITE_TEXTO:
        raise HTTPException(status_code=400, detail=_MSG_LIMITE)

    xml_limpo, campos_zerados = limpar_xml(conteudo_original)

    db = SessionLocal()
    try:
        registro = XmlPersonalizado(
            grupo=grupo,
            nome_arquivo=arquivo.filename or "sem_nome.xml",
            conteudo_original=conteudo_original,
            conteudo_limpo=xml_limpo,
            campos_zerados=campos_zerados,
        )
        db.add(registro)
        db.commit()
        db.refresh(registro)
        novo_id = registro.id
    finally:
        db.close()

    try:
        registrar_uso("xml", "enviar-personalizado", {"grupo": grupo, "arquivo": arquivo.filename})
    except Exception:
        pass

    return {"id": novo_id, "arquivo": arquivo.filename, "campos_zerados": campos_zerados}


@router.get("/baixar-personalizado/{xml_id}")
def baixar_xml_personalizado(xml_id: int):
    """Baixa a versão já higienizada de um XML personalizado pelo ID."""
    db = SessionLocal()
    try:
        registro = (
            db.query(XmlPersonalizado)
            .filter(XmlPersonalizado.id == xml_id, XmlPersonalizado.excluido.isnot(True))
            .first()
        )
    finally:
        db.close()

    if not registro:
        raise HTTPException(status_code=404, detail="XML personalizado não encontrado.")

    return _resposta_download_xml(
        registro.conteudo_limpo or "",
        _nome_limpo(registro.nome_arquivo),
        registro.campos_zerados or 0,
    )


@router.get("/regra")
def regra_de_negocio(grupo: str | None = None, arquivo: str | None = None, id: int | None = None):
    """
    Regra de negócio de um XML (o que o movimento faz no estoque, financeiro,
    fiscal, orçamento...): da biblioteca fixa (grupo + arquivo) ou de um XML
    personalizado (id). Só leitura.
    """
    if id is not None:
        db = SessionLocal()
        try:
            registro = (
                db.query(XmlPersonalizado)
                .filter(XmlPersonalizado.id == id, XmlPersonalizado.excluido.isnot(True))
                .first()
            )
        finally:
            db.close()
        if not registro:
            raise HTTPException(status_code=404, detail="XML personalizado não encontrado.")
        try:
            regra = regra_de_conteudo((registro.conteudo_original or registro.conteudo_limpo or "").encode("utf-8"))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        return {"grupo": registro.grupo, "arquivo": registro.nome_arquivo, "regra": regra.para_dict()}

    if not grupo or not arquivo:
        raise HTTPException(status_code=400, detail="Informe grupo e arquivo, ou o id do XML personalizado.")
    regra = regra_da_biblioteca(grupo, arquivo)
    if regra is None:
        raise HTTPException(status_code=404, detail="XML não encontrado ou não é de parâmetros de movimento.")
    return {"grupo": grupo, "arquivo": arquivo, "regra": regra.para_dict()}


@router.delete("/personalizado/{xml_id}")
def excluir_xml_personalizado(xml_id: int):
    """
    Exclusão REVERSÍVEL de um XML contribuído: marca como excluído, sem
    apagar a linha. Só mexe em xml_personalizado -- os XMLs fixos da base
    não têm id nem passam por aqui.
    """
    db = SessionLocal()
    try:
        registro = (
            db.query(XmlPersonalizado)
            .filter(XmlPersonalizado.id == xml_id, XmlPersonalizado.excluido.isnot(True))
            .first()
        )
        if not registro:
            raise HTTPException(status_code=404, detail="XML personalizado não encontrado.")
        registro.excluido = True
        registro.excluido_em = datetime.utcnow()
        grupo, nome = registro.grupo, registro.nome_arquivo
        db.commit()
    finally:
        db.close()

    try:
        registrar_uso("xml", "excluir-personalizado", {"id": xml_id, "grupo": grupo, "arquivo": nome})
    except Exception:
        pass

    return {"id": xml_id, "excluido": True}


@router.get("/grupos")
def listar_grupos(response: Response):
    """Devolve a lista de grupos de movimento disponíveis."""
    # Lista fixa (só muda com deploy, que renova o cache da Vercel): o edge
    # responde sem acordar a função Python.
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
    return [
        {
            "codigo": codigo,
            "label": info["label"],
            "descricao": info.get("descricao"),
        }
        for codigo, info in config.GRUPOS.items()
    ]


@router.get("/pesquisar")
def pesquisar_global(tarefas: BackgroundTasks, q: str = ""):
    """Pesquisa por código e/ou descrição em TODOS os grupos de uma vez."""
    consulta = q.strip()[:200]
    if not consulta:
        return {"q": "", "total": 0, "resultados": []}

    personalizados = []
    try:
        db = SessionLocal()
        try:
            # Só as colunas leves: nunca carrega o conteúdo (Text) dos XMLs.
            linhas = db.query(
                XmlPersonalizado.id, XmlPersonalizado.grupo, XmlPersonalizado.nome_arquivo
            ).filter(XmlPersonalizado.excluido.isnot(True)).all()
            personalizados = [
                ItemXml(grupo=l.grupo, nome=l.nome_arquivo or "", personalizado=True, id=l.id)
                for l in linhas
                if config.grupo_existe(l.grupo)
            ]
        finally:
            db.close()
    except Exception:
        pass  # sem banco, a pesquisa segue só com os XMLs fixos

    achados = pesquisar(consulta, personalizados)
    resultados = [
        {
            "grupo": i.grupo,
            "codigo": i.codigo,
            "nome": i.nome,
            "personalizado": i.personalizado,
            **({"id": i.id} if i.personalizado else {}),
        }
        for i in achados[:LIMITE_RESULTADOS]
    ]
    if len(consulta) >= 3:
        tarefas.add_task(registrar_uso, "xml", "pesquisar", {"busca": consulta, "total_encontrado": len(achados)})

    return {"q": consulta, "total": len(achados), "resultados": resultados}


@router.get("/buscar")
def buscar_arquivos(tarefas: BackgroundTasks, grupo: str, busca: str = ""):
    """Lista os XMLs de um grupo, filtrando opcionalmente por nome."""
    if not config.grupo_existe(grupo):
        raise HTTPException(status_code=404, detail=f"Grupo '{grupo}' não encontrado.")

    pasta = config.pasta_do_grupo(grupo)
    if not pasta.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Pasta do grupo '{grupo}' não existe no servidor.",
        )

    termo = busca.strip().lower()
    arquivos_pasta = sorted(
        f.name
        for f in pasta.iterdir()
        if f.suffix.lower() == ".xml" and termo in f.stem.lower()
    )

    personalizados = []
    try:
        db = SessionLocal()
        try:
            consulta = db.query(XmlPersonalizado).filter(
                XmlPersonalizado.grupo == grupo, XmlPersonalizado.excluido.isnot(True)
            )
            if termo:
                # Escapa os curingas do LIKE: "_" é comum em nome de arquivo
                # e, sem escape, casaria com qualquer caractere.
                termo_like = termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                consulta = consulta.filter(
                    XmlPersonalizado.nome_arquivo.ilike(f"%{termo_like}%", escape="\\")
                )
            personalizados = [
                {"id": p.id, "nome": p.nome_arquivo, "personalizado": True}
                for p in consulta.order_by(XmlPersonalizado.criado_em.desc()).all()
            ]
        finally:
            db.close()
    except Exception:
        pass

    resultado = [{"nome": nome, "personalizado": False} for nome in arquivos_pasta] + personalizados
    tarefas.add_task(registrar_uso, "xml", "buscar", {"grupo": grupo, "busca": termo, "total_encontrado": len(resultado)})

    return {"grupo": grupo, "arquivos": resultado}


@router.post("/limpar")
def limpar_arquivo(tarefas: BackgroundTasks, grupo: str, arquivo: str):
    """Higieniza um XML específico da base fixa e devolve para download."""
    if not config.grupo_existe(grupo):
        raise HTTPException(status_code=404, detail=f"Grupo '{grupo}' não encontrado.")

    pasta = config.pasta_do_grupo(grupo).resolve()
    caminho = (pasta / arquivo).resolve()
    # "arquivo" vem da URL: sem essa checagem, um nome tipo "../outra_pasta/x.xml"
    # (ou caminho absoluto) lia qualquer .xml do servidor fora da pasta do grupo.
    if (
        caminho.parent != pasta
        or not caminho.is_file()
        or caminho.suffix.lower() != ".xml"
    ):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    try:
        conteudo_original = caminho.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Arquivo da base não está em UTF-8 -- não foi possível higienizar.",
        )
    xml_limpo, campos_zerados = limpar_xml(conteudo_original)

    tarefas.add_task(registrar_uso, "xml", "limpar", {"grupo": grupo, "arquivo": arquivo, "campos_zerados": campos_zerados})

    return _resposta_download_xml(xml_limpo, _nome_limpo(caminho.name), campos_zerados)