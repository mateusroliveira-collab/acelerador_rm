# Histórico, decisões e pendências

O que foi construído no Acelerador RM, em que ordem, que decisões foram tomadas (e por quê) e o
que ainda falta validar. Atualizado em 19/11/2026. Os hashes entre parênteses são commits do Git
(`git show <hash>` mostra o detalhe).

## 1. Linha do tempo

### Fase 1 — Fundação (25/08 a 01/09/2026)
- **Buscador de XML** com higienização (zera coligada, filial, fórmulas, séries, códigos de tabela)
  e base de XMLs por grupo de movimento (`4dae96f`, `91b1de7`, `f4073cb`).
- **CNAB 240** estrutural (FEBRABAN) com segmentos A, B, P, Q, R e corretor de valores fixos
  (`d501494`, `73bf58f`); depois segmentos J, J52, N, O, W, Z (FGTS e tributos) e E, T, U
  (`de1a533`, `b649da0`).
- **Banco do Brasil**: tabelas de ocorrências do CNAB 240 (cobrança e pagamentos, 150 códigos) e
  CNAB 400 (`980a663`, `c136a33`, `1438b0c`).
- **Ponte MIT 41**: sugestão de grupo a partir da saída do interpretador (`4dcf68b`).
- **Pré-processador de MIT 41**: subprocessos do PDF, depois com extração pela geometria das
  tabelas, que resolveu o embaralhamento do índice (`fb47a09`, `5c029ce`).
- **Banco Neon** + log de uso + XMLs contribuídos salvos no banco (`07a601e`, `a69531a`, `7684825`).
- **Registro online**: regras universais de boleto; Caixa via XML real do SIGCB (`3951625`, `4277cf9`).
- Incidentes de produção que viraram regra de trabalho: `__init__.py` apagados (`e4de039`) e arquivo
  `bb.py.py` (`6f74eb1`) derrubaram a API inteira → conferir nomes e imports + smoke test.

### Fase 2 — Revisão geral (04/11/2026)
- Criação do **smoke test** e correção dos defeitos achados na revisão (`118edda`, `c9b1f9c`).
- Queda em produção por driver do Postgres → `psycopg2` explícito (`b150f14`).

### Fase 3 — Melhorias e Gerador de DataServer (18 e 19/11/2026)
| Entrega | Commit |
|---|---|
| Pesquisa global por código e descrição no Buscador | `fd3d29b` |
| Exclusão reversível de XML contribuído (com log) | `ec3169b` |
| Desempenho: cache de `/grupos`, log em segundo plano, startup leve, pool do Neon | `9395d23` |
| Matcher da MIT 41: sinônimos com peso, plural, busca aproximada, piso de confiança, testes com MIT real | `339a10e` |
| **Gerador de DataServer** (`GlbUsuarioData`) a partir do JSON real e da tela do RM | `3fb6d90` |
| Modo lote (colar planilha/CSV, até 500 linhas, JSONL + script PowerShell) | `39f31c8` |
| Preparação para escala: API `/api/v1`, segurança opcional, configuração por cliente, versão de schema | `8728a8b` |
| Planilha-modelo: Apps Script (removido) → link de cópia → **modelo Excel gerado pelo site** e página pública | `9cabeb8`, `88155d6`, `d89c4ce`, `a63b818` |
| Validação de `.xlsx` com planilha marcada e saída XML | `a63b818` |

### Fase 4 — MIT 41 + biblioteca e CRUD no RM (19/11/2026)
| Entrega | Commit |
|---|---|
| **Regra de negócio de cada XML** no Buscador (índice pré-calculado) | `af717aa` |
| Leitura do que a MIT pede por movimento, com a frase que justifica | `e0a63d2` |
| Cruzamento MIT x biblioteca: pronto / ajustar / criar + ficha | `d9ae7b8` |
| Tela **Análise da MIT 41** com exportação CSV/Markdown | `8e931ea` |
| **Conector local** para GET/POST/PUT/DELETE no RM | `31c5f56` |
| Tela **Conector RM** (Postman simplificado) | `b23be4a` |
| Envio do lote do Gerador direto ao RM pelo conector | `ce59855` |

