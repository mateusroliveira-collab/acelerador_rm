# Guia do analista

Como usar cada tela do Acelerador RM no dia a dia de uma implantação. Nenhuma ferramenta usa IA:
cada resultado mostra de onde veio (trecho da MIT, parâmetro do XML, linha e posição do arquivo).
Quando a ferramenta não tem certeza, ela diz — e a palavra final é sempre sua.

Sumário:
1. [Interpretador de MIT 41](#1-interpretador-de-mit-41)
2. [Buscador de XML](#2-buscador-de-xml)
3. [Validador de CNAB e registro online](#3-validador-de-cnab-e-registro-online)
4. [Gerador de DataServer](#4-gerador-de-dataserver)
5. [Análise da MIT 41](#5-análise-da-mit-41)
6. [Conector RM](#6-conector-rm)
7. [Dúvidas frequentes](#7-dúvidas-frequentes)

---

## 1. Interpretador de MIT 41

**Tela:** `/pre-processador-mit41` · **Entrada:** PDF da MIT 41 (com texto selecionável, não escaneado).

1. Escolha o PDF e clique **Processar**.
2. A tabela lista os subprocessos (ex.: `4.1.1.2 Requisição de Materiais`) com o processo relacionado,
   AS IS, TO BE e GAP, e uma sugestão aproximada de grupo de movimento.
3. **Copiar para a Ponte**: gera o texto no formato `[INICIO_MOVIMENTO]...` que o Buscador de XML lê.

Limites: o índice de subprocessos é lido pela geometria das tabelas do PDF (mais confiável que o
texto corrido). Documento escaneado (imagem) não tem texto e é recusado.

> Para a análise completa (o que cada movimento pede x XMLs da biblioteca), use a
> [Análise da MIT 41](#5-análise-da-mit-41), que já faz este passo por dentro.

---

## 2. Buscador de XML

**Tela:** `/buscador-xml` · **Base:** ~130 XMLs de tipos de movimento em 6 grupos (1.1 a 4.1).

| Grupo | O que é |
|---|---|
| 1.1 | Pedido/solicitação de compra (sem efeito fiscal) |
| 1.2 | Nota fiscal de entrada |
| 2.1 | Pedido de venda / orçamento (sem efeito fiscal) |
| 2.2 | Nota fiscal de saída |
| 3.1 | Transferência entre filiais/locais |
| 4.1 | Movimento interno de estoque |

O que dá para fazer:
- **Pesquisa global** por código (`1.2.01` ou `1201`) ou descrição, sem acento, em todos os grupos.
- **Regra de negócio** (botão em cada XML): o que o movimento faz, lido dos parâmetros do XML.
  Exemplo para uma NF de compra: *Classificação 04.06.05 · Estoque: aumenta · Financeiro: a PAGAR ·
  Escritura nos livros fiscais · CFOP 1.556 / 2.900 · Contabiliza*.
  Inclui orçamento, aprovação, NF-e/NFS-e, geração de contrato e para quais movimentos segue no fluxo.
- **Limpar e baixar**: devolve o XML **higienizado**, com os campos que amarram o XML ao ambiente
  de origem zerados (coligada, filial, fórmulas, séries, códigos de tabela), pronto para importar
  em outro cliente.
- **Ponte MIT 41**: cole a saída do interpretador e veja o grupo sugerido para cada movimento,
  com os sinais que levaram à sugestão. Se escolher outro grupo, a correção é registrada (melhora
  o matcher).
- **Limpar um XML seu** (avulso): higieniza e devolve na hora, sem salvar nada.
- **Contribuir com a base**: envia um XML bom para a biblioteca compartilhada (fica no banco).
  Contribuições podem ser excluídas (exclusão reversível, fica registrada).

Limites da regra de negócio: alguns significados foram **deduzidos** comparando os 132 XMLs da
biblioteca, não lidos de documentação TOTVS — o nome das classificações (ex.: `04.06.01` =
Solicitação de compra), as fases do orçamento (T/M/A) e os saldos além do Saldo 2. Estão marcados
como deduzidos no código.

---

## 3. Validador de CNAB e registro online

**Tela:** `/validador-cnab`.

| Opção | O que valida |
|---|---|
| Genérico CNAB 240 | Estrutura FEBRABAN: header/trailer de arquivo e lote, segmentos (A, B, J, J52, N, O, P, Q, R, T, U, W, Z, E...) |
| Banco do Brasil / Caixa — CNAB 240 | Estrutura + regras do banco + dicas de onde corrigir no RM |
| Genérico CNAB 400 | Tamanho de linha e registros 0/1/9 |
| Banco do Brasil (CBR641/643) / Caixa (SIGCB) — CNAB 400 | Layout do banco; remessa ou retorno detectado sozinho |
| Registro online BB / Caixa | Dados da API de cobrança (Caixa: XML do SIGCB) |

Cada erro traz **linha, posição inicial e final, campo, valor encontrado e sugestão de onde
corrigir no RM**. O corretor do CNAB 240 só corrige valores **fixos** (ex.: tipo de registro) —
nunca dado de negócio (valor, vencimento, documento).

O validador de boleto (registro online) aplica regras universais: dígito de CPF/CNPJ, datas
(vencimento não antes da emissão), desconto não maior que o título e **multa máxima de 2%** (CDC,
art. 52 §1º).

> Próxima evolução planejada (adiada): cobrir todos os contextos de BB e Caixa com testes
> automatizados a partir de arquivos reais e padronizar o "como corrigir". Ver
> [HISTORICO_E_DECISOES.md](HISTORICO_E_DECISOES.md#3-pendências).

---

## 4. Gerador de DataServer

**Tela:** `/gerador-dataserver` · **Módulo disponível:** cadastro de usuário (`GlbUsuarioData`).

### Em lote (principal)
1. Preencha **Cliente** (opcional): com cliente cadastrado, a lista de *Código de Acesso* vem com os
   códigos dele.
2. **Baixar modelo Excel (.xlsx)** e entregue ao cliente — ou use **Copiar link para o cliente**
   (página pública `/planilha-modelo`). O modelo tem listas, validação de data/e-mail e cabeçalho
   protegido. Detalhes: [PLANILHA_MODELO.md](PLANILHA_MODELO.md).
3. Quando o cliente devolver: **Enviar planilha preenchida** (.xlsx ou CSV), ou cole as linhas, e
   clique **Validar lote** (até 500 linhas).
4. Com erros: **Baixar planilha marcada** (células em vermelho com comentário e aba "Erros"), ou
   copie/baixe o relatório, e devolva ao cliente.
5. Com registros válidos, escolha como carregar:
   - **Enviar direto ao RM** (quadro do conector, ver [seção 6](#6-conector-rm)) — recomendado;
   - **JSONL + script PowerShell** (pede usuário/senha com `Get-Credential`);
   - **JSON** (lista) ou **XML** (formato inferido, *a validar em homologação*).

### Formulário (um usuário)
Preencha os campos e clique **Validar e gerar prévia**: sai o JSON pronto para o REST DataServer.

O que o gerador **nunca** faz: gerar senha ou campos controlados pelo RM. Teste de exemplo:
`docs/exemplos/cadastro_usuarios_ficticio.xlsx` (30 usuários fictícios; esperado 27 válidos e 3 com
erro nas linhas 6, 12 e 20).

---

## 5. Análise da MIT 41

**Tela:** `/analise-mit41` · **Entrada:** PDF da MIT 41, texto colado da MIT, ou a saída do
interpretador (`[INICIO_MOVIMENTO]...`).

Para cada movimento a ferramenta:
1. lê o **TO BE** e o **GAP** (o AS IS descreve o processo atual e fica de fora);
2. conclui o que a MIT pede — estoque (aumenta/diminui/transfere/nenhum), financeiro (a pagar/a
   receber/nenhum), escrituração fiscal, natureza da nota, NF-e, NFS-e, orçamento, contabilização,
   aprovação, geração de contrato — guardando **a frase da MIT** que justifica cada conclusão;
3. define o grupo (1.1 a 4.1): pelo nome e, quando a MIT descreve o comportamento com clareza,
   **o conteúdo vence o nome** (uma "Compra de Material" que escritura, dá entrada no estoque e gera
   contas a pagar é 1.2);
4. compara com a **regra de negócio** de cada XML da biblioteca (e das contribuições) e com o nome.

Resultado por movimento:

| Status | Significado | O que fazer |
|---|---|---|
| **Pronto** | Há XML sem divergência e com evidência (nome parecido ou 2+ regras batendo) | Baixe o XML-base higienizado |
| **Ajustar** | Há XML-base, mas 1–2 parâmetros divergem, ou o XML certo está em outro grupo | Siga a tabela de ajustes |
| **Criar** | Nada parecido; a ficha indica o XML mais próximo como base | Siga a ficha e confirme com o cliente |
| **Sem dados** | Não é tipo de movimento (cadastro) ou a MIT não detalha | Verifique na MIT |

A **ficha** de cada movimento traz: grupo, código sugerido (próximo livre na biblioteca — use a
numeração do cliente), XML-base com botão de download higienizado, o que a MIT pede, a tabela de
**ajustes** (MIT pede × XML faz × onde mexer, com a propriedade exata do XML e a frase da MIT), o
que **confirmar com o cliente** (o que a MIT não diz) e o **fluxo** (de qual movimento vem, para
qual segue).

Exporte em **CSV** (abre no Excel) ou **relatório Markdown** para compartilhar.

Cuidados:
- Se a MIT se contradiz ("não gera financeiro" e depois "gera contas a pagar"), o item fica
  **contraditório** e as duas frases aparecem — decida você.
- "Onde mexer" usa a propriedade **exata** do XML; o nome da aba da parametrização foi deduzido.
- A qualidade depende da MIT: quanto mais o TO BE descreve o comportamento, melhor o resultado.

---

## 6. Conector RM

**Tela:** `/conector-rm` · Consulta, inclui, altera e exclui registros no RM pelo **REST
DataServer**, a partir da **sua máquina**.

Por que um conector: o site roda na nuvem e não enxerga o RM do cliente (rede interna/VPN). O
conector é um pequeno programa Python que roda na sua máquina e repassa as chamadas.

### Primeira vez
1. Tenha **Python 3.9+** instalado (nada mais para instalar).
2. Na tela, informe o **endereço do RM** (ex.: `https://rm.cliente.com.br:8051`), a porta local
   (padrão 8765) e marque *certificado próprio* se o RM usar HTTPS autoassinado.
3. **Baixar conector_rm.py** e **Copiar comando**. Rode o comando na pasta do arquivo, por exemplo:
   ```
   python conector_rm.py --rm https://rm.cliente.com.br:8051 --origem https://acelerador-rm.vercel.app
   ```
4. A janela mostra o **código de pareamento** (ex.: `7F3A91C2`). Deixe-a aberta.
5. Na tela, cole o código e clique **Conectar**. Se o navegador pedir permissão para acessar a
   **rede local**, permita.

### Fazendo chamadas
- Informe usuário e senha do RM (ficam só na memória da aba; somem ao recarregar).
- Escolha o método, o DataServer e a chave. O caminho é montado sozinho
  (`/rmsrestdataserver/rest/GlbUsuarioData/<chave>`) e pode ser editado.
- **GET** aceita parâmetros (ex.: `filter=CODUSUARIO = 'maria.silva'`); **POST/PUT** levam corpo JSON;
  **DELETE** pede confirmação.
- A resposta mostra status HTTP, tempo, o JSON e, em caso de erro, **como corrigir**. O histórico da
  sessão guarda as últimas 15 chamadas (sem senha) com **Repetir**.

### Enviar o lote do Gerador de DataServer
No resultado do lote, o quadro **Enviar direto ao RM** usa a mesma conexão. Ele começa com
**"Enviar só o primeiro registro (teste)"** marcado: confira o registro no RM e o próximo clique
envia os demais, sem reenviar o primeiro. O resultado mostra cada registro com o HTTP e a mensagem do RM.

### Erros comuns
| Mensagem | Causa provável | Como corrigir |
|---|---|---|
| Não encontrei o conector | Janela fechada, porta diferente ou permissão de rede local negada | Abra o conector, confira a porta, permita o acesso |
| Origem não autorizada | Conector aberto sem `--origem` igual ao site | Feche e abra com o comando copiado da tela |
| Certificado não confiável | RM com HTTPS autoassinado | Reabra com `--aceitar-certificado-autoassinado` |
| RM recusou a conexão / não encontrei o endereço | Porta errada, serviço parado ou VPN desligada | Confira `--rm`, a VPN e o serviço do RM |
| HTTP 401 / 403 | Senha errada / usuário sem permissão no DataServer | Confira usuário e perfil de acesso no RM |

Segurança: o conector só escuta na própria máquina (`127.0.0.1`), exige o código de pareamento, só
aceita a origem do site, só chama o RM informado e só em `/rmsrestdataserver/` e `/api/`. Senha,
usuário e conteúdo das chamadas **não** aparecem no log da janela.

> **Use homologação primeiro.** O formato exato das URLs do REST do RM (chave na URL, filtros) foi
> deduzido de exemplos e deve ser confirmado na primeira chamada em cada cliente.

---

## 7. Dúvidas frequentes

**A ferramenta usa IA?** Não. São regras; cada conclusão mostra a evidência.

**Meus dados ficam salvos?** O site guarda apenas: log de uso (ferramenta, ação, contagens, termos
pesquisados no Buscador e nomes de XML — sem conteúdo de MIT, de planilha ou senha), XMLs que você contribuir e configuração de clientes (códigos de
acesso). MIT, planilhas e lotes são processados e descartados. Senha do RM nunca passa pelo site.

**Achei um resultado errado.** Anote o caso (trecho da MIT, XML, linha do arquivo) e passe para o
time técnico: cada regra é ajustável e cada correção vira um teste automatizado.
