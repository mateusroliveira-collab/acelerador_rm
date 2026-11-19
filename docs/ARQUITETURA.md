# Arquitetura

Visão técnica do Acelerador RM: peças, rotas, banco, segurança e fluxos de dados. Para o uso das
telas, veja o [Guia do analista](GUIA_DO_ANALISTA.md); para trabalhar no código, o
[Desenvolvimento](DESENVOLVIMENTO.md).

## 1. Visão geral

```
                        Navegador do analista
            ┌──────────────────────────┬──────────────────────────────┐
            │  Site (Next.js, Vercel)  │  Conector RM (opcional)       │
            │  app/*                   │  python conector_rm.py        │
            └────────────┬─────────────┴──────────────┬───────────────┘
                         │ /api/*                      │ http://127.0.0.1:8765
                         ▼                             ▼
          ┌─────────────────────────────┐     ┌──────────────────────┐
          │ API FastAPI (1 função)      │     │ RM do cliente        │
          │ api/index.py + api/_lib/*   │     │ REST DataServer      │
          └──────────────┬──────────────┘     │ (rede interna / VPN) │
                         │                    └──────────────────────┘
                         ▼
          ┌─────────────────────────────┐
          │ Neon Postgres (ou SQLite)   │
          │ uso, XMLs contribuídos,     │
          │ configuração de clientes    │
          └─────────────────────────────┘
```

- **O servidor nunca fala com o RM.** Quem fala é o conector, na máquina do analista.
- **Arquivos estáticos versionados** (não mudam sem deploy): `data/xml_base/` (biblioteca de XMLs),
  `data/regras_xml.json` (índice de regras), `public/conector/conector_rm.py`.

## 2. Backend: uma função só

A Vercel empacota `api/index.py` e tudo o que ele importa como **uma única função serverless**.
Consequências:

- **Um erro de import em qualquer módulo derruba a API inteira.** Mitigação: `scripts/smoke_test.py`
  importa a API e chama as rotas principais; roda antes de todo commit.
- **Cold start conta.** Por isso: leitura pesada é pré-calculada (índice de regras dos XMLs),
  imports pesados são tardios (`pdfplumber`, `openpyxl` dentro das funções), o log de uso roda em
  segundo plano (`BackgroundTasks`) e o índice da biblioteca é lido uma vez por processo
  (`lru_cache`).
- **Sem disco persistente.** Tudo o que precisa sobreviver vai para o banco.

### Módulos (`api/_lib/`)

| Módulo | Responsabilidade |
|---|---|
| `config.py` | Grupos de movimento (1.1 a 4.1), pastas da biblioteca |
| `xml_cleaner.py` | Higienização de XML (zera campos que amarram ao ambiente de origem) |
| `pesquisa_xml.py` | Pesquisa global por código/descrição (sem acento, com cache) |
| `regras_xml.py` | Lê os parâmetros do XML de tipo de movimento e gera a **regra de negócio** |
| `mit41/pre_processador.py` | Estrutura do PDF da MIT: índice, subprocessos, AS IS/TO BE/GAP |
| `mit41/parser.py` | Lê a saída do interpretador (`[INICIO_MOVIMENTO]`, `CAMPO=valor`) |
| `mit41/sinonimos.py`, `matcher.py` | Sugestão de grupo por termos com peso, plural e busca aproximada |
| `mit41/requisitos.py` | O que a MIT pede por movimento, com a frase que justifica (negação, ambiguidade) |
| `mit41/analise.py` | Cruza requisitos x regras dos XMLs: status, ficha, ajustes, pendências, fluxo |
| `cnab/` | Layouts e validadores CNAB 240/400 (genérico FEBRABAN, BB, Caixa), corretor 240 |
| `registro_online_boleto/` | Regras universais de boleto e XML de registro online da Caixa (SIGCB) |
| `dataserver/` | Gerador de DataServer: base de módulos, lote, Excel, XML, planilha-modelo |
| `seguranca.py` | Chave de API, cliente efetivo e limite por minuto (opcionais) |
| `clientes.py` | Configuração por cliente (tabela `cliente`) |
| `db.py`, `models.py` | Conexão (Neon com pool, SQLite em dev), tabelas e migração automática |
| `registro_uso.py` | Log de uso; falha no log nunca derruba a ferramenta |

