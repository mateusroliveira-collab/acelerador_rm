# Planilha-modelo: Cadastro de Usuário (GlbUsuarioData)

O **modelo Excel (.xlsx) é gerado pelo próprio site** a partir dos campos do sistema, então nunca fica
diferente do que o validador espera. Não depende de Google nem de link.

- **Baixar o modelo** (analista): Gerador de DataServer > aba **Em lote** > *Baixar modelo Excel (.xlsx)*.
  Com o campo **Cliente** preenchido, a aba "Listas" já vem com os códigos de acesso dele.
- **Página para o cliente:** `/planilha-modelo` (o analista copia o endereço pelo botão
  *Copiar link para o cliente*). Lá o cliente baixa o Excel ou o CSV; se houver uma planilha do Google
  configurada (`PLANILHA_MODELO_GLB_USUARIO`), aparece também *Criar cópia no Google Sheets* (opcional).
- **Validar:** na aba **Em lote**, *Enviar planilha preenchida (.xlsx ou CSV)* (ou colar as linhas).
  Erros voltam por linha e, para `.xlsx`, também a **planilha marcada** (células em vermelho + comentário).
- **Teste com dados fictícios:** `python scripts/gerar_planilha_teste.py` (ou use
  `docs/exemplos/cadastro_usuarios_ficticio.xlsx`): 30 usuários, 27 válidos e 3 com erro (linhas 6, 12 e 20).

Abaixo, a especificação do conteúdo do modelo (a mesma vale para uma planilha do Google, se preferir
montar uma à mão). O modelo segue o **formato do GET** do `GlbUsuarioData`: cabeçalho com os nomes
técnicos dos campos, **na mesma ordem** em que o RM devolve, e valores como o RM grava (1/0, T/F).
Ficam de fora só o `id` (é o próprio `CODUSUARIO`), as credenciais (`SENHA`, `TOTPSECRETKEY`, senhas
de redes sociais, `ULTIMASSENHAS`) e os campos que o RM controla (`DATAULTIMOACESSO`,
`DATAULTIMOACESSOVALIDO`, `CONTROLE`, `DTAEXPSENHA`, `NUMLOGININVALIDO`, `DATALOGININVALIDO`) — no
JSON de saída eles aparecem, com `null`.

## Aba "Dados"
Linha 1 = cabeçalho (congelada e protegida). Linhas 2 a 501 = dados (até 500 usuários).

| Col | Cabeçalho | Obrig. | Validação / formato |
|---|---|---|---|
| A | `CODUSUARIO` | Sim | texto (login; chave do registro) |
| B | `NOME` | | texto |
| C | `CODACESSO` | Sim | lista = `Listas!A2:A200` (recusa valor fora da lista) |
| D | `STATUS` | | lista `1`, `0` (vazio = 1, ativo) |
| E | `DATAINICIO` | Sim | data, formato `dd/MM/yyyy` |
| F | `IGNORARAUTENTICACAOLDAP` | | lista `T`, `F` (vazio = F) |
| G | `DATAEXPIRACAO` | | data, formato `dd/MM/yyyy` (vazio = sempre válido) |
| H | `CODUSUARIOREDE` | | texto |
| I | `DOMINIOREDE` | | texto |
| J | `EMAIL` | | e-mail válido |
| K | `NOMESOCIAL` | | texto |
| L | `CODEXTERNO` | | texto |
| M | `INTEGRADOFLUIG` | | inteiro (vazio = não envia) |
| N | `OIDC_ENABLED` | Sim | lista `1`, `0` (vazio = 0) |
| O | `CONFIRMABTNOK` | | inteiro *(tipo inferido)* |
| P | `ULTIMACOLIGADA` | | inteiro |
| Q | `DIASEXPSENHA` | | inteiro, 0 ou maior |
| R | `OBRIGAALTERARSENHA` | | lista `1`, `0` (vazio = 1) |
| S | `ACESSONET` | | inteiro *(tipo inferido)* |
| T | `LIVEID` | | texto |
| U | `USUARIOTWITTER` | | texto |
| V | `USUARIOFACEBOOK` | | texto |
| W | `USUARIOLINKEDIN` | | texto |
| X | `FULLDETERMINED` | | inteiro *(tipo inferido)* |
| Y | `USERID` | | texto |
| Z | `USERIDFLUIGIDENTITY` | | texto |

