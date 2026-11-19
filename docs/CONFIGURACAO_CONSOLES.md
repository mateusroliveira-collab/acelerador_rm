# Configuração nos consoles (Vercel, Neon, Google)

Este projeto **não guarda chaves nem tokens de terceiros no código**. Tudo o que
é segredo vive nos consoles abaixo, configurado por você. Marque cada item ao concluir.

## 1. Neon (banco)
- [ ] No console do Neon, abra o projeto > **Connection Details** e marque **Pooled connection**.
- [ ] Copie a URL cujo host termina em `-pooler`. Ela vai no passo 2 (`DATABASE_URL`).
- [ ] (Recomendado) Em **Settings > Compute**, avalie desligar o "suspender após inatividade" ou
      aceitar o primeiro acesso mais lento depois de ociosidade.

## 2. Vercel (hospedagem)
Em **Project > Settings > Environment Variables** (ambiente *Production*; repita em *Preview* se usar):

| Variável | Obrigatória | Valor |
|---|---|---|
| `DATABASE_URL` | **Sim** | URL *pooled* do Neon (passo 1) |
| `PLANILHA_MODELO_GLB_USUARIO` | Não | Link da planilha-modelo no Google Sheets (seção 4). Sem ele, a tela mostra só o modelo CSV |
| `API_KEYS` | Não | `chave1:clienteA,chave2:clienteB` (chaves longas e aleatórias) |
| `API_EXIGIR_CHAVE` | Não | `1` para recusar chamadas sem chave (ver aviso abaixo) |
| `RATE_LIMIT_POR_MINUTO` | Não | ex.: `120` (limite aproximado por instância) |

- [ ] Depois de salvar variáveis, faça um **Redeploy** (variáveis só valem em novos deploys).
- [ ] Confirme que `GET https://SEU-APP.vercel.app/api/health` responde `{"status":"ok"}`.
- [ ] Confirme que `GET https://SEU-APP.vercel.app/api/v1/dataserver/modulos` lista o módulo.

> **Aviso sobre `API_EXIGIR_CHAVE=1`:** a tela web do próprio app não envia chave (uma chave no
> navegador seria pública). Com a exigência ligada, a tela deixa de funcionar até existir login
> ou um proxy autenticado na frente. Para uso interno, deixe desligada e use as chaves apenas
> para identificar clientes e aplicar o limite de uso.

## 3. Cadastro de clientes (configuração fora do código)
Não há rota de escrita na API. Na sua máquina, com o venv ativo:

```powershell
# aponta para o Neon só nesta sessão do terminal (não salve em arquivo)
$env:DATABASE_URL = "postgresql://...-pooler.../banco?sslmode=require"
python scripts/cliente_config.py definir acme --nome "ACME S.A." --codigos-acesso Acesso01,Acesso02
python scripts/cliente_config.py listar
```
O script mostra o servidor de destino (sem usuário/senha) antes de gravar.
Guarde **somente configuração** (códigos de acesso, versão do RM) — nunca dado pessoal.

## 4. Planilha-modelo no Google Sheets (para o cliente preencher)
**Não há script, nem projeto no Google Cloud, nem chave.** A planilha é um arquivo comum no seu Drive;
o app só guarda o **link** dela.

- [ ] Crie a planilha no seu Google Drive e monte conforme `docs/PLANILHA_MODELO.md`
      (abas Dados, Listas e Instruções; cabeçalhos, validações e proteção).
- [ ] **Compartilhar > Acesso geral > "Qualquer pessoa com o link" > Leitor.**
      (É o que permite ao cliente abrir o link de cópia. A planilha-modelo não tem dados de ninguém.)
- [ ] Copie o link da barra de endereços e cadastre na Vercel como `PLANILHA_MODELO_GLB_USUARIO`
      (seção 2). Faça um **Redeploy**.
- [ ] Abra o Gerador de DataServer: aparece o botão **Abrir planilha modelo**, que leva à tela
      "Fazer uma cópia" do Google.

**Fluxo por cliente (recomendado):** abra o botão, faça a cópia, edite a aba **Listas** com os códigos
de acesso do cliente e **compartilhe a cópia com o cliente como _Editor_**. Assim o cliente não é dono
da planilha e **não consegue alterar o cabeçalho nem as abas protegidas**. Se você mandar direto o link de cópia, o
cliente vira dono da cópia dele e pode mexer em tudo — funciona, mas a ferramenta é que garante a qualidade,
porque valida tudo de novo ao receber os dados.

## 5. GitHub
- [ ] O `.gitignore` já ignora `.env`, `.env.local` e `*.db`. Confira com `git status` que nenhum
      segredo aparece antes de cada commit.
