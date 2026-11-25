"""
Módulo GlbUsuarioData (Cadastro de Usuário do RM -- tabela GUSUARIO).

Origem do schema: resposta real de GET no REST do DataServer (nomes e tipos
dos campos) + tela "Usuário" do RM (quais campos são obrigatórios: os que
aparecem em negrito -- Usuário, Código de Acesso, Login OIDC e Início de
Validade).

Formato: a planilha e o JSON seguem o retorno do GET -- nomes técnicos dos
campos, na mesma ordem, booleanos como o RM grava (1/0 e T/F) e, no JSON,
o envelope {"messages", "length", "data"} com todas as chaves do GET.

DE PROPÓSITO fora da planilha e do envio (saem null no JSON):
 - SENHA (e qualquer credencial): a ferramenta nunca pede nem gera senha;
   no RM a senha de usuário novo fica desabilitada, e a primeira senha segue
   o fluxo de "Alterar senha no próximo login";
 - segredos (TOTPSECRETKEY, senhas de redes sociais, histórico de senhas);
 - campos controlados pelo RM (último acesso, logins inválidos, CONTROLE...).
"""

from ..base import BOOLEANO, DATA, EMAIL, INTEIRO, TEXTO, Campo, Modulo, valor_no_payload

# Fuso usado nas datas (o RM devolve "-03:00"/"-02:00" conforme o horário de verão).
FUSO_PADRAO = "-03:00"

# Todas as chaves do GET de GlbUsuarioData, NA ORDEM em que o RM devolve.
# O JSON de saída segue exatamente este formato.
CAMPOS_GET = (
    "id", "CODUSUARIO", "NOME", "CODACESSO", "STATUS", "DATAINICIO", "IGNORARAUTENTICACAOLDAP",
    "DATAEXPIRACAO", "DATAULTIMOACESSO", "CODUSUARIOREDE", "DOMINIOREDE", "EMAIL", "NOMESOCIAL",
    "DATAULTIMOACESSOVALIDO", "CODEXTERNO", "INTEGRADOFLUIG", "OIDC_ENABLED", "TOTPSECRETKEY",
    "CONFIRMABTNOK", "SENHA", "CONTROLE", "ULTIMACOLIGADA", "DTAEXPSENHA", "DIASEXPSENHA",
    "OBRIGAALTERARSENHA", "NUMLOGININVALIDO", "DATALOGININVALIDO", "ACESSONET", "LIVEID",
    "USUARIOTWITTER", "SENHATWITTER", "USUARIOFACEBOOK", "SENHAFACEBOOK", "USUARIOLINKEDIN",
    "SENHALINKEDIN", "FULLDETERMINED", "USERID", "USERIDFLUIGIDENTITY", "ULTIMASSENHAS",
)

# Chaves do GET que NUNCA são preenchidas pela ferramenta (saem null no JSON e
# não vão no envio): credenciais/segredos e campos que o próprio RM controla.
CREDENCIAIS = ("SENHA", "TOTPSECRETKEY", "SENHATWITTER", "SENHAFACEBOOK", "SENHALINKEDIN", "ULTIMASSENHAS")
CONTROLADOS_PELO_RM = ("id", "DATAULTIMOACESSO", "DATAULTIMOACESSOVALIDO", "CONTROLE", "DTAEXPSENHA",
                       "NUMLOGININVALIDO", "DATALOGININVALIDO")

_INFERIDO = "Tipo inferido (o exemplo do RM veio vazio): confirme em homologação."

# Na ordem do GET (é a ordem das colunas da planilha e do formulário).
CAMPOS = (
    Campo("CODUSUARIO", "Usuário", obrigatorio=True,
          ajuda="Login do usuário no RM. É a chave do registro."),
    Campo("NOME", "Nome"),
    Campo("CODACESSO", "Código de Acesso", obrigatorio=True,
          ajuda="Código do grupo/perfil de acesso já cadastrado no RM (ex.: Acesso01)."),
    Campo("STATUS", "Ativo", tipo=BOOLEANO, padrao=True, ajuda="1 = usuário ativo; 0 = inativo. Vazio = 1."),
    Campo("DATAINICIO", "Início de Validade", tipo=DATA, obrigatorio=True,
          ajuda="Data DD/MM/AAAA (ou AAAA-MM-DD). Padrão do formulário: hoje."),
    Campo("IGNORARAUTENTICACAOLDAP", "Ignorar autenticação LDAP", tipo=BOOLEANO,
          padrao=False, aba="Rede", formato_booleano="TF", ajuda="T = sim; F = não. Vazio = F."),
    Campo("DATAEXPIRACAO", "Expiração de Validade", tipo=DATA,
          ajuda='Data DD/MM/AAAA. Vazio = "Sempre é válido".'),
    Campo("CODUSUARIOREDE", "Usuário de rede", aba="Rede"),
    Campo("DOMINIOREDE", "Domínio de rede", aba="Rede"),
    Campo("EMAIL", "E-Mail", tipo=EMAIL),
    Campo("NOMESOCIAL", "Nome Social"),
    Campo("CODEXTERNO", "Código externo", aba="Outros"),
    Campo("INTEGRADOFLUIG", "Integrado ao Fluig", tipo=INTEIRO, aba="Outros",
          ajuda="0 ou 1. Vazio = não envia (o RM mantém o valor dele)."),
    Campo("OIDC_ENABLED", "Login OIDC", tipo=BOOLEANO, padrao=False, obrigatorio=True,
          ajuda="1 = sim; 0 = não. Vazio = 0."),
    Campo("CONFIRMABTNOK", "Confirma botão OK", tipo=INTEIRO, aba="Outros", ajuda=_INFERIDO),
    Campo("ULTIMACOLIGADA", "Última coligada", tipo=INTEIRO, aba="Outros",
          ajuda="Código da coligada que abre por padrão."),
    Campo("DIASEXPSENHA", "Força a troca de senha a cada (dias)", tipo=INTEIRO,
          ajuda="Deixe vazio para não forçar a troca periódica."),
    Campo("OBRIGAALTERARSENHA", "Alterar senha no próximo login", tipo=BOOLEANO, padrao=True,
          ajuda="1 = sim; 0 = não. Vazio = 1."),
    Campo("ACESSONET", "Acesso .NET", tipo=INTEIRO, aba="Outros", ajuda=_INFERIDO),
    Campo("LIVEID", "Live ID", aba="Outros"),
    Campo("USUARIOTWITTER", "Usuário Twitter", aba="Outros"),
    Campo("USUARIOFACEBOOK", "Usuário Facebook", aba="Outros"),
    Campo("USUARIOLINKEDIN", "Usuário LinkedIn", aba="Outros"),
    Campo("FULLDETERMINED", "Full determined", tipo=INTEIRO, aba="Outros", ajuda=_INFERIDO),
    Campo("USERID", "User ID", aba="Outros"),
    Campo("USERIDFLUIGIDENTITY", "User ID Fluig Identity", aba="Outros"),
)

