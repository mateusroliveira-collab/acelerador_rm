import re
import xml.etree.ElementTree as ET
from ..cnab.cnab240.validador_caixa import validar_cnab240_caixa
from ..cnab.cnab240.validador_bb import validar_cnab240_bb
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..cnab.bancos.caixa import buscar_erro

class PayloadXML(BaseModel):
    xml: str

def sanitizar_xml_cole(xml_str: str) -> str:
    """
    Remove prefixos de namespace (ex: <ext:TAG>, </sib:TAG>) do XML colado.
    Permite que qualquer trecho de log do RM seja lido sem erro de 'unbound prefix'.
    """
    xml_str = xml_str.strip()
    # Remove o prefixo das tags de abertura e fechamento (ex: <ext:TITULO> vira <TITULO>)
    xml_limpo = re.sub(r'<(/?)[a-zA-Z0-9_]+:([a-zA-Z0-9_]+)', r'<\1\2', xml_str)
    return xml_limpo

@router.post("/validar-xml-caixa")
async def validar_xml_caixa(payload: PayloadXML):
    erros = []
    
    if not payload.xml or not payload.xml.strip():
        return {
            "valido": False, 
            "erros": [{
                "mensagem": "O XML colado está vazio.", 
                "campo": "Texto", 
                "sugestao_rm": "Cole o XML de requisição do log do RM."
            }]
        }

    # 1. Higieniza o XML colado removendo sujeiras de namespace
    xml_tratado = sanitizar_xml_cole(payload.xml)

    try:
        root = ET.fromstring(xml_tratado)
        
        def get_tag_text(tag_name):
            for elem in root.iter():
                if elem.tag.upper() == tag_name.upper():
                    return elem.text
            return None

        # 2. Mapeamento de Validação de Campos
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
                
        # 3. Validação do Nosso Número Caixa (deve ter 17 dígitos e começar com 14)
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

        # 4. Validação de Documento do Pagador
        cpf = get_tag_text("CPF")
        cnpj = get_tag_text("CNPJ")
        if (not cpf or not cpf.strip()) and (not cnpj or not cnpj.strip()):
            erros.append({
                "mensagem": "É obrigatório enviar CPF ou CNPJ do pagador.",
                "campo": "<CPF> ou <CNPJ>",
                "valor_encontrado": "Nenhum",
                "sugestao_rm": "Acessar módulo Gestão Financeira > Cadastros > Específicos > Clientes / Fornecedores > Filtrar o cliente > Editar > Preencher CPF/CNPJ."
            })

    except ET.ParseError as e:
        erros.append({
            "mensagem": f"Estrutura de tags XML corrompida ou incompleta: {str(e)}",
            "campo": "Estrutura XML",
            "valor_encontrado": "N/A",
            "sugestao_rm": "Certifique-se de ter copiado o bloco de tags completo do log do RM (ex: de <ext:SERVICO_ENTRADA> até </ext:SERVICO_ENTRADA>)."
        })
    
    return {"valido": len(erros) == 0, "erros": erros}

@router.post("/validar-240-caixa")
async def validar_arquivo_240_caixa(arquivo: UploadFile = File(...)):
    """Valida arquivo CNAB 240 da Caixa com regras de negócio e Dicas RM."""
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = validar_cnab240_caixa(conteudo)
    try:
        registrar_uso("cnab", "validar-240-caixa", {"valido": resultado.valido, "total_erros": len(resultado.erros)})
    except Exception:
        pass
    return resultado.to_dict()

@router.post("/validar-240-bb")
async def validar_arquivo_240_bb(arquivo: UploadFile = File(...)):
    """Valida arquivo CNAB 240 do Banco do Brasil com Dicas RM."""
    conteudo_bytes = await arquivo.read()
    conteudo = conteudo_bytes.decode("utf-8-sig", errors="replace")
    resultado = validar_cnab240_bb(conteudo)
    try:
        registrar_uso("cnab", "validar-240-bb", {"valido": resultado.valido, "total_erros": len(resultado.erros)})
    except Exception:
        pass
    return resultado.to_dict()