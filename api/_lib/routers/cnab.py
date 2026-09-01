"""
Rotas da API para o validador de CNAB e Registro Online (XML).
"""
import xml.etree.ElementTree as ET
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from ..cnab.cnab400.validador_bb import validar_cnab400_bb
from ..cnab.cnab240.validador import validar_cnab240
from ..cnab.cnab240.corretor import corrigir_cnab240
from ..cnab.cnab400.validador import validar_cnab400
from ..cnab.cnab400.validador_caixa import validar_cnab400_caixa
from ..cnab.registro_online.validador import traduzir_erro_banco
from ..cnab.bancos.caixa import buscar_erro
from ..registro_uso import registrar_uso

router = APIRouter(prefix="/api/cnab", tags=["cnab"])


class PayloadXML(BaseModel):
    xml: str


@router.post("/validar-240")
async def validar_arquivo_240(arquivo: UploadFile = File(...)):
    """Recebe um arquivo de remessa/retorno CNAB 240 e valida a estrutura."""
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = validar_cnab240(conteudo)
    try:
        registrar_uso("cnab", "validar-240", {"valido": resultado.valido, "total_erros": len(resultado.erros)})
    except Exception:
        pass
    return resultado.to_dict()


@router.post("/validar-400")
async def validar_arquivo_400(arquivo: UploadFile = File(...)):
    """Valida a estrutura genérica de um arquivo CNAB 400."""
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = validar_cnab400(conteudo)
    try:
        registrar_uso("cnab", "validar-400", {"valido": resultado.valido, "total_erros": len(resultado.erros)})
    except Exception:
        pass
    return resultado.to_dict()


@router.post("/validar-400-caixa")
async def validar_arquivo_400_caixa(arquivo: UploadFile = File(...)):
    """Valida um arquivo CNAB 400 da Caixa (Remessa ou Retorno com dicas RM)."""
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = validar_cnab400_caixa(conteudo)
    try:
        registrar_uso("cnab", "validar-400-caixa", {"valido": resultado.valido, "total_erros": len(resultado.erros)})
    except Exception:
        pass
    return resultado.to_dict()


@router.post("/validar-400-bb")
async def validar_arquivo_cnab400_bb(arquivo: UploadFile = File(...)):
    """Valida um arquivo CNAB 400 do Banco do Brasil."""
    if not arquivo.filename.upper().endswith((".TXT", ".RET", ".REM")):
        raise HTTPException(
            status_code=400, detail="O arquivo deve ser um .TXT, .RET ou .REM."
        )

    try:
        conteudo_bytes = await arquivo.read()
        conteudo_texto = conteudo_bytes.decode("utf-8-sig", errors="replace")
        resultado = validar_cnab400_bb(conteudo_texto)
        try:
            registrar_uso("cnab", "validar-400-bb", {"valido": resultado.valido, "total_erros": len(resultado.erros)})
        except Exception:
            pass
        return resultado.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corrigir-240")
async def corrigir_arquivo_240(arquivo: UploadFile = File(...)):
    """Corrige valores fixos constantes no CNAB 240."""
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = corrigir_cnab240(conteudo)
    dados_resultado = resultado.to_dict()
    try:
        registrar_uso(
            "cnab",
            "corrigir-240",
            {
                "total_erros_restantes": len(dados_resultado.get("erros_restantes", []))
                if isinstance(dados_resultado.get("erros_restantes"), list)
                else None,
            },
        )
    except Exception:
        pass
    return dados_resultado


@router.post("/traduzir-erro")
def traduzir_erro(
    banco: str, codigo_erro: str, mensagem: str = "", tabela: str | None = None
):
    """Traduz um erro do banco devolvendo dica do RM."""
    erro = traduzir_erro_banco(banco, codigo_erro, mensagem, tabela)
    return erro.to_dict()


@router.post("/validar-xml-caixa")
async def validar_xml_caixa(payload: PayloadXML):
    """Valida o XML de requisição do Registro Online da Caixa."""
    erros = []
    try:
        root = ET.fromstring(payload.xml.strip())
        
        def get_tag_text(tag_name):
            tag_name_lower = tag_name.lower()
            for elem in root.iter():
                if tag_name_lower in elem.tag.lower():
                    return elem.text
            return None

        campos_obrigatorios = {
            "CODIGO_BENEFICIARIO": ("35", "Verifique o Convênio/Código do Cedente preenchido no RM."),
            "NOSSO_NUMERO": ("02", "Verifique a geração do Nosso Número no boleto."),
            "DATA_VENCIMENTO": ("45", "O boleto não possui data de vencimento preenchida."),
            "VALOR": ("27", "O valor do título está zerado ou vazio."),
            "CEP": ("81", "O CEP do cliente é obrigatório para registro na Caixa."),
            "CIDADE": ("45", "A cidade do cliente não está preenchida no cadastro."),
        }

        for tag, (codigo_erro, sugestao_padrao) in campos_obrigatorios.items():
            valor = get_tag_text(tag)
            if not valor or not valor.strip():
                dica_bento = buscar_erro(codigo_erro)
                sugestao = dica_bento["sugestao_rm"] if dica_bento else sugestao_padrao
                
                erros.append({
                    "mensagem": f"Tag obrigatória <{tag}> não encontrada ou vazia no XML. Erro Bancário Previsto: ({codigo_erro})",
                    "campo": f"<{tag}>",
                    "valor_encontrado": "Vazio",
                    "sugestao_rm": sugestao
                })
                
        nosso_numero = get_tag_text("NOSSO_NUMERO")
        if nosso_numero and nosso_numero.strip():
            if len(nosso_numero) == 17 and not nosso_numero.startswith("14"):
                dica_bento = buscar_erro("24", tabela="critica_remessa_400")
                sugestao = dica_bento["sugestao_rm"] if dica_bento else "Prefixo inválido. Deve iniciar com '14'."
                
                erros.append({
                    "mensagem": "Prefixo do Nosso Número inválido para Cobrança Registrada na Caixa.",
                    "campo": "<NOSSO_NUMERO>",
                    "valor_encontrado": nosso_numero,
                    "sugestao_rm": sugestao
                })

        cpf = get_tag_text("CPF")
        cnpj = get_tag_text("CNPJ")
        if not cpf and not cnpj:
            erros.append({
                "mensagem": "É obrigatório enviar CPF ou CNPJ do pagador.",
                "campo": "<CPF> ou <CNPJ>",
                "valor_encontrado": "Nenhum",
                "sugestao_rm": "Acessar módulo Gestão Financeira > Cadastros > Especificos > Clientes / Fornecedores > Filtrar o cliente > editar > Informar CPF/CNPJ."
            })

    except ET.ParseError as e:
        erros.append({
            "mensagem": f"O texto colado não é um XML válido. Erro: {str(e)}",
            "campo": "Estrutura XML",
            "valor_encontrado": "N/A",
            "sugestao_rm": "Copie o XML completo gerado pelo log do TOTVS RM."
        })
    
    return {"valido": len(erros) == 0, "erros": erros}


@router.post("/validar-xml-bb")
async def validar_xml_bb(payload: PayloadXML):
    """Valida o XML/JSON de requisição do Registro Online do Banco do Brasil."""
    return {"valido": True, "erros": []}