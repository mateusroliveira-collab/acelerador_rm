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
    "Se abriu o conector sem --origem igual a este site, feche e abra de novo com o comando da tela Conector RM."
  );
}
