"""
Pontos de entrada de autenticação e limite de uso -- DESLIGADOS por padrão.

Hoje a API é aberta (uso interno). Para escalar/produtizar, basta ligar por
variável de ambiente, sem mexer em código:

  API_KEYS              "chave1:clienteA,chave2:clienteB"  (chave -> código do cliente)
  API_EXIGIR_CHAVE      "1" para recusar (401) chamadas sem chave válida
  RATE_LIMIT_POR_MINUTO inteiro; 0 ou ausente = sem limite

Limite de uso: contador em memória por instância da função. Na Vercel cada
instância conta separado, então o limite é APROXIMADO (protege contra abuso
simples, não é cota exata). Pra cota exata seria preciso um armazenamento
compartilhado (ex.: Redis) -- fica pra quando houver produto.
"""

import hmac
import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

CLIENTE_INTERNO = "interno"
_janelas: dict[str, deque] = defaultdict(deque)


def _chaves() -> dict[str, str]:
    bruto = os.environ.get("API_KEYS", "")
    pares = {}
    for item in bruto.split(","):
        chave, _, cliente = item.strip().partition(":")
        if chave and cliente:
            pares[chave] = cliente
    return pares


def _cliente_da_chave(chave: str | None) -> str | None:
    if not chave:
        return None
    for valida, cliente in _chaves().items():
        if hmac.compare_digest(chave, valida):  # tempo constante
            return cliente
    return None


def _limite() -> int:
    try:
        return max(0, int(os.environ.get("RATE_LIMIT_POR_MINUTO", "0")))
    except ValueError:
        return 0


def identificar_cliente(request: Request) -> str:
    """
    Dependência do FastAPI: devolve o código do cliente da chamada.
    Sem chaves configuradas -> "interno". Com API_EXIGIR_CHAVE=1 e chave
    ausente/inválida -> 401. Aplica o limite de uso, se ligado.
    """
    chave = request.headers.get("x-api-key")
    cliente = _cliente_da_chave(chave)

    if cliente is None:
        if os.environ.get("API_EXIGIR_CHAVE") == "1":
            raise HTTPException(status_code=401, detail="Chave de API ausente ou inválida.")
        cliente = CLIENTE_INTERNO

    limite = _limite()
    if limite:
        agora = time.monotonic()
        origem = request.client.host if request.client else "?"
        janela = _janelas[f"{cliente}|{origem}"]
        while janela and agora - janela[0] > 60:
            janela.popleft()
        if len(janela) >= limite:
            raise HTTPException(status_code=429, detail="Limite de uso excedido. Tente novamente em instantes.")
        janela.append(agora)
    return cliente
