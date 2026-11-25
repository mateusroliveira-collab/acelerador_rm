/**
 * Registros do REST DataServer do RM, no formato que o GET devolve:
 *   {"messages": [], "length": N, "data": {...} | [...]}
 * Usado pelo "Postman facilitado" (PostmanRm) para ler, juntar, limpar e
 * enviar registros (um por chamada, como o REST do DataServer recebe).
 */

export type Registro = Record<string, unknown>;

export const SEPARADOR_CHAVE = "$_$"; // chave composta do RM: CODCOLIGADA$_$CODEVENTO = "1$_$1"

function ehObjeto(v: unknown): v is Registro {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/**
 * Aceita o envelope do GET (data objeto ou lista), uma lista de registros ou
 * um registro só. Devolve sempre uma lista de registros.
 */
export function extrairRegistros(json: unknown): Registro[] {
  if (Array.isArray(json)) return json.filter(ehObjeto);
  if (!ehObjeto(json)) return [];
  if ("data" in json && ("messages" in json || "length" in json || Object.keys(json).length === 1)) {
    return extrairRegistros(json.data ?? []);
  }
  return [json];
}

/** Lê o texto do corpo. Lança Error com mensagem em português se não for JSON. */
export function lerRegistros(texto: string): Registro[] {
  if (!texto.trim()) return [];
  let json: unknown;
  try {
    json = JSON.parse(texto);
  } catch (e) {
    const detalhe = e instanceof Error ? e.message : "";
    throw new Error(`O corpo não é um JSON válido. ${detalhe}`.trim());
  }
  return extrairRegistros(json);
}

/** Envelope igual ao do GET do RM. */
export function envelope(registros: Registro[]) {
  return { messages: [], length: registros.length, data: registros };
}

export function textoEnvelope(registros: Registro[]) {
  return JSON.stringify(envelope(registros), null, 2);
}

export type OpcoesLimpeza = {
  /** Tira campos null (num PUT, null apagaria o valor que está no RM). */
  removerNulos: boolean;
  /** Mantém "id" e "parent_id" (por padrão saem: o RM monta a chave pelos campos). */
  manterId: boolean;
  /** Campos que nunca vão no envio (ex.: SENHA, DATAULTIMOACESSO). */
  camposNaoEnviar: string[];
};

/** Prepara um registro para POST/PUT. Vale também para as tabelas filhas (listas). */
export function limparParaEnvio(reg: Registro, op: OpcoesLimpeza): Registro {
  const fora = new Set(op.camposNaoEnviar);
  if (!op.manterId) {
    fora.add("id");
    fora.add("parent_id");
  }
  const limpar = (valor: unknown): unknown => {
    if (Array.isArray(valor)) return valor.map(limpar);
    if (!ehObjeto(valor)) return valor;
    const saida: Registro = {};
    for (const [k, v] of Object.entries(valor)) {
      if (fora.has(k)) continue;
      if (v === null && op.removerNulos) continue;
      saida[k] = limpar(v);
    }
    return saida;
  };
  return limpar(reg) as Registro;
}

/** "CODCOLIGADA,CODEVENTO" -> ["CODCOLIGADA", "CODEVENTO"] */
export function camposDaChave(campoChave: string): string[] {
  return campoChave.split(",").map((c) => c.trim()).filter(Boolean);
}

/** Valor da chave para a URL ("1$_$1"); sem os campos, usa o "id" do GET. "" se não achar. */
export function chaveDoRegistro(reg: Registro, campoChave: string): string {
  const campos = camposDaChave(campoChave);
  if (campos.length > 0) {
    const valores = campos.map((c) => reg[c]);
    if (valores.every((v) => v !== null && v !== undefined && String(v).trim() !== "")) {
      return valores.map((v) => String(v).trim()).join(SEPARADOR_CHAVE);
    }
  }
  return typeof reg.id === "string" || typeof reg.id === "number" ? String(reg.id) : "";
}

/** Chave para usar no caminho: escapa o que precisa, mas mantém o $_$ do RM legível. */
export function chaveNaUrl(chave: string) {
  return encodeURIComponent(chave).replace(/%24/g, "$");
}

/**
 * Troca a coligada em todo o registro (pai e tabelas filhas), inclusive no
 * "id"/"parent_id" do GET. Opcionalmente troca também CODCOLCONTA (coligada
 * das contas contábeis).
 */
export function trocarColigada(reg: Registro, nova: number, tambemContas: boolean): Registro {
  const trocarId = (id: unknown, antiga: unknown) => {
    if (typeof id !== "string" || antiga === undefined) return id;
    const partes = id.split(SEPARADOR_CHAVE);
    if (partes[0] === String(antiga)) partes[0] = String(nova);
    return partes.join(SEPARADOR_CHAVE);
  };
  const trocar = (valor: unknown, coligadaPai?: unknown): unknown => {
    if (Array.isArray(valor)) return valor.map((v) => trocar(v, coligadaPai));
    if (!ehObjeto(valor)) return valor;
    const antiga = "CODCOLIGADA" in valor ? valor.CODCOLIGADA : coligadaPai;
    const saida: Registro = {};
    for (const [k, v] of Object.entries(valor)) {
      if (k === "CODCOLIGADA") saida[k] = nova;
      else if (k === "CODCOLCONTA" && tambemContas && v !== null) saida[k] = nova;
      else if (k === "id") saida[k] = trocarId(v, antiga);
      else if (k === "parent_id") saida[k] = trocarId(v, coligadaPai ?? antiga);
      else saida[k] = trocar(v, antiga);
    }
    return saida;
  };
  return trocar(reg) as Registro;
}

type MensagemRm = { code?: string; type?: string; detail?: string; message?: string };

const EXPLICACOES: Record<string, string> = {
  "0007":
    "O RM recusou por uma restrição do banco. Causas comuns: (1) o registro já existe -- use " +
    "\"Se já existir: pular\" ou \"alterar\"; (2) algum código ligado não existe nesta base (ex.: " +
    "CODACESSO, conta contábil, fórmula, coligada); (3) faltou um campo obrigatório.",
};

/** Texto curto do que o RM respondeu, com a explicação dos códigos conhecidos. */
export function mensagemDoRm(resposta: unknown): string {
  if (typeof resposta === "string") return resposta.slice(0, 400);
  if (!ehObjeto(resposta)) return "";
  const msgs = Array.isArray(resposta.messages) ? (resposta.messages as MensagemRm[]) : [];
  const partes = msgs
    .filter((m) => ehObjeto(m))
    .map((m) => {
      const texto = m.detail ?? m.message ?? "";
      const explicacao = m.code ? EXPLICACOES[m.code] : undefined;
      return [m.code ? `[${m.code}] ${texto}` : texto, explicacao].filter(Boolean).join(" ");
    })
    .filter(Boolean);
  if (partes.length) return partes.join(" | ").slice(0, 900);
  const direto = (resposta.message ?? resposta.Message ?? resposta.detail ?? resposta.mensagem) as string | undefined;
  return typeof direto === "string" ? direto.slice(0, 400) : "";
}

/** Rótulo curto do registro para listas (ex.: NOME ou DESCRICAO). */
export function descricaoDoRegistro(reg: Registro): string {
  for (const campo of ["NOME", "DESCRICAO", "NOMEFANTASIA", "TITULO"]) {
    const v = reg[campo];
    if (typeof v === "string" && v.trim()) return v;
  }
  return "";
}