### Fase 5 — Formato do GET, Postman facilitado e Hub MIT 41 (25/11/2026)
| Entrega | Commit |
|---|---|
| Planilha e JSON do cadastro de usuário no **formato do GET** (nomes técnicos, ordem do RM, 1/0 e T/F, envelope `messages/length/data`) | `44a9f86` |
| Gerador renomeado para **Cadastro da GUSUARIO**, com envio ao RM pelo Postman facilitado | `7575f2f` |
| Conector 1.1: **várias bases** com nome, chave composta `$_$`, "se já existir: pular/alterar" | `7575f2f` |
| Tela **Evento Contábil Automático** (substitui o Conector RM): puxar, anexar JSON, trocar coligada, enviar | `7575f2f` |
| **Hub MIT 41**: Interpretador + Análise numa tela, PDF lido uma vez | `7575f2f` |
| Conector 1.2: abre com dois cliques (pergunta e guarda a configuração), atalho `.bat`, código de pareamento fixo e copiado | `8a226fc` |
| Conector 1.3: aceita os deploys da Vercel (`acelerador-*-equipe`), `/ping` e diagnóstico na tela | `b09db7c` |
| Conector 1.3.1/1.4: endereço do site sem o caminho da página; `.bat` abre o conector mais novo da pasta; **detecta o RM instalado** (porta e alias) e sugere as bases | (este commit: ver git log) |

## 2. Decisões

| Data | Decisão | Por quê | Alternativa descartada |
|---|---|---|---|
| ago/2026 | Regra determinística, sem IA em produção | Resultado auditável, sem custo, sem enviar dado de cliente para fora | IA para interpretar a MIT |
| ago/2026 | Backend como uma função FastAPI na Vercel + Neon | Free tier, deploy simples; banco porque a Vercel não tem disco persistente | Servidor próprio / on-premise |
| ago/2026 | Não gerar remessa CNAB, só validar e corrigir valores fixos | O RM já gera; risco financeiro alto | Gerador de remessa |
| 18/11 | Gerador de DataServer **não** conecta no RM e **não** guarda credencial | Segurança e compliance do cliente | Servidor chamando o RM |
| 19/11 | Planilha-modelo gerada pelo site em Excel; Google Sheets só opcional | Sempre igual ao que o validador espera, sem depender de conta Google | Apps Script (difícil de manter) |
| 19/11 | Análise MIT x XML **sem IA**, por regras com evidência | Mantém o princípio do projeto; cada conclusão mostra a frase da MIT | IA opcional por chave de API |
| 19/11 | CRUD no RM por **conector local**, em **Python** | A Vercel não enxerga o RM do cliente; senha não passa pelo servidor; Python é testável | Navegador chamando o RM (CORS/HTTPS) ou servidor chamando o RM |
| 19/11 | Conector aceita HTTP e HTTPS; autoassinado só com opção explícita | Cada cliente tem um cenário | Aceitar qualquer certificado por padrão |
| 19/11 | Índice de regras dos XMLs pré-calculado (`data/regras_xml.json`) | Ler 35 MB por requisição custaria ~1 s de cold start | Ler os XMLs a cada chamada |
| 19/11 | No cruzamento, o conteúdo da MIT vence o nome quando 2+ dimensões essenciais são conhecidas | "Compra de Material" que escritura e gera contas a pagar é 1.2, não 1.1 | Grupo só pelo nome |
| 19/11 | Frente CNAB adiada | Precisa de arquivos reais de BB e Caixa para testar | Evoluir sem amostras |
| 25/11 | JSON de saída no formato do GET, mas o **envio** leva um registro por chamada, sem `id`, sem `null`, sem credenciais | POST com o envelope do GET deu erro 0007 (restrição); num PUT, `null` apaga o valor no RM | Enviar o JSON do GET como está |
| 25/11 | Antes de um POST, consultar a chave e pular (padrão) ou alterar o que já existe | Evita o 0007 de "já existe" (ex.: `mestre`) | Deixar o RM recusar |
| 25/11 | Várias bases num conector só, por nome (`--rm nome=endereço`) | Puxar de uma base e enviar para outra sem trocar de conector; continua sem ser proxy aberto | Um conector por base |
| 25/11 | Código de pareamento guardado ao lado do conector (não muda a cada abertura) | Analistas não conseguiam ler o código (janela fechava); a proteção principal continua sendo a origem do site + só 127.0.0.1 | Código novo a cada abertura |
| 25/11 | Nome do DataServer de eventos contábeis editável e lembrado no navegador | Não estava confirmado; a tela serve para qualquer DataServer | Fixar um nome deduzido |

