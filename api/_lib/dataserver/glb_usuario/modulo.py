"""
Módulo GlbUsuarioData (Cadastro de Usuário do RM -- tabela GUSUARIO).

Origem do schema: resposta real de GET no REST do DataServer (nomes e tipos
dos campos) + tela "Usuário" do RM (quais campos são obrigatórios: os que
aparecem em negrito -- Usuário, Código de Acesso, Login OIDC e Início de
Validade).

DE PROPÓSITO fora do payload:
 - SENHA (e qualquer credencial): a ferramenta nunca pede nem gera senha;
   no RM a senha de usuário novo fica desabilitada, e a primeira senha segue
   o fluxo de "Alterar senha no próximo login";
 - campos controlados pelo RM (último acesso, logins inválidos, histórico de
   senhas, CONTROLE...), segredos (TOTPSECRETKEY, senhas de redes sociais)
   e integrações (Fluig, USERID...).
"""

from ..base import BOOLEANO, DATA, EMAIL, INTEIRO, TEXTO, Campo, Modulo, valor_no_payload

# Fuso usado nas datas (o RM devolve "-03:00"/"-02:00" conforme o horário de verão).
FUSO_PADRAO = "-03:00"

CAMPOS = (
    # --- aba Identificação ---
    Campo("CODUSUARIO", "Usuário", obrigatorio=True,
          ajuda="Login do usuário no RM. É a chave do registro."),
    Campo("NOME", "Nome"),
    Campo("NOMESOCIAL", "Nome Social"),
    Campo("EMAIL", "E-Mail", tipo=EMAIL),
    Campo("CODACESSO", "Código de Acesso", obrigatorio=True,
          ajuda="Código do grupo/perfil de acesso já cadastrado no RM (ex.: Acesso01)."),
    Campo("STATUS", "Ativo", tipo=BOOLEANO, padrao=True, ajuda="Sim = usuário ativo; Não = inativo."),
    Campo("OIDC_ENABLED", "Login OIDC", tipo=BOOLEANO, padrao=False, obrigatorio=True),
    Campo("OBRIGAALTERARSENHA", "Alterar senha no próximo login", tipo=BOOLEANO, padrao=True),
    Campo("DIASEXPSENHA", "Força a troca de senha a cada (dias)", tipo=INTEIRO,
          ajuda="Deixe vazio para não forçar a troca periódica."),
    Campo("DATAINICIO", "Início de Validade", tipo=DATA, obrigatorio=True,
          ajuda="Formato AAAA-MM-DD. Padrão: hoje."),
    Campo("DATAEXPIRACAO", "Expiração de Validade", tipo=DATA,
          ajuda='Vazio = "Sempre é válido".'),
    # --- aba Rede ---
    Campo("CODUSUARIOREDE", "Usuário de rede", aba="Rede"),
    Campo("DOMINIOREDE", "Domínio de rede", aba="Rede"),
    Campo("IGNORARAUTENTICACAOLDAP", "Ignorar autenticação LDAP", tipo=BOOLEANO,
          padrao=False, aba="Rede", formato_booleano="TF"),
)

_POR_NOME = {c.nome: c for c in CAMPOS}


def _regras(valores: dict, operacao: str) -> list[dict]:
    erros = []
    ini, fim = valores.get("DATAINICIO"), valores.get("DATAEXPIRACAO")
    if ini and fim and fim < ini:
        erros.append({"campo": "DATAEXPIRACAO",
                      "mensagem": "Expiração de Validade não pode ser anterior ao Início de Validade."})
    return erros


def _avisos(valores: dict, operacao: str) -> list[str]:
    avisos = []
    cod = valores.get("CODUSUARIO") or ""
    if any(ch.isspace() for ch in cod):
        avisos.append("O código do usuário tem espaços -- confira se o RM aceita esse formato.")
    if bool(valores.get("CODUSUARIOREDE")) != bool(valores.get("DOMINIOREDE")):
        avisos.append("Usuário de rede e Domínio de rede costumam ser preenchidos juntos.")
    if valores.get("OIDC_ENABLED") and not valores.get("EMAIL"):
        avisos.append("Login OIDC ligado sem e-mail: normalmente o provedor identifica o usuário pelo e-mail.")
    if not valores.get("STATUS"):
        avisos.append("O usuário será gerado INATIVO (STATUS 0).")
    return avisos


def gerar_payload(valores: dict, fuso: str = FUSO_PADRAO) -> dict:
    """Payload no formato do REST do DataServer: só campos preenchidos (ou booleanos)."""
    payload = {}
    for c in CAMPOS:
        v = valores.get(c.nome)
        if v is None:
            continue
        payload[c.nome] = valor_no_payload(c, v, fuso)
    return payload


