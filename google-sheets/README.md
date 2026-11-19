# Planilha do Acelerador RM no Google Sheets

Planilha-modelo com menu **Acelerador RM** que monta o modelo travado, valida os dados na API
e gera o arquivo para o RM. O cliente só preenche; o analista valida, corrige e gera.

## Arquivos
- `Codigo.gs` — o script (menu, montar modelo, validar, gerar arquivo). Contém o marcador
  `__API_BASE__`, substituído quando o script é baixado pela tela **Gerador de DataServer**
  (rota `GET /api/v1/dataserver/google-sheets/script?base=https://SEU-APP`).
- `appsscript.json` — manifesto com as permissões mínimas.

## Instalação (uma vez)
Veja `docs/CONFIGURACAO_CONSOLES.md`, seção 4. Depois: **Acelerador RM > 1. Configurar**
(cliente, operação e chave de API, se houver) e **2. Montar modelo**.

## Fluxo de uso
1. **Analista**: monta o modelo uma vez e usa **Arquivo > Fazer uma cópia** para cada cliente
   (a cópia leva o script junto; a chave de API **não** vai, ela fica na conta do analista).
2. **Cliente**: preenche a aba **Dados** (colunas amarelas são obrigatórias). Não altera o cabeçalho.
3. **Analista**: **3. Validar dados** — células com erro ficam vermelhas, com o motivo na nota.
   Corrige (ou devolve ao cliente) e valida de novo.
4. **Analista**: **4. Gerar arquivo para o RM** — baixa o JSONL e envia ao RM seguindo as instruções
   da tela do Gerador (script PowerShell com `Get-Credential`; nada de senha no arquivo).

## Limites e cuidados
- A proteção do cabeçalho e a validação de células **não são segurança**: o cliente consegue colar valores
  por cima. A API valida tudo de novo.
- Até **500 linhas** por lote (limite da API).
- Ao validar, as linhas vão à API (Vercel) e são processadas em memória, sem gravação.
  Confirme que isso é aceitável para o cliente (LGPD).
- Se a API mudar o schema (campo novo/alterado), a versão sobe e a planilha avisa
  "modelo desatualizado": use **Montar modelo** de novo (copie os dados antes).

## Roteiro de teste (o script não foi executado dentro do Google ainda — faça uma vez)
Use uma planilha de teste e um cliente fictício.
1. Menu **Acelerador RM** aparece após recarregar? ☐
2. **Configurar**: aceita cliente/operação sem erro? ☐
3. **Montar modelo**: cria a aba **Dados** com cabeçalho em negrito, obrigatórios em amarelo e as
   colunas Sim/Não com seta de lista? ☐ Datas aceitam só DD/MM/AAAA? ☐ E-mail inválido é recusado? ☐
4. Tente editar o cabeçalho com outra conta (editor, não dono): está bloqueado? ☐
5. Preencha 2 linhas válidas: **Validar** mostra "2 válido(s) de 2"? ☐
6. Erre de propósito (e-mail ruim, código de acesso vazio): células ficam vermelhas e a nota explica? ☐
7. Corrija e valide de novo: as marcas vermelhas somem? ☐
8. **Gerar arquivo**: abre a janela com o JSONL; **Baixar** salva o arquivo (se o navegador bloquear o
   download, use **Copiar**)? ☐
9. Copie a planilha (**Fazer uma cópia**): o modelo, a validação e o menu continuam funcionando, e a
   chave de API **não** foi junto? ☐
10. Se algo falhar: **Extensões > Apps Script > Execuções** mostra o erro detalhado.

Itens que merecem atenção especial por serem comportamentos do Google que não consegui conferir daqui:
o download pelo botão da janela (item 8) e o bloqueio do cabeçalho para editores (item 4).