## 3. Pendências

### Precisa de validação em ambiente real (homologação)
- **REST do RM**: formato das URLs (`/rmsrestdataserver/rest/<DataServer>/<chave>`), chave composta,
  filtro (`filter=`), comportamento do PUT e autenticação Basic. Deduzidos do JSON de exemplo; o
  caminho é editável na tela.
- **Eventos contábeis**: nome do DataServer, se o POST aceita as tabelas filhas (`TITMEVCDB`/`TITMEVCCR`)
  no mesmo corpo e o comportamento do GET por chave inexistente (usado no "se já existir").
- **GlbUsuarioData**: formato de `OBRIGAALTERARSENHA` (1/0) e `DIASEXPSENHA` (inteiro), tamanhos
  máximos dos campos, aba "Segurança" da tela do RM (não coberta).
- **Saída XML do Gerador**: formato inferido do padrão DataSet do RM.
- **Modelo Excel**: abrir no Excel real e conferir listas entre abas, recusa de data inválida e
  proteção do cabeçalho.
- **Teste de lote**: `docs/exemplos/cadastro_usuarios_ficticio.xlsx` deve dar 27 válidos e 3 com erro.

### Significados deduzidos (conferir com documentação TOTVS)
- Nomes das classificações de tipo de movimento (`04.04.xx`, `04.06.xx`, `04.08.xx`, `04.09`).
- Fases do orçamento (`T` solicitação, `M` pedido, `A` realizado; `D` estorna).
- Saldos além do Saldo 2 (ex.: A3 em pedidos, A10 em requisições).
- Nome das abas em "Onde mexer" (a propriedade do XML é exata).

### Biblioteca de XMLs (conferir)
- "Entrada por Transferência" (`3.1.03`) está com efeito **diminui** no estoque.
- "Baixa de Material do Estoque" e "Requisição de Material" estão no grupo **1.1** (esperado 4.1).
- Grupos esperados dos casos em `tests/casos_mit41/casos.py` são classificação do analista
  (ex.: Devolução de Compra → 2.2): revisar.

### Evoluções planejadas
- **CNAB BB e Caixa** (adiada): auditar cobertura de todos os contextos (240/400, remessa/retorno,
  registro online), criar testes com arquivos reais anonimizados e padronizar "onde está o erro +
  como corrigir", preparando a entrada de outros bancos.
- **Calibrar a leitura da MIT** com o texto TO BE de MITs reais (anonimizadas).
- **Novos módulos do Gerador**: Educacional (plano feito, não implementado), Tipos de Documento.
  Eventos contábeis já têm o Postman facilitado (sem planilha).
- **Segurança**: login (ou proteção da Vercel) antes de abrir o site para fora do time — hoje
  `/api/log/*`, envio e exclusão de XML contribuído são públicos.
- Limpeza: `estrutura.txt` é uma listagem antiga de arquivos de outra máquina, sem uso.
