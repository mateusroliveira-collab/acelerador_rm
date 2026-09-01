# Ferramentas RM — Acelerador de Implantação TOTVS RM

Conjunto de ferramentas internas para analistas do TOTVS RM (Backoffice —
Compras, Estoque, Faturamento, Financeiro), pensadas pra acelerar tarefas
manuais, repetitivas e propensas a erro humano durante implantação e
parametrização de clientes.

**No ar em:** `https://acelerador-rm.vercel.app`

---

## Por que esse projeto existe

Analistas de implantação do RM gastam uma parte relevante do tempo em
tarefas que são, no fundo, mecânicas — mas que hoje são feitas na mão:

- Procurar um XML de referência parecido com o que o cliente precisa, e
  depois limpar à mão todo campo que "amarra" aquele XML no ambiente
  original (coligada, filial, fórmula, série de numeração...).
- Ler um arquivo CNAB de banco linha por linha pra achar o campo que
  está causando rejeição.
- Ler um documento de levantamento (MIT 41) de dezenas de páginas pra
  extrair a lista de processos e decidir onde cada um se encaixa no RM.

Nenhuma dessas tarefas precisa de inteligência artificial pra ser bem
feita — precisa de **regra determinística, testada contra caso real, e
honesta sobre o que não sabe resolver sozinha**. É essa a filosofia do
projeto: sempre que possível, regra pura (regex, posição de campo,
algoritmo público) em vez de IA. Quando algo genuinamente exige
interpretação de linguagem, isso fica marcado explicitamente como
"precisa de IA" — a ferramenta nunca finge ter resolvido uma parte que
não resolveu.

---

## As quatro ferramentas

### 1. Buscador de XML (`/buscador-xml`)

Busca um arquivo XML de referência dentro da base do projeto, agrupado
por tipo de movimento (Cobrança, Pagamento, Estoque, etc.), e devolve
uma versão **higienizada** — com todo campo que amarra o XML num
ambiente específico (coligada, filial, fórmula, convênio, série de
numeração...) zerado, pronto pra reparametrizar num cliente novo.

- **Ponte com o MIT 41**: cola a saída já interpretada de um documento
  MIT 41 (ver ferramenta 3) e a tela sugere automaticamente o grupo de
  XML certo pra cada movimento, por pontuação de palavra-chave.
- **Upload avulso**: sobe qualquer XML seu (de outro projeto) só pra
  higienizar e baixar na hora — nada fica salvo.
- **Contribuir pra base**: sobe um XML de referência bom, que fica
  salvo (no banco, não em arquivo — ver seção de arquitetura) e passa a
  aparecer na busca pra qualquer pessoa depois.

### 2. Validador de CNAB (`/validador-cnab`)

Valida arquivo de remessa/retorno bancário (CNAB 240 e 400), campo a
campo, apontando **linha, posição exata e uma sugestão de onde
corrigir no RM** — não só "está errado", mas onde mexer.

- Estrutura de CNAB 240 (Header/Trailer, Segmentos A/B/P/Q/R) é
  **universal, padrão FEBRABAN** — vale pra qualquer banco.
- Camada específica por banco (código de erro, particularidade de
  layout) é construída sob demanda, banco por banco, sempre a partir do
  **manual oficial** — nunca por suposição.
- Corretor automático (`corrigir-240`) só mexe em valor **fixo/constante**
  (tipo de registro, por exemplo) — nunca em dado de negócio.

### 3. Pré-processador de MIT 41 (`/pre-processador-mit41`)

Recebe o PDF **bruto** de um documento de levantamento MIT 41 (antes de
qualquer IA) e organiza os subprocessos numa tabela — via regra pura,
sem inteligência artificial:

- Extrai a tabela-índice de subprocessos usando a **geometria real do
  PDF** (não o texto linear, que embaralha quando uma célula quebra em
  várias linhas).
- Mostra AS IS / TO BE / GAP de cada subprocesso.
- Já calcula uma sugestão aproximada de grupo de XML (nome + palavra-chave),
  mais fraca que a Ponte completa, mas útil como ponto de partida.
- Deixa **explícito** onde a classificação de negócio (efeito em
  estoque, financeiro, fiscal) exigiria interpretação de linguagem de
  verdade — isso não é fingido, é marcado como pendente.

### 4. Validador de Registro Online

Valida os dados de um boleto antes do envio pra API de registro online
do banco — sem depender de nenhuma documentação específica de banco,
porque as regras aqui são **universais**:

- CPF/CNPJ: algoritmo oficial de dígito verificador (Receita Federal).
- Datas (vencimento não pode ser antes da emissão), valores (desconto
  não pode ser maior que o título).
- Limite legal de multa de 2% — isso é **lei** (Código de Defesa do
  Consumidor, art. 52 §1º), não regra de banco.
