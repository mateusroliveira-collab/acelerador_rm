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
export function comandoConector(bases: string, origem: string, porta: string, autoassinado: boolean) {
  const linhas = bases.split("\n").map((l) => l.trim()).filter(Boolean);
  const partes = ["python conector_rm.py"];
  for (const l of linhas.length ? linhas : ["https://SERVIDOR-RM:PORTA"]) partes.push(`--rm ${l}`);
  if (origem) partes.push(`--origem ${origem}`);
  if (porta && porta !== PORTA_PADRAO) partes.push(`--porta ${porta}`);
  if (autoassinado) partes.push("--aceitar-certificado-autoassinado");
  return partes.join(" ");
}
