"""
Rotas da API para o buscador e higienizador de XML / MIT 41.

Este arquivo NÃO é um entrypoint da Vercel -- é um módulo comum,
importado pelo api/index.py através de app.include_router(). Toda a
lógica pesada (limpeza de XML) mora em xml_cleaner.py; aqui só
orquestra: recebe a requisição, chama a lógica, devolve a resposta.
"""

from fastapi import APIRouter, HTTPException, Response, UploadFile, File
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
from ..registro_uso import registrar_uso
from ..db import SessionLocal
from ..models import XmlPersonalizado

router = APIRouter(prefix="/api/xml", tags=["xml"])


class TextoMit41(BaseModel):
    texto: str


@router.post("/sugerir-grupo")
def sugerir_grupo_por_mit41(corpo: TextoMit41):
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
    try:
        registrar_uso("mit41", "sugerir-grupo", {"total_movimentos": len(resultados)})
    except Exception:
        pass

    return {"movimentos": resultados}


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
async def limpar_xml_avulso(arquivo: UploadFile = File(...)):
    """Higieniza um XML enviado na hora, SEM salvar no banco ou disco."""
    conteudo_bytes = await arquivo.read()
    try:
        conteudo_original = conteudo_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Arquivo não parece ser um XML de texto válido (falha ao decodificar).",
        )

    xml_limpo, campos_zerados = limpar_xml(conteudo_original)
    nome_saida = (arquivo.filename or "arquivo").rsplit(".", 1)[0] + "_LIMPO.xml"

    try:
        registrar_uso("xml", "limpar-avulso", {"campos_zerados": campos_zerados})
    except Exception:
        pass

    return Response(
        content=xml_limpo,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_saida}"',
            "X-Campos-Zerados": str(campos_zerados),
        },
    )


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

    if len(conteudo_original) > 2_000_000:
        raise HTTPException(
            status_code=400,
            detail="Arquivo muito grande (limite de ~2MB de texto pra esse tipo de envio).",
        )

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
        registro = db.query(XmlPersonalizado).filter(XmlPersonalizado.id == xml_id).first()
    finally:
        db.close()

    if not registro:
        raise HTTPException(status_code=404, detail="XML personalizado não encontrado.")

    nome_saida = registro.nome_arquivo.rsplit(".", 1)[0] + "_LIMPO.xml"
    return Response(
        content=registro.conteudo_limpo,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_saida}"',
            "X-Campos-Zerados": str(registro.campos_zerados),
        },
    )


@router.get("/grupos")
def listar_grupos():
    """Devolve a lista de grupos de movimento disponíveis."""
    return [
        {
            "codigo": codigo,
            "label": info["label"],
            "descricao": info.get("descricao"),
        }
        for codigo, info in config.GRUPOS.items()
    ]


@router.get("/buscar")
def buscar_arquivos(grupo: str, busca: str = ""):
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
            consulta = db.query(XmlPersonalizado).filter(XmlPersonalizado.grupo == grupo)
            if termo:
                consulta = consulta.filter(XmlPersonalizado.nome_arquivo.ilike(f"%{termo}%"))
            personalizados = [
                {"id": p.id, "nome": p.nome_arquivo, "personalizado": True}
                for p in consulta.order_by(XmlPersonalizado.criado_em.desc()).all()
            ]
        finally:
            db.close()
    except Exception:
        pass

    resultado = [{"nome": nome, "personalizado": False} for nome in arquivos_pasta] + personalizados
    try:
        registrar_uso("xml", "buscar", {"grupo": grupo, "busca": termo, "total_encontrado": len(resultado)})
    except Exception:
        pass

    return {"grupo": grupo, "arquivos": resultado}


@router.post("/limpar")
def limpar_arquivo(grupo: str, arquivo: str):
    """Higieniza um XML específico da base fixa e devolve para download."""
    if not config.grupo_existe(grupo):
        raise HTTPException(status_code=404, detail=f"Grupo '{grupo}' não encontrado.")

    caminho = config.pasta_do_grupo(grupo) / arquivo
    if not caminho.exists() or caminho.suffix.lower() != ".xml":
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    conteudo_original = caminho.read_text(encoding="utf-8-sig")
    xml_limpo, campos_zerados = limpar_xml(conteudo_original)

    nome_saida = caminho.stem + "_LIMPO.xml"
    try:
        registrar_uso("xml", "limpar", {"grupo": grupo, "arquivo": arquivo, "campos_zerados": campos_zerados})
    except Exception:
        pass

    return Response(
        content=xml_limpo,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_saida}"',
            "X-Campos-Zerados": str(campos_zerados),
        },
    )