"""
Rotas da API para o validador de CNAB.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from ..cnab.cnab400.validador_bb import validar_cnab400_bb
from ..cnab.cnab240.validador import validar_cnab240
from ..cnab.cnab240.corretor import corrigir_cnab240
from ..cnab.cnab400.validador import validar_cnab400
from ..cnab.cnab400.validador_caixa import validar_cnab400_caixa
from ..cnab.registro_online.validador import traduzir_erro_banco
from ..registro_uso import registrar_uso

router = APIRouter(prefix="/api/cnab", tags=["cnab"])


@router.post("/validar-240")
async def validar_arquivo_240(arquivo: UploadFile = File(...)):
    """Recebe um arquivo de remessa/retorno CNAB 240 e valida a estrutura."""
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = validar_cnab240(conteudo)
    registrar_uso("cnab", "validar-240", {"valido": resultado.valido, "total_erros": len(resultado.erros)})
    return resultado.to_dict()


@router.post("/validar-400")
async def validar_arquivo_400(arquivo: UploadFile = File(...)):
    """
    Recebe um arquivo de remessa/retorno CNAB 400 e valida a estrutura
    genérica (tamanho de linha, sequência header/detalhe/trailer). Ainda
    não valida campo a campo do registro de detalhe -- isso é específico
    por banco.
    """
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = validar_cnab400(conteudo)
    registrar_uso("cnab", "validar-400", {"valido": resultado.valido, "total_erros": len(resultado.erros)})
    return resultado.to_dict()


@router.post("/validar-400-caixa")
async def validar_arquivo_400_caixa(arquivo: UploadFile = File(...)):
    """
    Recebe um arquivo de remessa/retorno CNAB 400 de Cobrança Bancária da
    Caixa, detecta sozinho se é remessa ou retorno, e valida campo a
    campo (inclusive Nosso Número, valor do título, dados do pagador).
    """
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = validar_cnab400_caixa(conteudo)
    registrar_uso("cnab", "validar-400-caixa", {"valido": resultado.valido, "total_erros": len(resultado.erros)})
    return resultado.to_dict()


@router.post("/corrigir-240")
async def corrigir_arquivo_240(arquivo: UploadFile = File(...)):
    """
    Corrige automaticamente só os erros de valor fixo/constante (ex: tipo
    de registro, lote de serviço). Dado de negócio nunca é corrigido
    sozinho -- volta em "erros_restantes" pro analista resolver no RM.
    """
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = corrigir_cnab240(conteudo)
    registrar_uso("cnab", "corrigir-240", {"total_corrigido": resultado.total_corrigido, "total_pendente": resultado.total_pendente})
    return resultado.to_dict()


@router.post("/traduzir-erro")
def traduzir_erro(
    banco: str, codigo_erro: str, mensagem: str = "", tabela: str | None = None
):
    """Traduz um erro devolvido pelo banco (registro online) numa dica pro RM."""
    erro = traduzir_erro_banco(banco, codigo_erro, mensagem, tabela)
    return erro.to_dict()


@router.post("/validar-400-bb")
async def validar_arquivo_cnab400_bb(arquivo: UploadFile = File(...)):
    if not arquivo.filename.upper().endswith((".TXT", ".RET", ".REM")):
        raise HTTPException(
            status_code=400, detail="O arquivo deve ser um .TXT, .RET ou .REM."
        )

    try:
        conteudo_bytes = await arquivo.read()
        conteudo_texto = conteudo_bytes.decode("utf-8", errors="replace")
        
        resultado = validar_cnab400_bb(conteudo_texto)
        return resultado.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))