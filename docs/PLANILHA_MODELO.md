# Planilha-modelo: Cadastro de Usuário (GlbUsuarioData)

Especificação da planilha do Google Sheets que o cliente preenche. A ferramenta (aba **Em lote**)
reconhece o cabeçalho pelos **rótulos da tela do RM**, então não é preciso traduzir nada: basta
copiar as linhas da aba **Dados** e colar na ferramenta.

## Aba "Dados"
Linha 1 = cabeçalho (congelada e protegida). Linhas 2 a 501 = dados (até 500 usuários).

| Col | Cabeçalho (exatamente assim) | Obrig. | Validação / formato |
|---|---|---|---|
| A | `Usuário *` | Sim | texto |
| B | `Nome` | | texto |
| C | `Nome Social` | | texto |
| D | `E-Mail` | | e-mail válido |
| E | `Código de Acesso *` | Sim | lista = `Listas!A2:A200` (recusa valor fora da lista) |
| F | `Ativo` | | lista `Sim`, `Não` (vazio = Sim) |
| G | `Login OIDC *` | Sim | lista `Sim`, `Não` (vazio = Não) |
| H | `Alterar senha no próximo login` | | lista `Sim`, `Não` (vazio = Sim) |
| I | `Força a troca de senha a cada (dias)` | | número inteiro, 0 ou maior |
| J | `Início de Validade *` | Sim | data, formato `dd/MM/yyyy` |
| K | `Expiração de Validade` | | data, formato `dd/MM/yyyy` (vazio = sempre válido) |
| L | `Usuário de rede` | | texto |
| M | `Domínio de rede` | | texto |
| N | `Ignorar autenticação LDAP` | | lista `Sim`, `Não` (vazio = Não) |

Formatação:
- Cabeçalho em negrito, centralizado. Obrigatórios (`*`) com fundo amarelo (`#FFF2CC`); demais cinza (`#EFEFEF`).
- Colunas de texto (A, B, C, D, L, M) com formato **Texto simples** (preserva zeros à esquerda).
- Colunas J e K com formato de data `dd/MM/yyyy`.
- Em cada título, uma **nota** com o que é o campo e como preencher.
- Validações rígidas ("Rejeitar entrada") com seta de lista onde houver.
- Linha 1 congelada. **Proteger intervalo** A1:N1 (só o dono edita).

> O `*` no cabeçalho é ignorado pela ferramenta. Não renomeie os títulos: o reconhecimento
> depende deles (há um teste automatizado que garante o mapeamento).

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

1. Preencha a aba **Dados**, uma linha por usuário. Colunas com `*` e fundo amarelo são obrigatórias.
2. Passe o mouse no título da coluna para ver como preencher.
3. Colunas com seta têm uma lista: escolha o valor. Datas: DD/MM/AAAA.
4. **Não informe senha.** Ela não faz parte deste cadastro.
5. Não altere o cabeçalho nem a ordem das colunas.
6. Ao terminar, avise o analista.

Exemplo de linha (fica **só nesta aba**, nunca na aba Dados):
`maria.silva | Maria Silva | | maria.silva@empresa.com | Acesso01 | Sim | Não | Sim | | 01/12/2026 | | | | Não`

## Como usar
1. Botão **Abrir planilha modelo** (Gerador de DataServer) → *Fazer uma cópia*.
2. Preencha a aba **Listas** com os códigos de acesso do cliente.
3. Compartilhe a cópia com o cliente como **Editor** (assim o cabeçalho e as abas protegidas ficam travados para ele).
4. Quando o cliente terminar: abra a cópia, aba **Dados**, `Ctrl+A`, `Ctrl+C`; na ferramenta, aba
   **Em lote**, cole e clique **Validar lote**.
5. Erros: **Copiar relatório de erros** (ou baixar o CSV), devolva ao cliente, repita.
6. Tudo válido: baixe o JSONL e siga as instruções de envio ao RM exibidas na tela.

## Limites
- A proteção e a validação do Google **não são segurança** (o cliente pode colar valores por cima, e o
  dono de uma cópia pode alterar tudo). A ferramenta valida tudo de novo ao receber.
- Até 500 linhas por lote.
- A planilha não leva senha nem dado de ninguém; só o cliente digita dados na **cópia dele**.
