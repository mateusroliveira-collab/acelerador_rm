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
from ._lib.routers.registro_online_boleto import router as registro_online_router
from ._lib.routers.registro_online_caixa import router as registro_online_caixa_router
from ._lib.routers.log import router as log_router
from ._lib.db import criar_tabelas
app = FastAPI(title="Ferramentas RM")
app.include_router(xml_router)
app.include_router(cnab_router)
app.include_router(registro_online_router)
app.include_router(registro_online_caixa_router)
app.include_router(log_router)
# Garante que as tabelas existem -- seguro rodar toda vez, não recria o
# que já existe. Se o banco estiver indisponível na inicialização, não
# devemos derrubar o app inteiro por causa disso.
try:
    criar_tabelas()
except Exception:
    pass
@app.get("/api/health")
def health():
    """Rota simples pra confirmar que a API está no ar."""
    return {"status": "ok"}
