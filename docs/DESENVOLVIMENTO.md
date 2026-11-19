# Desenvolvimento

Como preparar o ambiente, testar, commitar e estender cada ferramenta. A visão das peças está em
[ARQUITETURA.md](ARQUITETURA.md).

## 1. Ambiente

Requisitos: Python 3.12 (versão usada no desenvolvimento; confira a do runtime nas configurações
do projeto na Vercel), Node 20+, Git. Windows é o ambiente principal do time.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
npm install
```

Rodar:

```powershell
uvicorn api.index:app --host 127.0.0.1 --port 8000   # NUNCA com --reload (trava nesta configuração)
npm run dev                                          # outro terminal; site em http://localhost:3000
```

Sem `DATABASE_URL`, o backend usa SQLite (`dev.db`). Para apontar para o Neon numa sessão, defina a
variável só no terminal (`$env:DATABASE_URL = "..."`) — nunca em arquivo versionado.

## 2. Verificações

| Comando | Quando | O que garante |
|---|---|---|
| `python scripts/smoke_test.py` | **Antes de todo commit** (obrigatório) | A API importa e as rotas principais respondem (um import quebrado derruba a função única na Vercel) |
| `python -m pytest -q tests` | Antes de todo commit | ~190 testes: regras de XML, requisitos e análise da MIT, matcher, DataServer, Excel, conector, segurança |
| `npx tsc --noEmit` | Ao mexer no frontend | Tipos do Next/React |
| `npm run build` | Antes de mudanças grandes no frontend | Build de produção (localmente falha só pelo certificado corporativo ao baixar Google Fonts; na Vercel funciona) |

Os testes usam banco SQLite temporário e nunca tocam o `dev.db` nem o Neon. Os testes do conector
sobem um RM falso local: nada sai da máquina.

## 3. Regras de trabalho do time

1. **Uma tarefa por vez, commits pequenos**, mensagem em português dizendo o que muda e por quê.
2. **Smoke test antes de cada commit.** Se falhar, não commita.
3. **Mostre o diff e espere aprovação** antes de commitar.
4. **O push é sempre manual** (quem é dono da tarefa decide quando enviar).
5. **Sem IA em produção, sem chave/token de terceiros, lógica determinística.**
6. **Nunca commitar credenciais.** Confira `git status` antes de cada commit.
7. **Depois de criar, mover ou renomear arquivo Python**, confira nome (`bb.py.py` já derrubou a
   produção), `__init__.py` do pacote e os imports — e rode o smoke test.
8. **Toda regra nova ou ajustada ganha um teste** com o caso real que motivou a mudança.

## 4. Como estender

### Adicionar/trocar XML na biblioteca
1. Coloque o `.xml` na pasta do grupo em `data/xml_base/Movimentos do tipo X.Y/`.
2. Regere o índice de regras: `python scripts/gerar_indice_regras_xml.py`.
3. `pytest` (o teste `test_indice_em_dia_com_a_biblioteca` falha se esquecer o passo 2).
4. XML que não deve ser usado: inclua "NÃO UTILIZAR" ou "CONCLUIR" no nome — a análise da MIT ignora.

### Ajustar a leitura da MIT (requisitos)
- Expressões de negócio: `REGRAS` em `api/_lib/mit41/requisitos.py`. Cada dimensão tem regras de
  **negação** (vencem na mesma frase) e **positivas** (em ordem de especificidade; a primeira vale,
  exceto estoque, onde entrada + saída na mesma frase = transferência).
- O texto é normalizado (minúsculas, sem acento, só letras/dígitos/hífen) antes das regras.
- Acrescente o caso em `tests/test_requisitos_mit41.py`.

### Ajustar o cruzamento MIT x XML
Constantes no topo de `api/_lib/mit41/analise.py`:

| Constante | Valor | Efeito |
|---|---|---|
| `PESOS` | estoque/financeiro 3, escrituração/NF-e/NFS-e 2, demais 1 | Peso de cada dimensão; divergência custa peso + 1 |
| `PESO_NOME` | 8 | Multiplica a semelhança de nome (0 a 1) |
| `BONUS_GRUPO` | 3 | XML no grupo provável |
| `NOME_FORTE` | 0,5 | Metade das palavras do título no nome do XML |
| `MAX_DIVERGENCIAS_AJUSTAR` | 2 | Acima disso o status vira "criar" |
| `ESSENCIAIS` | estoque, financeiro, escrituração | Viram pendência se a MIT não disser; 2+ conhecidas fazem o conteúdo vencer o nome no grupo |
| `PARAMETROS` | — | "Onde mexer" de cada dimensão (área + propriedade do XML) |

Casos reais anonimizados para conferir: `tests/casos_mit41/casos.py` (o grupo esperado é
classificação do analista — revise se discordar).

### Ajustar a sugestão de grupo (matcher)
Termos e pesos em `api/_lib/mit41/sinonimos.py` (`CONCEITOS`); piso de confiança e bônus do nome em
`matcher.py`. Testes em `tests/test_matcher_mit41.py`.

### Novo significado de parâmetro do XML
`api/_lib/regras_xml.py`: `regra_de_propriedades()` lê as propriedades (`Formulario.Propriedade`,
sem o prefixo `MovTMv` e o sufixo `ParamsForm`). Ao mudar campos de `RegraXml`, suba
`VERSAO_INDICE` e regere o índice. Para descobrir propriedades, compare valores entre os XMLs da
biblioteca (é assim que os significados atuais foram conferidos).

### Novo módulo do Gerador de DataServer
1. Crie `api/_lib/dataserver/<modulo>/` com `__init__.py` exportando `MODULO` e `gerar_payload`
   (modelo: `glb_usuario/`).
2. Defina `Modulo(chave=..., dataserver=..., campos=[Campo(...)], operacoes=..., campo_chave=...,
   versao_schema="1", ...)` com regras, avisos e entrega.
3. Registre em `api/_lib/dataserver/registro.py` (`MODULOS`).
4. Testes no padrão de `tests/test_dataserver.py`; rode o smoke test. A tela, o modelo Excel, o CSV,
   o lote e o envio pelo conector passam a funcionar sozinhos a partir dos campos.
5. Mudou campo de módulo existente? Suba `versao_schema` (planilhas antigas recebem aviso).

### Novo banco no CNAB
Layout em `api/_lib/cnab/cnab240|cnab400/bancos/<banco>.py` (posições do **manual oficial**),
validador `validador_<banco>.py` usando `ErroValidacao` (com `sugestao_rm`) e rota em
`api/_lib/routers/cnab.py`. Inclua na tela `app/validador-cnab/page.tsx`.

### Conector RM
- Só biblioteca padrão do Python (o analista não instala nada). Python 3.9+.
- Mudança de comportamento: suba `VERSAO`; a tela mostra a versão conectada.
- Nunca logar usuário, senha ou corpo (há teste para isso).
- Novos caminhos permitidos: `PREFIXOS_PERMITIDOS` (avalie o risco: o conector não pode virar proxy aberto).

### Cliente com configuração própria
```powershell
$env:DATABASE_URL = "postgresql://...-pooler.../banco?sslmode=require"
python scripts/cliente_config.py definir acme --nome "ACME S.A." --codigos-acesso Acesso01,Acesso02
python scripts/cliente_config.py listar
```

## 5. Scripts

| Script | Para quê |
|---|---|
| `scripts/smoke_test.py` | Verificação obrigatória antes de commit |
| `scripts/gerar_indice_regras_xml.py` | Regera `data/regras_xml.json` |
| `scripts/gerar_planilha_teste.py` | Planilha fictícia de teste (30 usuários, 3 erros) |
| `scripts/cliente_config.py` | listar/mostrar/definir/ativar/desativar cliente |

## 6. Pegadinhas conhecidas

- `uvicorn --reload` trava nesta configuração de máquina.
- URL de *preview* da Vercel é uma foto congelada de um deploy; teste na URL de produção.
- Erro genérico `FUNCTION_INVOCATION_FAILED` em produção: veja *Build Logs* (dependência) e
  *Runtime Logs* (traceback) no painel da Vercel.
- Git avisa "LF will be replaced by CRLF" no Windows: é inofensivo.
- `next build` local falha ao baixar Google Fonts por causa do certificado corporativo; não é erro
  de código.
- Fechar o terminal do `npm run dev` à força pode deixar o processo `node` vivo segurando a
  porta: confira com `Get-NetTCPConnection -LocalPort 3000`.
