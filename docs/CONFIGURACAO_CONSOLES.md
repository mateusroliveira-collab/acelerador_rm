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
| `PLANILHA_MODELO_GLB_USUARIO` | Não | Link da planilha-modelo no Google Sheets (seção 4). Sem ele, só não aparece a opção do Google: o modelo Excel funciona sempre |
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

## 4. Planilha-modelo (para o cliente preencher)
**O modelo Excel (.xlsx) é gerado pelo próprio site** e não exige configuração em console nenhum.
O analista baixa em *Gerador de DataServer > Em lote > Baixar modelo Excel*, e o cliente pode baixar em
`https://SEU-APP.vercel.app/planilha-modelo` (botão *Copiar link para o cliente* na tela do analista).

**Opcional — planilha do Google Sheets** (para quem prefere trabalhar no Google):
- [ ] Monte a planilha conforme `docs/PLANILHA_MODELO.md`.
- [ ] **Compartilhar > Acesso geral > "Qualquer pessoa com o link" > Leitor.**
- [ ] Cadastre o link na Vercel como `PLANILHA_MODELO_GLB_USUARIO` e faça um **Redeploy**. Aparece o botão
      *Criar cópia no Google Sheets* na página do cliente e *Abrir planilha modelo* na tela do analista.
- Quem copia vira dono da cópia dele e pode alterar tudo (inclusive o cabeçalho); a ferramenta valida
  tudo de novo ao receber os dados.

## 5. Conector RM (nenhuma configuração de console)
O conector roda na máquina de cada analista e é baixado pela própria tela (`/conector-rm`), que
monta o comando com o endereço do RM e a origem do site. Não há variável de ambiente, chave nem
segredo no servidor: o site não se conecta ao RM. Requisito na máquina do analista: Python 3.9+ e
acesso de rede ao RM (VPN do cliente, se for o caso). Ver [GUIA_DO_ANALISTA.md](GUIA_DO_ANALISTA.md#6-conector-rm).

## 6. GitHub
- [ ] O `.gitignore` já ignora `.env`, `.env.local` e `*.db`. Confira com `git status` que nenhum
      segredo aparece antes de cada commit.
