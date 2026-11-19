/**
 * Acelerador RM -- Gerador de DataServer dentro do Google Sheets.
 *
 * Como usar: veja google-sheets/README.md. Resumo: este código é colado no
 * Apps Script da planilha-modelo (Extensões > Apps Script). Ele cria o menu
 * "Acelerador RM" com:
 *   - Montar modelo   : monta a aba "Dados" a partir dos campos da API
 *                       (cabeçalho travado, listas, datas e e-mails validados);
 *   - Validar dados   : envia as linhas à API, pinta as células com erro e
 *                       explica o problema em uma nota;
 *   - Gerar arquivo   : abre a janela com o JSONL pronto pro RM.
 *
 * Privacidade: ao validar, as linhas da aba "Dados" (que podem ter dados
 * pessoais) são enviadas à API do Acelerador RM, que processa em memória e
 * não grava nada. A chave de API (se houver) fica só nas propriedades do
 * USUÁRIO que a configurou -- nunca na planilha, então não vai junto
 * quando a planilha é copiada ou compartilhada com o cliente.
 *
 * Este script NÃO envia nada ao RM.
 */

var API_BASE_PADRAO = '__API_BASE__';
var MODULO = 'glb-usuario';
var ABA_DADOS = 'Dados';
var ABA_INSTRUCOES = 'Instruções';
var ABA_CONFIG = '_config';
var MAX_LINHAS = 500;
var COR_ERRO = '#f4c7c3';
var COR_OBRIGATORIO = '#fff2cc';
var COR_CABECALHO = '#efefef';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Acelerador RM')
    .addItem('1. Configurar', 'configurar')
    .addItem('2. Montar modelo', 'montarModelo')
    .addSeparator()
    .addItem('3. Validar dados', 'validar')
    .addItem('4. Gerar arquivo para o RM', 'gerarArquivo')
    .addToUi();
}

/* ------------------------------ configuração ------------------------------ */

// Configuração NÃO secreta fica numa aba oculta (acompanha as cópias da planilha).
function lerConfig_() {
  var aba = SpreadsheetApp.getActive().getSheetByName(ABA_CONFIG);
  var cfg = { API_BASE: API_BASE_PADRAO, CLIENTE: '', OPERACAO: 'incluir', VERSAO_SCHEMA: '' };
  if (aba && aba.getLastRow() > 0) {
    aba.getRange(1, 1, aba.getLastRow(), 2).getValues().forEach(function (l) {
      if (l[0]) cfg[l[0]] = String(l[1]);
    });
  }
  // A chave de API é secreta: só nas propriedades do usuário.
  cfg.API_KEY = PropertiesService.getUserProperties().getProperty('API_KEY') || '';
  return cfg;
}

function salvarConfig_(cfg) {
  var ss = SpreadsheetApp.getActive();
  var aba = ss.getSheetByName(ABA_CONFIG) || ss.insertSheet(ABA_CONFIG);
  var chaves = ['API_BASE', 'CLIENTE', 'OPERACAO', 'VERSAO_SCHEMA'];
  aba.clear();
  aba.getRange(1, 1, chaves.length, 2).setValues(chaves.map(function (k) { return [k, cfg[k] || '']; }));
  aba.hideSheet();
}