Formatação:
- Cabeçalho em negrito, centralizado. Obrigatórios com fundo amarelo (`#FFF2CC`); demais cinza (`#EFEFEF`).
- Colunas de texto com formato **Texto simples** (preserva zeros à esquerda); datas em `dd/MM/yyyy`.
- Em cada título, uma **nota** com o nome do campo na tela do RM, o formato e como preencher.
- Validações rígidas ("Rejeitar entrada") com seta de lista onde houver.
- Linha 1 congelada e protegida.

> Não renomeie os títulos: o reconhecimento depende deles (há um teste automatizado que garante o
> mapeamento). Planilhas antigas, com os rótulos da tela (`Usuário *`, `Ativo`...) e `Sim`/`Não`,
> continuam sendo aceitas.

## Aba "Listas"
| A |
|---|
| `Códigos de acesso` *(título)* |
| `Acesso01` |
| `Acesso02` |
| *(o analista substitui pelos códigos do cliente; até a linha 200)* |

Protegida (só o analista edita). Se ficar com os valores de exemplo, o cliente só conseguirá escolher
`Acesso01`/`Acesso02`: **lembre de preencher antes de compartilhar a cópia.**

## Aba "Instruções"
Texto para o cliente (protegida):

1. Preencha a aba **Dados**, uma linha por usuário. Colunas com fundo amarelo são obrigatórias.
2. O cabeçalho usa os nomes dos campos do RM, na ordem em que o RM devolve os dados.
3. Passe o mouse no título da coluna para ver o que é e como preencher.
4. Sim/não como o RM grava: `1`/`0` (`IGNORARAUTENTICACAOLDAP`: `T`/`F`).
5. Colunas com seta têm uma lista: escolha o valor. Datas: DD/MM/AAAA.
6. **Não informe senha.** Ela não faz parte deste cadastro.
7. Não altere o cabeçalho nem a ordem das colunas.
8. Ao terminar, avise o analista.

Abaixo do texto, a aba traz o **dicionário dos campos** (campo, descrição, obrigatório, formato).

Exemplo de linha (colunas A a G; o resto vazio):
`maria.silva | Maria Silva | Acesso01 | 1 | 01/12/2026 | F | `

## Saída
- **JSON (formato do GET)**: `{"messages": [], "length": N, "data": [ ... ]}`, cada registro com as
  39 chaves do GET na mesma ordem (`id` = `CODUSUARIO`; o que não foi preenchido sai `null`).
- **Envio ao RM** (conector / JSONL): um registro por chamada, só com os campos preenchidos.

## Como usar
### Com o modelo Excel (recomendado)
1. Gerador de DataServer > **Em lote**: preencha **Cliente** (para vir com os códigos de acesso dele)
   e clique **Baixar modelo Excel (.xlsx)**. Sem cliente cadastrado, troque os códigos de exemplo da
   aba **Listas** antes de enviar (Revisão > Desproteger planilha, sem senha).
2. Envie o arquivo ao cliente (ou o link `/planilha-modelo`, botão *Copiar link para o cliente*).
3. Quando o cliente devolver: **Enviar planilha preenchida** e **Validar lote**.
4. Erros: **Baixar planilha marcada** (células em vermelho com comentário + aba "Erros"), devolva ao
   cliente, repita.
5. Tudo válido: **Enviar direto ao RM** pelo conector (comece pelo teste de um registro) ou baixe o
   JSONL e use o script exibido na tela.

### Com uma planilha do Google Sheets (opcional)
1. Botão **Abrir planilha modelo** (aparece se `PLANILHA_MODELO_GLB_USUARIO` estiver configurada) →
   *Fazer uma cópia*, preencha a aba **Listas** e compartilhe a cópia com o cliente como **Editor**.
2. Quando o cliente terminar: aba **Dados**, `Ctrl+A`, `Ctrl+C`; na ferramenta, aba **Em lote**,
   cole e clique **Validar lote**. Daí em diante, igual aos passos 4 e 5 acima.

## Limites
- A proteção e a validação do Google **não são segurança** (o cliente pode colar valores por cima, e o
  dono de uma cópia pode alterar tudo). A ferramenta valida tudo de novo ao receber.
- Até 500 linhas por lote.
- A planilha não leva senha nem dado de ninguém; só o cliente digita dados na **cópia dele**.