## 3. Rotas da API

Todas sob `/api`. A documentação interativa fica em `/docs` (local).

### Buscador de XML e MIT 41 (`/api/xml`)
| Método | Rota | O que faz |
|---|---|---|
| GET | `/grupos` | Grupos de movimento (cache de borda) |
| GET | `/buscar?grupo=&busca=` | XMLs de um grupo (biblioteca + contribuições) |
| GET | `/pesquisar?q=` | Pesquisa global por código/descrição |
| GET | `/regra?grupo=&arquivo=` ou `?id=` | Regra de negócio de um XML |
| POST | `/limpar?grupo=&arquivo=` | Baixa XML da biblioteca higienizado |
| POST | `/limpar-avulso` | Higieniza um XML enviado, sem salvar |
| POST | `/enviar?grupo=` | Contribui um XML (salvo no banco, higienizado) |
| GET | `/baixar-personalizado/{id}` | Baixa contribuição higienizada |
| DELETE | `/personalizado/{id}` | Exclusão reversível de contribuição |
| POST | `/pre-processar-mit41` | PDF da MIT → subprocessos |
| POST | `/sugerir-grupo` | Saída do interpretador → grupo sugerido por movimento |
| POST | `/sugestao-corrigida` | Registra quando o analista escolhe outro grupo |
| POST | `/analisar-mit41` | Análise completa a partir de texto (bruto ou do interpretador) |
| POST | `/analisar-mit41-pdf` | Análise completa a partir do PDF (até 15 MB) |

### CNAB e registro online
| Método | Rota | O que faz |
|---|---|---|
| POST | `/api/cnab/validar-240`, `-240-bb`, `-240-caixa` | CNAB 240 genérico / BB / Caixa |
| POST | `/api/cnab/validar-400`, `-400-bb`, `-400-caixa` | CNAB 400 genérico / BB / Caixa |
| POST | `/api/cnab/corrigir-240` | Corrige só valores fixos do 240 |
| POST | `/api/cnab/traduzir-erro` | Tradução de código de ocorrência |
| POST | `/api/cnab/validar-xml-bb`, `-xml-caixa` | Registro online (API de cobrança) |
| POST | `/api/registro-online/validar-boleto` | Regras universais do boleto |
| POST | `/api/registro-online/validar-caixa-xml` | XML do SIGCB (Caixa) |

### Gerador de DataServer (`/api/v1/dataserver`; alias oculto `/api/dataserver`)
| Método | Rota | O que faz |
|---|---|---|
| GET | `/modulos?cliente=` | Módulos, campos, `campo_chave`, opções do cliente e links da planilha |
| GET | `/{chave}/modelo-xlsx?cliente=` | Modelo Excel |
| GET | `/{chave}/modelo-csv` | Modelo CSV |
| POST | `/{chave}/lote` | Valida texto/CSV colado |
| POST | `/{chave}/lote-xlsx` | Valida planilha .xlsx (devolve planilha marcada se houver erro) |
| POST | `/{chave}/validar`, `/{chave}/gerar` | Um registro (formulário) |