- Completude de endereço, exigida pra registro na CIP.

---

## Arquitetura

| Peça | Escolha |
|---|---|
| Frontend | Next.js (App Router), Tailwind |
| Backend | FastAPI (Python), empacotado como **uma função só** na Vercel |
| Banco de dados | Neon (Postgres serverless) |
| Hospedagem | Vercel (free tier) |

### Por que "uma função só" importa

A Vercel empacota o backend Python inteiro como uma única função
serverless. Isso tem uma consequência importante: **se qualquer arquivo
do backend falhar ao importar, a API inteira cai** — Buscador de XML,
Validador de CNAB e Pré-processador de MIT 41 juntos, mesmo que o
problema seja em um só desses módulos. Por isso todo `import` novo
precisa ser testado antes de subir.

### Por que existe um banco de dados

A Vercel roda em ambiente **sem sistema de arquivos persistente** —
qualquer coisa que o backend escrever em disco durante uma requisição
desaparece depois (não sobrevive nem até a próxima chamada). Por isso:

- **Log de uso** das 4 ferramentas fica no Postgres (Neon), não em
  arquivo de log.
- **XMLs "contribuídos" pela tela do Buscador** ficam salvos no banco
  (tabela `xml_personalizado`), não como arquivo `.xml` na pasta —  
  só assim eles sobrevivem a um novo deploy.
- A base **oficial** de XMLs (a que vem versionada no repositório, em
  `data/xml_base/`) continua sendo arquivo — só muda via commit no Git.

---

## Rodando local

```powershell
# Backend
cd Desktop\Projeto-rm-tools
.venv\Scripts\activate
uvicorn api.index:app --host 127.0.0.1 --port 8000
# (sem --reload -- trava em algumas máquinas Windows)

# Frontend (outro terminal, com o backend já rodando)
npm run dev
```

- Backend sozinho: `http://localhost:8000/docs` (tela automática do
  FastAPI, testa qualquer rota sem precisar do frontend).
- Site completo: `http://localhost:3000`.

Sem `DATABASE_URL` configurada, o backend local cai automaticamente
pra um SQLite (`dev.db`, criado sozinho) — serve pra testar, só não é
o mesmo banco de produção.

## Variáveis de ambiente (produção, configuradas na Vercel)

| Variável | Pra quê |
|---|---|
| `DATABASE_URL` | Connection string do Postgres (Neon) |

---

## Estrutura de pastas (resumo)

```
api/
├── index.py                  # entrypoint único da API
└── _lib/
    ├── db.py                 # conexão com banco (detecta URL sozinho)
    ├── models.py             # tabelas: RegistroUso, XmlPersonalizado
    ├── registro_uso.py       # log de uso -- nunca derruba a ferramenta principal
    ├── xml_cleaner.py        # motor de higienização de XML
    ├── config.py             # labels e pastas dos 6 grupos de XML
    ├── mit41/                # parser, matcher e pré-processador de MIT 41
    ├── cnab/                 # validador/corretor CNAB 240+400, por banco
    ├── registro_online_boleto/  # validação universal de boleto
    └── routers/              # rotas HTTP de cada ferramenta

app/
├── buscador-xml/
├── validador-cnab/
├── pre-processador-mit41/
└── components/

data/
└── xml_base/                 # XMLs de referência oficiais (versionados)
```

---

## Pegadinhas de ambiente já conhecidas

- **`uvicorn --reload` trava** nessa configuração de máquina — sempre
  rodar sem essa flag.
- **URL de preview da Vercel é foto congelada** — cada deploy tem uma
  URL própria que nunca atualiza depois. Sempre testar em
  `acelerador-rm.vercel.app`.
- **Nome de arquivo duplicado (`arquivo.py.py`)** já causou queda total
  do site uma vez — o Python não reconhece isso como módulo válido.
  Depois de mover/renomear arquivo, sempre conferir o nome final.
- Erro em produção costuma ser genérico
  (`FUNCTION_INVOCATION_FAILED`). O diagnóstico real fica nos **Build
  Logs** (erro de instalar dependência) ou **Runtime Logs** (traceback
  Python) do painel da Vercel.

---

## O que este projeto **não** faz (por decisão, não por limitação)

- **Não gera arquivo de remessa CNAB.** Só valida e (parcialmente)
  corrige. O RM já gera remessa — duplicar essa função seria risco
  financeiro desproporcional ao ganho.
- **Não usa IA em produção**, em nenhuma das quatro ferramentas. Toda
  lógica é regra determinística, testável e auditável. Onde a tarefa
  genuinamente precisa de interpretação de linguagem (parte da análise
  do MIT 41), isso fica marcado como pendente — nunca é simulado.
