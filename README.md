# Acelerador RM — Ferramentas de implantação TOTVS RM

Conjunto de ferramentas internas para analistas de implantação do TOTVS RM (Backoffice: Compras,
Estoque, Faturamento, Financeiro). Elas aceleram tarefas manuais, repetitivas e sujeitas a erro
humano: ler a MIT 41, achar e limpar XMLs de parametrização, validar arquivos de banco e carregar
cadastros no RM.

**No ar em:** `https://acelerador-rm.vercel.app`

---

## Princípios (valem para tudo no projeto)

1. **Sem IA em produção.** Toda lógica é regra determinística, testável e explicável: cada
   conclusão mostra o porquê (o trecho da MIT, o parâmetro do XML, a linha e a posição do CNAB).
   Onde a regra não tem certeza, a ferramenta diz isso em vez de chutar.
2. **Sem chaves nem tokens de terceiros.** O site não depende de serviço pago nem de API externa.
3. **O site não se conecta ao RM do cliente e não guarda credenciais.** As chamadas ao RM saem da
   máquina do analista, pelo **conector local**; a senha é digitada na hora e nunca é gravada.
4. **Tudo é validado de novo no servidor.** Planilha protegida, lista suspensa ou validação na
   tela ajudam, mas não são garantia.

---

## As ferramentas

| # | Tela | Para quê | Guia |
|---|---|---|---|
| 01 | **Interpretador de MIT 41** (`/pre-processador-mit41`) | Organiza o PDF bruto da MIT em subprocessos (AS IS / TO BE / GAP) | [guia](docs/GUIA_DO_ANALISTA.md#1-interpretador-de-mit-41) |
| 02 | **Buscador de XML** (`/buscador-xml`) | Acha XML de tipo de movimento, mostra a **regra de negócio** dele e baixa higienizado | [guia](docs/GUIA_DO_ANALISTA.md#2-buscador-de-xml) |
| 03 | **Validador de CNAB** (`/validador-cnab`) | Valida CNAB 240/400 e registro online (BB e Caixa), apontando linha, posição e onde corrigir | [guia](docs/GUIA_DO_ANALISTA.md#3-validador-de-cnab-e-registro-online) |
| 04 | **Gerador de DataServer** (`/gerador-dataserver`) | Planilha-modelo para o cliente, validação em lote e geração do JSON/XML para o RM | [guia](docs/GUIA_DO_ANALISTA.md#4-gerador-de-dataserver) |
| 05 | **Análise da MIT 41** (`/analise-mit41`) | Cruza a MIT inteira com a biblioteca de XMLs: o que já existe, o que ajustar, ficha do que criar | [guia](docs/GUIA_DO_ANALISTA.md#5-análise-da-mit-41) |
| 06 | **Conector RM** (`/conector-rm`) | GET/POST/PUT/DELETE no RM (REST DataServer), como um Postman simplificado | [guia](docs/GUIA_DO_ANALISTA.md#6-conector-rm) |
| — | **Planilha-modelo** (`/planilha-modelo`) | Página pública para o **cliente** baixar a planilha de cadastro | [guia](docs/PLANILHA_MODELO.md) |

Fluxo típico de uma implantação de Compras/Estoque/Faturamento:

```
MIT 41 (PDF) ──► Análise da MIT 41 ──► fichas: pronto / ajustar / criar
                                         │
                                         ▼
                      Buscador de XML (regra de negócio + XML higienizado)
                                         │
                                         ▼
                              parametrização no RM

Cadastros: planilha-modelo ──► cliente preenche ──► Gerador de DataServer (valida)
                                                       │
                                                       ▼
                                     Conector RM (na máquina do analista) ──► RM
```

---

## Arquitetura em uma tabela

| Peça | Escolha |
|---|---|
| Frontend | Next.js 15 (App Router) + Tailwind, em `app/` |
| Backend | FastAPI (Python), empacotado como **uma única função** serverless na Vercel (`api/index.py`) |
| Banco | Neon (Postgres serverless); SQLite automático em desenvolvimento |
| Hospedagem | Vercel |
| Conector RM | Script Python (só biblioteca padrão) que roda na máquina do analista: `public/conector/conector_rm.py` |

Detalhes, rotas, banco e modelo de segurança: [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

> **Atenção:** como o backend é uma função só, **um erro de import em qualquer arquivo derruba a
> API inteira**. Por isso existe o `scripts/smoke_test.py`, que roda antes de todo commit.

---

## Rodando local

```powershell
# Backend (na raiz do projeto)
.venv\Scripts\activate
uvicorn api.index:app --host 127.0.0.1 --port 8000   # sem --reload (trava nesta configuração)

# Frontend (outro terminal, com o backend rodando)
npm run dev
```

- Site: `http://localhost:3000`. Em desenvolvimento, `/api/*` é redirecionado para o uvicorn
  (ver `next.config.mjs`).
- API sozinha: `http://localhost:8000/docs`.
- Sem `DATABASE_URL`, o backend usa um SQLite local (`dev.db`).

Testes e regras de trabalho: [docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md).

```powershell
python -m pytest -q tests          # testes automatizados
python scripts/smoke_test.py       # obrigatório antes de cada commit
```

---

## Documentação

| Documento | Para quem | Conteúdo |
|---|---|---|
| [docs/GUIA_DO_ANALISTA.md](docs/GUIA_DO_ANALISTA.md) | Analistas | Passo a passo de cada tela, limites e dicas |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Desenvolvimento | Peças, rotas da API, banco, segurança, fluxos de dados |
| [docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md) | Desenvolvimento | Ambiente, testes, regras de commit e como estender cada ferramenta |
| [docs/HISTORICO_E_DECISOES.md](docs/HISTORICO_E_DECISOES.md) | Time e coordenação | O que foi feito em cada frente, decisões tomadas e o que ainda falta validar |
| [docs/CONFIGURACAO_CONSOLES.md](docs/CONFIGURACAO_CONSOLES.md) | Quem administra | Vercel, Neon, variáveis de ambiente, cadastro de clientes |
| [docs/PLANILHA_MODELO.md](docs/PLANILHA_MODELO.md) | Analistas | Planilha de cadastro de usuários (GlbUsuarioData) |

---

## O que o projeto **não** faz (por decisão)

- **Não gera arquivo de remessa CNAB.** Só valida e corrige valores fixos; o RM já gera a remessa.
- **Não usa IA** em nenhuma ferramenta (ver Princípios).
- **O servidor não chama o RM do cliente.** Quem chama é o conector, na máquina do analista.
- **Não guarda senha** do RM em lugar nenhum (nem no navegador, nem no conector, nem no banco).
