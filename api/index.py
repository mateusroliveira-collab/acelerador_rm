"""
Entrypoint único da API na Vercel.

A Vercel empacota um app FastAPI inteiro como UMA função só -- por isso
existe só este arquivo de entrypoint. As rotas de cada módulo (xml, e
futuramente cnab e mit41) ficam organizadas em routers separados dentro
de api/_lib/routers/, e são registradas aqui.
"""

from fastapi import FastAPI

from ._lib.routers.xml import router as xml_router
from ._lib.routers.cnab import router as cnab_router

app = FastAPI(title="Ferramentas RM")

app.include_router(xml_router)
app.include_router(cnab_router)


@app.get("/api/health")
def health():
    """Rota simples pra confirmar que a API está no ar."""
    return {"status": "ok"}