### Outras
| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/health` | Saúde |
| GET | `/api/log/recentes`, `/api/log/resumo` | Log de uso |

## 4. Banco de dados

| Tabela | Conteúdo |
|---|---|
| `registro_uso` | Ferramenta, ação, detalhes (JSON: contagens, termos de busca, nomes de arquivo), sucesso, data |
| `xml_personalizado` | XMLs contribuídos: original, higienizado, campos zerados, `excluido`/`excluido_em` |
| `cliente` | Código, nome, ativo e `config` (JSON por módulo, ex.: `codigos_acesso`) |

- `criar_tabelas()` roda no startup e é **idempotente**: cria tabelas novas e adiciona colunas que
  faltam (uma consulta ao `information_schema` quando o esquema já está em dia).
- Neon: use a URL *pooled* (`-pooler`); o engine usa `pool_size=2` e `pool_pre_ping`.
- A tabela `cliente` não tem rota de escrita: é mantida por `scripts/cliente_config.py`.

## 5. Segurança

### Site e API
- Sem login: o site é de uso interno e as rotas são públicas.
- **Opcional** (desligado por padrão), só no Gerador de DataServer: `API_KEYS` (chave → cliente; com
  chave, o cliente efetivo é o da chave), `API_EXIGIR_CHAVE=1` (quebra a tela web, que não envia
  chave) e `RATE_LIMIT_POR_MINUTO` (aproximado, por instância). Ver
  [CONFIGURACAO_CONSOLES.md](CONFIGURACAO_CONSOLES.md).
- Uploads com limite de tamanho (PDF 15 MB, texto 2 MB, .xlsx 2 MB com verificação de zip-bomb,
  `.xlsm` recusado). Planilhas lidas em modo somente leitura.
- Nada de credencial no código; `.env` e `*.db` no `.gitignore`.

### Conector RM (`public/conector/conector_rm.py`)
| Proteção | Como |
|---|---|
| Só a própria máquina | Escuta em `127.0.0.1` |
| Só a tela autorizada | Código de pareamento aleatório por execução (`X-Conector-Token`, comparação em tempo constante) + CORS restrito a `--origem` + `Access-Control-Allow-Private-Network` |
| Não é proxy aberto | Host fixo (`--rm`); caminhos só em `/rmsrestdataserver/` e `/api/`; recusa `//`, `://`, `..` e `\` |
| Credenciais | Chegam a cada chamada, vão em Basic Auth direto ao RM, nunca gravadas |
| Log | Só método, caminho, status e tempo — sem usuário, senha ou corpo |
| TLS | Verifica certificado; só aceita autoassinado com `--aceitar-certificado-autoassinado` (avisa na janela) |
| Limites | Corpo de entrada 5 MB, resposta 2 MB, lote 500 registros, timeout configurável |

### Pontos de atenção conhecidos
- `/api/log/recentes` e `/api/log/resumo` são públicos (expõem termos de busca e nomes de XML).
- `POST /api/xml/enviar` e `DELETE /api/xml/personalizado/{id}` são públicos (a exclusão é
  reversível e registrada no log).
- Se o site passar a ser acessado por gente de fora do time, priorize um login (ou proteção da
  Vercel) antes de qualquer outra coisa.

## 6. Fluxos de dados

### Análise da MIT 41
```
PDF ─► pdfplumber (texto + tabelas) ─► pre_processador (subprocessos, TO BE/GAP)
     ─► requisitos (frase a frase: estoque, financeiro, fiscal... + evidência)
     ─► matcher (grupo pelo nome) + grupo pelos requisitos (conteúdo vence quando claro)
     ─► analise: compara com regras_xml (índice data/regras_xml.json + contribuições do banco)
     ─► status + ficha (XML-base, ajustes com propriedade do XML, pendências, fluxo)
```
Nada é gravado, exceto o log de uso (contagens).

### Cadastro em lote (GlbUsuarioData)
```
modelo .xlsx (gerado pelo site) ─► cliente preenche ─► /lote-xlsx (valida; planilha marcada)
   ─► registros válidos (JSON) ─► navegador ─► conector local ─► RM (POST/PUT, 1 por chamada)
                               └► ou JSONL + script PowerShell (Get-Credential)
```
O servidor recebe a planilha, devolve o resultado e descarta. A senha só existe no navegador
(memória) e no conector (durante a chamada).

## 7. Frontend

| Rota | Arquivo |
|---|---|
| `/` | `app/page.tsx` (cards das ferramentas) |
| `/pre-processador-mit41` | `app/pre-processador-mit41/page.tsx` |
| `/buscador-xml` | `app/buscador-xml/page.tsx` |
| `/validador-cnab` | `app/validador-cnab/page.tsx` |
| `/gerador-dataserver` | `app/gerador-dataserver/page.tsx` + `EnviarAoRm.tsx` |
| `/planilha-modelo` | `app/planilha-modelo/page.tsx` (pública, para o cliente) |
| `/analise-mit41` | `app/analise-mit41/page.tsx` |
| `/conector-rm` | `app/conector-rm/page.tsx` |

Utilitários: `app/lib/download.ts` (download de blob), `app/lib/conector.ts` (porta e código de
pareamento na sessão da aba — nunca a senha). Em desenvolvimento, `next.config.mjs` redireciona
`/api/*` para o uvicorn na porta 8000.
