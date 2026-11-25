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
    `Não encontrei o conector em ${urlConector(porta)}. Confira se a janela do conector está aberta e ` +
    `se a "Porta do conector" é a da linha "Porta:" da janela (padrão ${PORTA_PADRAO}) -- não é a porta do RM. ` +
    "Se o navegador pedir permissão para acessar a rede local, permita. " +
    "Se abriu o conector sem --origem igual a este site, feche e abra de novo com o comando de " +
    "\"Como abrir o conector\"."
  );
}

export type BaseRm = { nome: string; rm: string; alias?: string | null };
/** RM instalado na máquina do analista, achado pelo conector (1.4+). */
export type RmLocal = { endereco: string; alias: string | null; instalacao: string; servico: string; no_ar: boolean };
export type StatusConector = { versao: string; rm: string; bases: BaseRm[]; rm_local?: RmLocal[] };

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

/** Site oficial: sempre autorizado no conector. */
export const SITE_OFICIAL = "https://acelerador-rm.vercel.app";

/**
 * Origens que o conector deve aceitar para este site. Endereço de deploy da
 * Vercel (projeto-<9 letras>-equipe.vercel.app) muda a cada deploy: autoriza
 * também projeto-*-equipe.vercel.app, para o conector não parar de funcionar.
 */
export function origensDoSite(origem: string): string[] {
  const o = origem.trim().replace(/\/+$/, "").toLowerCase();
  const saida = o ? [o] : [];
  const m = /^https:\/\/([a-z0-9-]+?)-[a-z0-9]{9}-([a-z0-9-]+)\.vercel\.app$/.exec(o);
  if (m) saida.push(`https://${m[1]}-*-${m[2]}.vercel.app`);
  if (!saida.includes(SITE_OFICIAL)) saida.push(SITE_OFICIAL);
  return saida;
}

/** O que o /ping do conector (1.3+) responde: aceita qualquer site, não revela nada além disto. */
export type PingConector = { conector: true; versao: string; origem_autorizada: boolean };

export async function pingConector(porta: string): Promise<PingConector | null> {
  try {
    const r = await fetch(`${urlConector(porta)}/ping`, { cache: "no-store" });
    const dados = await r.json();
    return dados?.conector === true ? dados : null;
  } catch {
    return null;
  }
}

/**
 * Comando para abrir o conector. `bases`: uma por linha, "nome=https://servidor:porta"
 * (ou só o endereço, se for uma base).
 */
function argumentosConector(bases: string, origem: string, porta: string, autoassinado: boolean, aspas: boolean) {
  // Aspas sempre que houver * (o terminal expandiria o curinga).
  const q = (v: string) => (aspas || v.includes("*") ? `"${v.replace(/"/g, "")}"` : v);
  const linhas = bases.split("\n").map((l) => l.trim()).filter(Boolean);
  const partes: string[] = [];
  // Sem bases: o conector (1.4+) procura o RM instalado nesta máquina e pergunta.
  for (const l of linhas) partes.push(`--rm ${q(l)}`);
  for (const o of origem ? origensDoSite(origem) : []) partes.push(`--origem ${q(o)}`);
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
    // O navegador renomeia downloads repetidos ("conector_rm (4).py"): usa o mais novo da pasta.
    'set "ARQ="',
    "for /f \"delims=\" %%f in ('dir /b /o:d \"conector_rm*.py\" 2^>nul') do set \"ARQ=%%f\"",
    'if not defined ARQ (',
    "  echo Coloque este arquivo na mesma pasta do conector_rm.py.",
    "  pause",
    "  exit /b 1",
    ")",
    'echo Abrindo "%ARQ%" (o conector mais novo desta pasta)...',
    "echo.",
    "where py >nul 2>nul",
    "if %errorlevel%==0 (",
    `  py "%ARQ%" ${args}`,
    ") else (",
    `  python "%ARQ%" ${args}`,
    ")",
    "echo.",
    "echo O conector foi encerrado.",
    "pause",
    "",
  ].join("\r\n");
}
