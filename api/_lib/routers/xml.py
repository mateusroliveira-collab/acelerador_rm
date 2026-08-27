"""
Rotas da API para o buscador de XML.

Este arquivo NÃO é um entrypoint da Vercel -- é um módulo comum,
importado pelo api/index.py através de app.include_router(). Toda a
lógica pesada (limpeza de XML) mora em xml_cleaner.py; aqui só
orquestra: recebe a requisição, chama a lógica, devolve a resposta.
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from .. import config
from ..xml_cleaner import limpar_xml
from ..mit41.parser import parsear_mit41
from ..mit41.matcher import sugerir_grupos

router = APIRouter(prefix="/api/xml", tags=["xml"])


class TextoMit41(BaseModel):
    texto: str


@router.post("/sugerir-grupo")
def sugerir_grupo_por_mit41(corpo: TextoMit41):
    """
    Recebe um trecho colado da saída do interpretador de MIT 41, extrai
    os campos estruturados, e devolve sugestões de grupo de movimento --
    cada uma com os sinais que levaram àquela pontuação (não é caixa
    preta, o analista confirma antes de usar).
    """
    campos = parsear_mit41(corpo.texto)
    if not campos:
        raise HTTPException(
            status_code=400,
            detail="Não consegui reconhecer nenhum campo nesse texto. Confirma se é a saída do interpretador de MIT 41.",
        )
    sugestoes = sugerir_grupos(campos)
    return {"campos_extraidos": campos, "sugestoes": sugestoes}
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
