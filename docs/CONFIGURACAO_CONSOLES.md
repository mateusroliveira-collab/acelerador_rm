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

## 4. Google (Apps Script) — para a planilha no Google Sheets
**Não é preciso criar projeto no Google Cloud Console.** O script fica "preso" à planilha
(*container-bound*) e usa só permissões da conta de quem o executa.

- [ ] Crie a planilha-modelo no seu Google Drive.
- [ ] **Extensões > Apps Script**. Em **Configurações do projeto**, marque
      *Mostrar arquivo de manifesto "appsscript.json" no editor*.
- [ ] Cole o conteúdo de `appsscript.json` (baixe na tela do Gerador de DataServer, ou use o arquivo
      de `google-sheets/`) e o de `Codigo.gs` (baixe **pela tela do Gerador**: ele já vem com o endereço da API).
- [ ] Salve, recarregue a planilha: aparece o menu **Acelerador RM**.
- [ ] Na primeira execução o Google pede autorização e mostra *"app não verificado"*: é esperado para
      um script seu. **Avançado > Acessar (não seguro) > Permitir**. As permissões pedidas são só:
      planilha atual, janelas do menu, chamadas externas e e-mail da conta.
- [ ] Siga o roteiro de teste em `google-sheets/README.md`.

Para publicar além da sua organização (produto), o caminho correto é um **Add-on** com revisão do Google —
projeto à parte, fora deste escopo.

## 5. GitHub
- [ ] O `.gitignore` já ignora `.env`, `.env.local` e `*.db`. Confira com `git status` que nenhum
      segredo aparece antes de cada commit.
