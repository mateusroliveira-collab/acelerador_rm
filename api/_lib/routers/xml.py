"""
Rotas da API para o buscador de XML.

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
from ..mit41.pre_processador import pre_processar_documento, montar_campos_para_matcher

router = APIRouter(prefix="/api/xml", tags=["xml"])


class TextoMit41(BaseModel):
    texto: str


@router.post("/sugerir-grupo")
def sugerir_grupo_por_mit41(corpo: TextoMit41):
    """
    Recebe um trecho colado da saída do interpretador de MIT 41 -- pode
    ser UM movimento ou o documento INTEIRO com vários -- separa cada
    [INICIO_MOVIMENTO]...[FIM_MOVIMENTO], extrai os campos de cada um, e
    devolve sugestões de grupo por movimento. Cada sugestão mostra os
    sinais que levaram àquela pontuação (não é caixa preta), e um
    movimento sem sinal suficiente vem com lista de sugestões vazia --
    nunca inventa uma resposta fraca.
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
    return {"movimentos": resultados}


@router.post("/pre-processar-mit41")
async def pre_processar_mit41_bruto(arquivo: UploadFile = File(...)):
    """
    Recebe o PDF BRUTO de um documento MIT 41 (sem nenhuma interpretação
    de IA ainda), extrai o texto, e separa a estrutura que dá pra
    extrair com confiabilidade real via regra pura: número e título do
    subprocesso, caminho "Processo Relacionado", texto AS IS, texto TO BE
    e a seção GAP.

    Também devolve uma sugestão de grupo APROXIMADA por movimento (usando
    só nome + processo relacionado + palavras-chave fiscais no TO BE) --
    é mais fraca que a Ponte MIT 41 completa (que usa a saída já
    interpretada pelo Gem), e isso fica marcado explicitamente.
    """
    import pdfplumber
    import io

    conteudo_bytes = await arquivo.read()
    try:
        with pdfplumber.open(io.BytesIO(conteudo_bytes)) as pdf:
            texto = "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)
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

    subprocessos = pre_processar_documento(texto)
    return {
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


@router.get("/grupos")
def listar_grupos():
    """Devolve a lista de grupos de movimento disponíveis (pro dropdown do front)."""
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
    """Lista os XMLs de um grupo, opcionalmente filtrados por um termo no nome."""
    if not config.grupo_existe(grupo):
        raise HTTPException(status_code=404, detail=f"Grupo '{grupo}' não encontrado.")

    pasta = config.pasta_do_grupo(grupo)
    if not pasta.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Pasta do grupo '{grupo}' não existe no servidor.",
        )

    termo = busca.strip().lower()
    arquivos = sorted(
        f.name
        for f in pasta.iterdir()
        if f.suffix.lower() == ".xml" and termo in f.stem.lower()
    )
    return {"grupo": grupo, "arquivos": arquivos}


@router.post("/limpar")
def limpar_arquivo(grupo: str, arquivo: str):
    """Higieniza um XML específico e devolve o resultado pronto pra download."""
    if not config.grupo_existe(grupo):
        raise HTTPException(status_code=404, detail=f"Grupo '{grupo}' não encontrado.")

    caminho = config.pasta_do_grupo(grupo) / arquivo
    if not caminho.exists() or caminho.suffix.lower() != ".xml":
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    conteudo_original = caminho.read_text(encoding="utf-8-sig")
    xml_limpo, campos_zerados = limpar_xml(conteudo_original)

    nome_saida = caminho.stem + "_LIMPO.xml"
    return Response(
        content=xml_limpo,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_saida}"',
            "X-Campos-Zerados": str(campos_zerados),
        },
    )
