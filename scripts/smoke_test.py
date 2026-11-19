"""
Smoke test: importa a API inteira (um erro de import derruba a função única
da Vercel) e exercita as rotas principais de XML.

Uso: python scripts/smoke_test.py   (sai com código != 0 se algo falhar)
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
# Banco descartável: nunca toca o dev.db nem o Neon durante o teste.
os.environ.pop("VERCEL", None)
for _v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST"):
    os.environ.pop(_v, None)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/smoke.db"

from fastapi.testclient import TestClient  # noqa: E402

from api.index import app  # noqa: E402  (falha aqui = erro de import em produção)

client = TestClient(app)
falhas = []


def checar(nome, condicao):
    print(("OK    " if condicao else "FALHA ") + nome)
    if not condicao:
        falhas.append(nome)


r = client.get("/api/health")
checar("GET /api/health", r.status_code == 200)

r = client.get("/api/xml/grupos")
checar("GET /api/xml/grupos", r.status_code == 200 and len(r.json()) >= 6)

r = client.get("/api/xml/buscar", params={"grupo": "1.1"})
checar("GET /api/xml/buscar", r.status_code == 200 and len(r.json()["arquivos"]) > 0)

r = client.get("/api/xml/pesquisar", params={"q": "1.1.01"})
checar("GET /api/xml/pesquisar (código)", r.status_code == 200 and r.json()["total"] > 0)

r = client.get("/api/xml/pesquisar", params={"q": "requisicao"})
checar("GET /api/xml/pesquisar (sem acento)", r.status_code == 200 and r.json()["total"] > 0)

r = client.get("/api/xml/pesquisar", params={"q": ""})
checar("GET /api/xml/pesquisar (vazio)", r.status_code == 200 and r.json()["total"] == 0)

texto_mit41 = "[INICIO_MOVIMENTO]\nNOME_MOVIMENTO=Baixa de Estoque\n[FIM_MOVIMENTO]"
r = client.post("/api/xml/sugerir-grupo", json={"texto": texto_mit41})
checar("POST /api/xml/sugerir-grupo", r.status_code == 200 and r.json()["movimentos"][0]["sugestoes"][0]["grupo"] == "4.1")

r = client.get("/api/dataserver/modulos")
checar("GET /api/dataserver/modulos", r.status_code == 200 and r.json()[0]["dataserver"] == "GlbUsuarioData")

r = client.post("/api/dataserver/glb-usuario/gerar", json={"operacao": "incluir", "valores": {
    "CODUSUARIO": "teste.smoke", "CODACESSO": "Acesso01", "DATAINICIO": "2026-01-01"}})
checar("POST /api/dataserver/glb-usuario/gerar", r.status_code == 200 and r.json()["payload"]["STATUS"] == 1)

texto_lote = "\n".join([
    "CODUSUARIO;CODACESSO;DATAINICIO",
    "teste.um;Acesso01;01/01/2026",
    "teste.dois;Acesso01;01/01/2026",
])
r = client.post("/api/dataserver/glb-usuario/lote", json={"operacao": "incluir", "texto": texto_lote})
checar("POST /api/dataserver/glb-usuario/lote", r.status_code == 200 and r.json()["validos"] == 2)

r = client.get("/api/v1/dataserver/modulos")
checar("GET /api/v1/dataserver/modulos", r.status_code == 200 and r.json()[0]["versao_schema"] == "1")

r = client.get("/api/v1/dataserver/modulos")
checar("modulos traz planilha_modelo_url", r.status_code == 200 and "planilha_modelo_url" in r.json()[0])

r = client.get("/api/v1/dataserver/glb-usuario/modelo-xlsx")
checar("GET modelo-xlsx", r.status_code == 200 and r.content[:2] == b"PK")

r = client.post("/api/v1/dataserver/glb-usuario/lote-xlsx", files={"arquivo": ("modelo.xlsx", r.content)})
checar("POST lote-xlsx (modelo vazio recusado)", r.status_code == 400)

r = client.get("/api/dataserver/glb-usuario/modelo-csv")
checar("GET /api/dataserver/glb-usuario/modelo-csv", r.status_code == 200 and b"CODUSUARIO" in r.content)

print()
if falhas:
    print(f"{len(falhas)} falha(s).")
    sys.exit(1)
print("Smoke test OK.")