_POR_NOME = {c.nome: c for c in CAMPOS}
# Garantias do formato: campos do schema na mesma ordem do GET, sem credencial.
assert [c.nome for c in CAMPOS] == [k for k in CAMPOS_GET if k in _POR_NOME]
assert not set(_POR_NOME) & set(CREDENCIAIS + CONTROLADOS_PELO_RM)


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
    """
    Corpo do ENVIO (POST/PUT) no formato do REST do DataServer, na ordem do GET:
    só campos preenchidos (ou booleanos). Não leva null de propósito: num PUT,
    um null apagaria o que já está no RM. O JSON completo, igual ao GET, é o
    `registro_completo` (base.py).
    """
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
    nome_envio = f"GlbUsuarioData_{operacao}_{cod}_envio.json"
    base = "https://<SEU_SERVIDOR>:<PORTA>/rmsrestdataserver/rest/GlbUsuarioData"
    if operacao == "incluir":
        envio = f'curl -X POST "{base}" -H "Content-Type: application/json" -u "<SEU_USUARIO_RM>:<SUA_SENHA_RM>" --data "@{nome_envio}"'
    else:
        envio = f'curl -X PUT "{base}/{cod}" -H "Content-Type: application/json" -u "<SEU_USUARIO_RM>:<SUA_SENHA_RM>" --data "@{nome_envio}"'
    return {
        "nome_arquivo": nome_arquivo,
        "nome_arquivo_envio": nome_envio,
        "instrucoes": [
            "Esta ferramenta NÃO envia nada ao RM: o arquivo gerado é enviado por você.",
            "O JSON da prévia está no mesmo formato do GET do RM (messages, length, data; todos os campos). "
            "Para o POST/PUT use o \"corpo do envio\": só o registro, só com os campos preenchidos.",
            "Teste primeiro em um ambiente de homologação.",
            f"Exemplo de envio (ajuste servidor, porta e autenticação ao seu ambiente): {envio}",
            "No SOAP UI/Postman/Insomnia: use o mesmo endereço, método "
            + ("POST" if operacao == "incluir" else "PUT")
            + ', cabeçalho Content-Type: application/json e cole o corpo do envio.',
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
    nome="Cadastro da GUSUARIO",
    dataserver="GlbUsuarioData",
    descricao="Gera o JSON para incluir ou alterar um usuário (tabela GUSUARIO) via REST do DataServer.",
    campos=CAMPOS,
    operacoes=("incluir", "alterar"),
    regras=_regras,
    avisos=_avisos,
    entrega=_entrega,
    entrega_lote=_entrega_lote,
    campo_chave="CODUSUARIO",
    versao_schema="2",  # v2: colunas com os nomes do RM, na ordem do GET, valores 1/0 e T/F
    tabela_xml="GUSUARIO",
    listas_config={"codigos_acesso": "CODACESSO"},
    campos_saida=CAMPOS_GET,
    id_do_registro=lambda payload: payload.get("CODUSUARIO"),
    campos_nao_enviar=CREDENCIAIS + CONTROLADOS_PELO_RM,
    nao_validado=(
        "Tamanhos máximos dos campos não foram confirmados (só há um teto geral de 255 caracteres).",
        "Os formatos de OBRIGAALTERARSENHA (1/0), DIASEXPSENHA, INTEGRADOFLUIG, CONFIRMABTNOK, "
        "ULTIMACOLIGADA, ACESSONET e FULLDETERMINED (inteiros) foram inferidos: o exemplo recebido "
        "só tinha esses campos vazios ou zerados.",
        "Credenciais (SENHA, TOTPSECRETKEY, senhas de redes sociais, ULTIMASSENHAS) e campos que o RM "
        "controla (último acesso, logins inválidos, CONTROLE, DTAEXPSENHA) saem null no JSON e nunca "
        "vão no envio.",
        "A URL do REST, a porta e a autenticação são do seu ambiente (placeholders nas instruções).",
        "A alteração (PUT) usa o código do usuário na URL -- confirme no seu ambiente.",
        "O XML (DataSet para SaveRecord) foi inferido do padrão do RM e não foi confirmado: valide em homologação.",
    ),
)