function configurar() {
  var ui = SpreadsheetApp.getUi();
  var cfg = lerConfig_();

  var r = ui.prompt('Cliente', 'Código do cliente (opcional -- usado para a lista de códigos de acesso). Atual: ' + (cfg.CLIENTE || '(nenhum)'), ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  if (r.getResponseText().trim() !== '') cfg.CLIENTE = r.getResponseText().trim();

  r = ui.prompt('Operação', 'Digite "incluir" (usuário novo) ou "alterar" (usuário existente). Atual: ' + cfg.OPERACAO, ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  var op = r.getResponseText().trim().toLowerCase();
  if (op === 'incluir' || op === 'alterar') cfg.OPERACAO = op;

  r = ui.prompt('Chave de API', 'Só se a sua instalação exigir (deixe vazio se não). Fica salva apenas na SUA conta.', ui.ButtonSet.OK_CANCEL);
  if (r.getSelectedButton() !== ui.Button.OK) return;
  if (r.getResponseText().trim() !== '') {
    PropertiesService.getUserProperties().setProperty('API_KEY', r.getResponseText().trim());
  }

  salvarConfig_(cfg);
  SpreadsheetApp.getActive().toast('Configuração salva.', 'Acelerador RM', 4);
}

/* --------------------------------- API ----------------------------------- */

function chamarApi_(metodo, caminho, corpo) {
  var cfg = lerConfig_();
  if (!cfg.API_BASE || cfg.API_BASE.indexOf('__API_BASE__') >= 0) {
    throw new Error('Endereço da API não configurado. Baixe o script de novo pela tela do Gerador de DataServer.');
  }
  var opcoes = { method: metodo, muteHttpExceptions: true, headers: {} };
  if (cfg.API_KEY) opcoes.headers['X-API-Key'] = cfg.API_KEY;
  if (corpo) {
    opcoes.contentType = 'application/json';
    opcoes.payload = JSON.stringify(corpo);
  }
  var resp = UrlFetchApp.fetch(cfg.API_BASE + '/api/v1/dataserver' + caminho, opcoes);
  var codigo = resp.getResponseCode();
  var dados = null;
  try { dados = JSON.parse(resp.getContentText()); } catch (e) { /* resposta não-JSON */ }
  if (codigo >= 400) {
    var detalhe = dados && typeof dados.detail === 'string' ? dados.detail : 'HTTP ' + codigo;
    throw new Error(detalhe);
  }
  return dados;
}

/* ------------------------------ montar modelo ------------------------------ */

function montarModelo() {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActive();
  var cfg = lerConfig_();

  var modulo;
  try {
    var caminho = '/modulos' + (cfg.CLIENTE ? '?cliente=' + encodeURIComponent(cfg.CLIENTE) : '');
    modulo = chamarApi_('get', caminho).filter(function (m) { return m.chave === MODULO; })[0];
    if (!modulo) throw new Error('Módulo "' + MODULO + '" não encontrado na API.');
  } catch (e) {
    ui.alert('Não foi possível montar o modelo', String(e.message || e), ui.ButtonSet.OK);
    return;
  }

  var aba = ss.getSheetByName(ABA_DADOS);
  if (aba) {
    var ok = ui.alert('Refazer o modelo?', 'A aba "' + ABA_DADOS + '" será apagada e recriada. Os dados digitados nela serão perdidos.', ui.ButtonSet.YES_NO);
    if (ok !== ui.Button.YES) return;
    aba.getProtections(SpreadsheetApp.ProtectionType.RANGE).forEach(function (p) { p.remove(); });
    aba.clear();
    aba.getRange(1, 1, aba.getMaxRows(), aba.getMaxColumns()).clearDataValidations();
  } else {
    aba = ss.insertSheet(ABA_DADOS, 0);
  }

  var campos = modulo.campos;
  var n = campos.length;
  if (aba.getMaxColumns() < n) aba.insertColumnsAfter(aba.getMaxColumns(), n - aba.getMaxColumns());
  if (aba.getMaxRows() < MAX_LINHAS + 1) aba.insertRowsAfter(aba.getMaxRows(), MAX_LINHAS + 1 - aba.getMaxRows());

  // Cabeçalho: nome técnico do campo, com o rótulo e a ajuda em uma nota.
  var cab = aba.getRange(1, 1, 1, n);
  cab.setValues([campos.map(function (c) { return c.nome; })]);
  cab.setFontWeight('bold').setHorizontalAlignment('center');
  cab.setBackgrounds([campos.map(function (c) { return c.obrigatorio ? COR_OBRIGATORIO : COR_CABECALHO; })]);
  cab.setNotes([campos.map(notaDoCampo_)]);

  // Validação por coluna (linhas 2..MAX_LINHAS+1).
  campos.forEach(function (c, j) {
    var col = aba.getRange(2, j + 1, MAX_LINHAS, 1);
    var regra = null;
    if (c.opcoes && c.opcoes.length) {
      regra = SpreadsheetApp.newDataValidation().requireValueInList(c.opcoes, true).setAllowInvalid(false)
        .setHelpText('Escolha um valor da lista.').build();
    } else if (c.tipo === 'booleano') {
      regra = SpreadsheetApp.newDataValidation().requireValueInList(['Sim', 'Não'], true).setAllowInvalid(false)
        .setHelpText('Sim ou Não. Vazio = ' + (c.padrao ? 'Sim' : 'Não') + '.').build();
    } else if (c.tipo === 'data') {
      col.setNumberFormat('dd/MM/yyyy');
      regra = SpreadsheetApp.newDataValidation().requireDate().setAllowInvalid(false)
        .setHelpText('Data no formato DD/MM/AAAA.').build();
    } else if (c.tipo === 'inteiro') {
      regra = SpreadsheetApp.newDataValidation().requireNumberGreaterThanOrEqualTo(0).setAllowInvalid(false)
        .setHelpText('Número inteiro, zero ou maior.').build();
    } else if (c.tipo === 'email') {
      col.setNumberFormat('@');
      regra = SpreadsheetApp.newDataValidation().requireTextIsEmail().setAllowInvalid(false)
        .setHelpText('Informe um e-mail válido.').build();
    } else {
      col.setNumberFormat('@'); // texto puro: preserva zeros à esquerda
      if (c.tamanho_max) {
        regra = SpreadsheetApp.newDataValidation().requireTextLengthLessThanOrEqualTo(c.tamanho_max).setAllowInvalid(false)
          .setHelpText('Máximo de ' + c.tamanho_max + ' caracteres.').build();
      }
    }
    if (regra) col.setDataValidation(regra);
  });

  aba.setFrozenRows(1);
  aba.autoResizeColumns(1, n);

  // Trava o cabeçalho: só quem criou o modelo edita. (Proteção do Sheets não é
  // segurança forte -- o servidor valida tudo de novo -- mas evita acidente.)
  var prot = aba.getRange(1, 1, 1, n).protect().setDescription('Cabeçalho do modelo -- não editar');
  prot.addEditor(Session.getEffectiveUser());
  prot.removeEditors(prot.getEditors().filter(function (u) {
    return u.getEmail() !== Session.getEffectiveUser().getEmail();
  }));
  if (prot.canDomainEdit()) prot.setDomainEdit(false);

  montarInstrucoes_(modulo, cfg);
  cfg.VERSAO_SCHEMA = String(modulo.versao_schema || '');
  salvarConfig_(cfg);
  ss.setActiveSheet(aba);
  ss.toast('Modelo montado (schema v' + cfg.VERSAO_SCHEMA + '). Preencha a aba "' + ABA_DADOS + '".', 'Acelerador RM', 6);
}

function notaDoCampo_(c) {
  var t = c.rotulo + (c.obrigatorio ? ' (obrigatório)' : '');
  if (c.ajuda) t += '\n' + c.ajuda;
  return t;
}

function montarInstrucoes_(modulo, cfg) {
  var ss = SpreadsheetApp.getActive();
  var aba = ss.getSheetByName(ABA_INSTRUCOES) || ss.insertSheet(ABA_INSTRUCOES);
  aba.clear();
  var linhas = [
    ['Como preencher -- ' + modulo.nome + ' (' + modulo.dataserver + ')'],
    [''],
    ['1. Preencha a aba "' + ABA_DADOS + '", uma linha por usuário. Colunas com fundo amarelo são obrigatórias.'],
    ['2. Passe o mouse (ou clique) no título da coluna para ver o que é e como preencher.'],
    ['3. Colunas de Sim/Não e de lista têm uma seta: escolha o valor. Datas: DD/MM/AAAA.'],
    ['4. Deixe vazio o que não souber -- exceto as colunas obrigatórias.'],
    ['5. NÃO informe senha: ela não faz parte deste cadastro.'],
    ['6. Não altere o cabeçalho (linha 1) nem a ordem das colunas.'],
    ['7. Ao terminar, avise o analista: ele valida os dados e gera o arquivo para o RM.'],
    [''],
    ['Versão do modelo: schema v' + (modulo.versao_schema || '?')]
  ];
  aba.getRange(1, 1, linhas.length, 1).setValues(linhas);
  aba.getRange(1, 1).setFontWeight('bold').setFontSize(13);
  aba.setColumnWidth(1, 720);
}

/* --------------------------------- validar --------------------------------- */

function lerDados_(aba, n) {
  var ultima = aba.getLastRow();
  var cab = aba.getRange(1, 1, 1, n).getValues()[0].map(String);
  if (ultima < 2) return { cab: cab, linhas: [], numeros: [] };
  var valores = aba.getRange(2, 1, Math.min(ultima - 1, MAX_LINHAS), n).getDisplayValues();
  var linhas = [];
  var numeros = []; // linha real da planilha de cada linha enviada
  valores.forEach(function (l, i) {
    var vazia = l.every(function (c) { return String(c).trim() === ''; });
    if (!vazia) {
      linhas.push(l.map(function (c) { return String(c).replace(/[\t\r\n]+/g, ' ').trim(); }));
      numeros.push(i + 2);
    }
  });
  return { cab: cab, linhas: linhas, numeros: numeros };
}

function validar() {
  var r = validarInterno_(false);
  return r;
}

function validarInterno_(silencioso) {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActive();
  var cfg = lerConfig_();
  var aba = ss.getSheetByName(ABA_DADOS);
  if (!aba) {
    ui.alert('Falta a aba "' + ABA_DADOS + '"', 'Use o menu Acelerador RM > Montar modelo primeiro.', ui.ButtonSet.OK);
    return null;
  }
  var n = Math.max(aba.getLastColumn(), 1);
  var d = lerDados_(aba, n);
  if (d.linhas.length === 0) {
    ui.alert('Nada para validar', 'Preencha pelo menos uma linha na aba "' + ABA_DADOS + '".', ui.ButtonSet.OK);
    return null;
  }

  var texto = [d.cab.join('\t')].concat(d.linhas.map(function (l) { return l.join('\t'); })).join('\n');
  var resp;
  try {
    resp = chamarApi_('post', '/' + MODULO + '/lote', { operacao: cfg.OPERACAO, texto: texto, cliente: cfg.CLIENTE || null });
  } catch (e) {
    ui.alert('Não foi possível validar', String(e.message || e), ui.ButtonSet.OK);
    return null;
  }

  // Limpa as marcas da validação anterior e pinta as novas.
  var ultima = aba.getLastRow();
  if (ultima >= 2) {
    var area = aba.getRange(2, 1, ultima - 1, n);
    area.setBackground(null);
    area.clearNote();
  }
  var porCelula = {};
  resp.linhas.forEach(function (l) {
    if (l.valido) return;
    var linhaPlanilha = d.numeros[l.linha - 2];
    l.erros.forEach(function (e) {
      var col = d.cab.indexOf(e.campo);
      if (col < 0) col = 0; // erro sem coluna correspondente: marca a primeira
      var chave = linhaPlanilha + ':' + col;
      porCelula[chave] = (porCelula[chave] ? porCelula[chave] + '\n' : '') + e.mensagem;
    });
  });
  Object.keys(porCelula).forEach(function (chave) {
    var p = chave.split(':');
    aba.getRange(Number(p[0]), Number(p[1]) + 1).setBackground(COR_ERRO).setNote(porCelula[chave]);
  });

  if (cfg.VERSAO_SCHEMA && resp.versao_schema && String(resp.versao_schema) !== String(cfg.VERSAO_SCHEMA)) {
    ui.alert('Modelo desatualizado', 'Esta planilha foi montada com o schema v' + cfg.VERSAO_SCHEMA + ' e a API está na v' + resp.versao_schema + '. Use "Montar modelo" para atualizar (copie os dados antes).', ui.ButtonSet.OK);
  }

  var resumo = resp.validos + ' válido(s) de ' + resp.total + (resp.invalidos ? ' -- ' + resp.invalidos + ' com erro (células em vermelho; passe o mouse para ver o motivo).' : '.');
  if (resp.avisos_gerais && resp.avisos_gerais.length) resumo += '\n\n' + resp.avisos_gerais.join('\n');
  if (!silencioso) ui.alert('Resultado da validação', resumo, ui.ButtonSet.OK);
  ss.toast(resp.validos + '/' + resp.total + ' válidos', 'Acelerador RM', 5);
  return resp;
}

/* ----------------------------- gerar arquivo ------------------------------ */

function gerarArquivo() {
  var ui = SpreadsheetApp.getUi();
  var resp = validarInterno_(true);
  if (!resp) return;
  if (!resp.jsonl) {
    ui.alert('Nenhum registro válido', 'Corrija as células em vermelho e tente de novo.', ui.ButtonSet.OK);
    return;
  }
  if (resp.invalidos > 0) {
    var ok = ui.alert('Há linhas com erro', resp.invalidos + ' linha(s) com erro ficarão FORA do arquivo. Gerar mesmo assim com as ' + resp.validos + ' válida(s)?', ui.ButtonSet.YES_NO);
    if (ok !== ui.Button.YES) return;
  }
  var conteudo = JSON.stringify(resp.jsonl).replace(/</g, '\\u003c');
  var nome = JSON.stringify(resp.nome_arquivo).replace(/</g, '\\u003c');
  var html = HtmlService.createHtmlOutput(
    '<div style="font-family:Arial,sans-serif;font-size:13px">' +
    '<p>' + resp.validos + ' registro(s) válido(s). Baixe o arquivo (ou copie) e envie ao RM conforme as instruções do Gerador de DataServer.</p>' +
    '<textarea id="t" readonly style="width:100%;height:240px;font-family:monospace;font-size:11px"></textarea>' +
    '<p><button onclick="baixar()">Baixar arquivo</button> <button onclick="copiar()">Copiar</button></p></div>' +
    '<script>var CONTEUDO=' + conteudo + ';var NOME=' + nome + ';' +
    'document.getElementById("t").value=CONTEUDO;' +
    'function baixar(){var b=new Blob([CONTEUDO],{type:"application/json"});var a=document.createElement("a");' +
    'a.href=URL.createObjectURL(b);a.download=NOME;document.body.appendChild(a);a.click();}' +
    'function copiar(){var t=document.getElementById("t");t.select();document.execCommand("copy");}' +
    '</script>'
  ).setWidth(680).setHeight(430);
  ui.showModalDialog(html, 'Arquivo para o RM');
}
