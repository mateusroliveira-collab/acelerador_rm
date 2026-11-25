/**
 * Conexão com o conector local (public/conector/conector_rm.py).
 *
 * Só a porta e o código de pareamento ficam na sessão da aba, para outras
 * telas (ex.: lote do Gerador de DataServer) reaproveitarem. Usuário e senha
 * do RM NUNCA são guardados.
 */

export const PORTA_PADRAO = "8765";
const CHAVE_SESSAO = "conector_rm";

export type ConexaoConector = { porta: string; token: string };

export function urlConector(porta: string) {
  return `http://127.0.0.1:${porta}`;
}

export function lerConexaoSalva(): ConexaoConector | null {
  try {
    const v = JSON.parse(sessionStorage.getItem(CHAVE_SESSAO) || "null");
    return v && v.porta && v.token ? v : null;
  } catch {
    return null;
  }
}

export function salvarConexao(c: ConexaoConector) {
  sessionStorage.setItem(CHAVE_SESSAO, JSON.stringify(c));
}

/** Mensagem para quando o navegador nem alcança o conector. */
export function mensagemConectorInacessivel(porta: string) {
  return (
    `Não encontrei o conector em ${urlConector(porta)}. Confira se a janela do conector está aberta, ` +
    "se a porta é a mesma e se o navegador pediu permissão para acessar a rede local (permita). " +
    "Se abriu o conector sem --origem igual a este site, feche e abra de novo com o comando de " +
    "\"Como abrir o conector\"."
  );
}

export type BaseRm = { nome: string; rm: string };
export type StatusConector = { versao: string; rm: string; bases: BaseRm[] };

/** Versão mínima do conector para várias bases e "se já existir: pular/alterar". */
export const VERSAO_MINIMA = "1.1.0";

export function versaoAtende(versao: string, minima = VERSAO_MINIMA) {
  const a = versao.split(".").map(Number);
  const b = minima.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0);
  }
  return true;
}

/**
 * Comando para abrir o conector. `bases`: uma por linha, "nome=https://servidor:porta"
 * (ou só o endereço, se for uma base).
 */
function argumentosConector(bases: string, origem: string, porta: string, autoassinado: boolean, aspas: boolean) {
  const q = (v: string) => (aspas ? `"${v.replace(/"/g, "")}"` : v);
  const linhas = bases.split("\n").map((l) => l.trim()).filter(Boolean);
  const partes: string[] = [];
  for (const l of linhas.length ? linhas : ["https://SERVIDOR-RM:PORTA"]) partes.push(`--rm ${q(l)}`);
  if (origem) partes.push(`--origem ${q(origem)}`);
  if (porta && porta !== PORTA_PADRAO) partes.push(`--porta ${porta}`);
  if (autoassinado) partes.push("--aceitar-certificado-autoassinado");
  return partes.join(" ");
}

export function comandoConector(bases: string, origem: string, porta: string, autoassinado: boolean) {
  return `python conector_rm.py ${argumentosConector(bases, origem, porta, autoassinado, false)}`;
}

/**
 * Atalho para Windows: salvo na mesma pasta do conector_rm.py, abre com dois
 * cliques e segura a janela (o código de pareamento não some se der erro).
 */
export function atalhoWindows(bases: string, origem: string, porta: string, autoassinado: boolean) {
  const args = argumentosConector(bases, origem, porta, autoassinado, true);
  return [
    "@echo off",
    "chcp 65001 >nul",
    "title Conector RM - deixe esta janela aberta",
    'cd /d "%~dp0"',
    'if not exist "conector_rm.py" (',
    "  echo Coloque este arquivo na mesma pasta do conector_rm.py.",
    "  pause",
    "  exit /b 1",
    ")",
    "where py >nul 2>nul",
    "if %errorlevel%==0 (",
    `  py conector_rm.py ${args}`,
    ") else (",
    `  python conector_rm.py ${args}`,
    ")",
    "echo.",
    "echo O conector foi encerrado.",
    "pause",
    "",
  ].join("\r\n");
}
