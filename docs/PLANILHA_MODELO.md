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
montar uma à mão). A ferramenta reconhece o cabeçalho pelos **rótulos da tela do RM**.

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