def _entrega(payload: dict, operacao: str) -> dict:
    cod = payload.get("CODUSUARIO", "usuario")
    nome_arquivo = f"GlbUsuarioData_{operacao}_{cod}.json"
    base = "https://<SEU_SERVIDOR>:<PORTA>/rmsrestdataserver/rest/GlbUsuarioData"
    if operacao == "incluir":
        envio = f'curl -X POST "{base}" -H "Content-Type: application/json" -u "<SEU_USUARIO_RM>:<SUA_SENHA_RM>" --data "@{nome_arquivo}"'
    else:
        envio = f'curl -X PUT "{base}/{cod}" -H "Content-Type: application/json" -u "<SEU_USUARIO_RM>:<SUA_SENHA_RM>" --data "@{nome_arquivo}"'
    return {
        "nome_arquivo": nome_arquivo,
        "instrucoes": [
            "Esta ferramenta NÃO envia nada ao RM: o arquivo gerado é enviado por você.",
            "Salve o JSON gerado (botão Baixar) e confira o conteúdo na prévia.",
            "Teste primeiro em um ambiente de homologação.",
            f"Exemplo de envio (ajuste servidor, porta e autenticação ao seu ambiente): {envio}",
            "No SOAP UI/Postman/Insomnia: use o mesmo endereço, método "
            + ("POST" if operacao == "incluir" else "PUT")
            + ', cabeçalho Content-Type: application/json e cole o JSON como corpo.',
            "Confira no RM (Usuários) se o registro foi criado/atualizado como esperado.",
            "Nunca coloque usuário e senha do RM neste site nem no arquivo gerado.",
        ],
    }


def _entrega_lote(operacao: str, nome_arquivo: str, total: int) -> list:
    base = "https://<SEU_SERVIDOR>:<PORTA>/rmsrestdataserver/rest/GlbUsuarioData"
    metodo = "Post" if operacao == "incluir" else "Put"
    uri = f'"{base}"' if operacao == "incluir" else f'"{base}/$cod"'
    linhas_script = ["$cred = Get-Credential   # pede usuário/senha do RM na hora; nada fica salvo"]
    linhas_script.append('Get-Content ".\\' + nome_arquivo + '" -Encoding UTF8 | ForEach-Object {')
    if operacao != "incluir":
        linhas_script.append("    $cod = ($_ | ConvertFrom-Json).CODUSUARIO")
    linhas_script.append(
        f"    Invoke-RestMethod -Method {metodo} -Uri {uri} -Credential $cred "
        "-ContentType 'application/json; charset=utf-8' "
        "-Body ([Text.Encoding]::UTF8.GetBytes($_))"
    )
    linhas_script.append("}")
    script = "\n".join(linhas_script)
    return [
        "Esta ferramenta NÃO envia nada ao RM: o envio é feito por você.",
        f"Foram gerados {total} registro(s) válido(s), um JSON por linha no arquivo .jsonl (o REST do DataServer recebe um registro por chamada).",
        "Linhas com erro ficam de fora do arquivo: corrija a planilha e gere de novo, ou envie só o que está válido.",
        "Teste primeiro em homologação, com poucas linhas.",
        "Exemplo de envio em PowerShell, na pasta onde salvou o arquivo "
        "(ajuste servidor, porta e autenticação ao seu ambiente):\n" + script,
        "Confira no RM (Usuários) se os registros foram criados/atualizados como esperado.",
        "Nunca coloque usuário e senha do RM neste site nem nos arquivos gerados.",
    ]


MODULO = Modulo(
    chave="glb-usuario",
    nome="Cadastro de Usuário",
    dataserver="GlbUsuarioData",
    descricao="Gera o JSON para incluir ou alterar um usuário (tabela GUSUARIO) via REST do DataServer.",
    campos=CAMPOS,
    operacoes=("incluir", "alterar"),
    regras=_regras,
    avisos=_avisos,
    entrega=_entrega,
    entrega_lote=_entrega_lote,
    campo_chave="CODUSUARIO",
    versao_schema="1",
    tabela_xml="GUSUARIO",
    listas_config={"codigos_acesso": "CODACESSO"},
    nao_validado=(
        "Tamanhos máximos dos campos não foram confirmados (só há um teto geral de 255 caracteres).",
        "Os formatos de OBRIGAALTERARSENHA (1/0) e DIASEXPSENHA (inteiro) foram inferidos: o exemplo "
        "recebido só tinha esses campos vazios.",
        "A URL do REST, a porta e a autenticação são do seu ambiente (placeholders nas instruções).",
        "A alteração (PUT) usa o código do usuário na URL -- confirme no seu ambiente.",
        "O XML (DataSet para SaveRecord) foi inferido do padrão do RM e não foi confirmado: valide em homologação.",
    ),
)
